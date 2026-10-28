# Adapted from sohan-shingade/fujiLUT, revision
# f3bead9b6d8dbc3f8ea489b70850fbc42fb4db46. Upstream declares MIT.
# See THIRD_PARTY_NOTICES.md for attribution and local changes.
from __future__ import annotations
import numpy as np
from numpy.typing import NDArray
from scipy.interpolate import CubicSpline
FilmProfile = dict

def rgb_to_hsl(rgb: NDArray) -> NDArray:
    """Convert (N, 3) sRGB array to (N, 3) HSL array.

    H in [0, 360), S in [0, 1], L in [0, 1].
    """
    r, g, b = rgb[:, 0], rgb[:, 1], rgb[:, 2]
    cmax = np.maximum(np.maximum(r, g), b)
    cmin = np.minimum(np.minimum(r, g), b)
    delta = cmax - cmin

    # Lightness
    l = (cmax + cmin) / 2.0

    # Saturation
    s = np.where(
        delta < 1e-10,
        0.0,
        np.where(
            l <= 0.5,
            delta / np.maximum(cmax + cmin, 1e-10),
            delta / np.maximum(2.0 - cmax - cmin, 1e-10),
        ),
    )

    # Hue
    safe_delta = np.where(delta < 1e-10, 1.0, delta)  # avoid div/0
    hr = np.where(cmax == r, ((g - b) / safe_delta) % 6.0, 0.0)
    hg = np.where(cmax == g, ((b - r) / safe_delta) + 2.0, 0.0)
    hb = np.where(cmax == b, ((r - g) / safe_delta) + 4.0, 0.0)

    h = np.where(delta < 1e-10, 0.0, np.where(cmax == r, hr, np.where(cmax == g, hg, hb)))
    h = (h * 60.0) % 360.0

    return np.stack([h, s, l], axis=-1)

def hsl_to_rgb(hsl: NDArray) -> NDArray:
    """Convert (N, 3) HSL array to (N, 3) sRGB array.

    Expects H in [0, 360), S in [0, 1], L in [0, 1].
    """
    h, s, l = hsl[:, 0], hsl[:, 1], hsl[:, 2]

    c = (1.0 - np.abs(2.0 * l - 1.0)) * s
    h_prime = (h / 60.0) % 6.0
    x = c * (1.0 - np.abs(h_prime % 2.0 - 1.0))
    m = l - c / 2.0

    # Select RGB based on hue sector
    sector = np.floor(h_prime).astype(int) % 6

    r = np.where(sector == 0, c, np.where(sector == 1, x, np.where(sector == 2, 0, np.where(sector == 3, 0, np.where(sector == 4, x, c)))))
    g = np.where(sector == 0, x, np.where(sector == 1, c, np.where(sector == 2, c, np.where(sector == 3, x, np.where(sector == 4, 0, 0)))))
    b = np.where(sector == 0, 0, np.where(sector == 1, 0, np.where(sector == 2, x, np.where(sector == 3, c, np.where(sector == 4, c, x)))))

    return np.stack([r + m, g + m, b + m], axis=-1)

def _luminance(rgb: NDArray) -> NDArray:
    """Compute perceived luminance (BT.709 weights)."""
    return 0.2126 * rgb[:, 0] + 0.7152 * rgb[:, 1] + 0.0722 * rgb[:, 2]

_HUE_RANGES: dict[str, tuple[float, float]] = {
    "reds": (0.0, 30.0),
    "oranges": (30.0, 15.0),
    "yellows": (55.0, 15.0),
    "greens": (120.0, 40.0),
    "cyans": (180.0, 30.0),
    "blues": (230.0, 30.0),
    "purples": (280.0, 20.0),
    "magentas": (320.0, 25.0),
}

def _hue_weight(hue: NDArray, center: float, half_width: float) -> NDArray:
    """Smooth weight for how much a hue value falls within a range.

    Uses cosine falloff centered on `center` with given `half_width` (degrees).
    Returns values in [0, 1].
    """
    # Angular distance on the hue wheel
    diff = np.abs(((hue - center + 180.0) % 360.0) - 180.0)
    weight = 0.5 * (1.0 + np.cos(np.pi * np.minimum(diff / half_width, 1.0)))
    weight = np.where(diff > half_width, 0.0, weight)
    return weight

def _apply_spline_curve(values: NDArray, control_points: list[tuple[float, float]]) -> NDArray:
    """Apply a cubic spline tone curve to an array of values in [0, 1]."""
    xs = np.array([p[0] for p in control_points])
    ys = np.array([p[1] for p in control_points])
    cs = CubicSpline(xs, ys, bc_type="clamped")
    return np.clip(cs(values), 0.0, 1.0)

def apply_film_simulation(rgb: NDArray, profile: FilmProfile) -> NDArray:
    """Apply a film simulation profile: tone curves, color matrix, HSL shifts.

    Args:
        rgb: (N, 3) sRGB array.
        profile: Film simulation profile dict.

    Returns:
        (N, 3) transformed sRGB array.
    """
    result = rgb.copy()

    # 1. Per-channel tone curves via cubic spline
    tone_curve = profile["tone_curve"]
    result[:, 0] = _apply_spline_curve(result[:, 0], tone_curve["r"])
    result[:, 1] = _apply_spline_curve(result[:, 1], tone_curve["g"])
    result[:, 2] = _apply_spline_curve(result[:, 2], tone_curve["b"])

    # 2. Color matrix (3x3 transform)
    matrix = np.array(profile["color_matrix"], dtype=np.float64)
    result = result @ matrix.T
    result = np.clip(result, 0.0, 1.0)

    # 3. HSL shifts per hue range
    hsl_shifts = profile.get("hsl_shifts")
    if hsl_shifts and any(
        abs(v) > 1e-6
        for shift in hsl_shifts.values()
        for v in shift.values()
    ):
        hsl = rgb_to_hsl(result)
        original_h = hsl[:, 0].copy()
        h, s, l = hsl[:, 0].copy(), hsl[:, 1].copy(), hsl[:, 2].copy()

        for range_name, shifts in hsl_shifts.items():
            if range_name not in _HUE_RANGES:
                continue
            h_shift = shifts.get("h", 0.0)
            s_shift = shifts.get("s", 0.0)
            l_shift = shifts.get("l", 0.0)
            if abs(h_shift) < 1e-6 and abs(s_shift) < 1e-6 and abs(l_shift) < 1e-6:
                continue

            center, half_width = _HUE_RANGES[range_name]
            w = _hue_weight(original_h, center, half_width)

            h += w * h_shift
            s += w * s_shift
            l += w * l_shift

        h = h % 360.0
        s = np.clip(s, 0.0, 1.0)
        l = np.clip(l, 0.0, 1.0)
        result = hsl_to_rgb(np.stack([h, s, l], axis=-1))

    # 4. Shadow and highlight tints
    shadow_tint = np.array(profile.get("shadow_tint", [0, 0, 0]), dtype=np.float64)
    highlight_tint = np.array(profile.get("highlight_tint", [0, 0, 0]), dtype=np.float64)

    if np.any(np.abs(shadow_tint) > 1e-6) or np.any(np.abs(highlight_tint) > 1e-6):
        lum = _luminance(result)
        # Shadow tint blends in dark areas, highlight tint in bright areas
        shadow_w = (1.0 - lum)[:, np.newaxis] ** 2  # quadratic falloff
        highlight_w = lum[:, np.newaxis] ** 2
        result = result + shadow_tint * shadow_w + highlight_tint * highlight_w

    return np.clip(result, 0.0, 1.0)

def apply_base_saturation(rgb: NDArray, base_saturation: float) -> NDArray:
    """Apply the film simulation's base saturation multiplier.

    This is separate from the user's Color parameter — it's part of the
    film simulation character.
    """
    if abs(base_saturation - 1.0) < 1e-6:
        return rgb

    hsl = rgb_to_hsl(rgb)
    hsl[:, 1] = np.clip(hsl[:, 1] * base_saturation, 0.0, 1.0)
    return hsl_to_rgb(hsl)
