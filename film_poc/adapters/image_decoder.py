"""Ordinary photo decoding (JPEG, PNG, TIFF) with Pillow. Auto-registered.

Limits: Pillow keeps RGB images at 8 bits per channel, so 16-bit RGB PNG/TIFF files are read at
8 bits (16-bit grayscale is kept at full precision). Files carry no camera preview, so no tone
matching happens: the sRGB-encoded pixels are simply linearised.
"""
import io
import logging
from pathlib import Path

import numpy as np
from PIL import Image, ImageCms, ImageOps

from ..core.raw import register_decoder
from . import rawpy_decoder  # noqa: F401 - RAW registers first, so it leads labels and filters

log = logging.getLogger(__name__)

MAX_PIXELS = 200_000_000   # normal camera sizes pass; larger files are refused
# Pillow warns above this and raises DecompressionBombError above twice this: a backstop
# for files whose header lies about the size. The check stays enabled.
Image.MAX_IMAGE_PIXELS = MAX_PIXELS

FORMAT_LABELS = {'.jpg': 'JPEG', '.jpeg': 'JPEG', '.png': 'PNG', '.tif': 'TIFF', '.tiff': 'TIFF'}
_GRAY_16 = ('I;16', 'I;16L', 'I;16B', 'I;16N', 'I')
_ALPHA = ('LA', 'La', 'PA', 'RGBA', 'RGBa')
_ENCODED_TO_LINEAR_8BIT: np.ndarray | None = None


def srgb_to_linear(encoded: np.ndarray) -> np.ndarray:
    """IEC 61966-2-1 transfer function (same constants as the tone reference), float32."""
    x = np.asarray(encoded, dtype=np.float32)
    return np.where(x <= .04045, x / 12.92, ((x + .055) / 1.055) ** 2.4).astype(np.float32)


def _lut() -> np.ndarray:
    global _ENCODED_TO_LINEAR_8BIT
    if _ENCODED_TO_LINEAR_8BIT is None:
        _ENCODED_TO_LINEAR_8BIT = srgb_to_linear(np.arange(256, dtype=np.float32) / 255)
    return _ENCODED_TO_LINEAR_8BIT


def _is_srgb(profile: 'ImageCms.ImageCmsProfile') -> bool:
    return 'srgb' in (ImageCms.getProfileDescription(profile) or '').lower()


def _to_srgb(image: Image.Image, icc: bytes | None) -> Image.Image:
    """Convert to sRGB when the embedded profile says otherwise; never raises."""
    if not icc:
        return image
    try:
        source = ImageCms.ImageCmsProfile(io.BytesIO(icc))
        if _is_srgb(source):
            return image
        target = ImageCms.createProfile('sRGB')
        return ImageCms.profileToProfile(
            image, source, target, renderingIntent=ImageCms.Intent.RELATIVE_COLORIMETRIC,
            outputMode='RGB', flags=ImageCms.Flags.BLACKPOINTCOMPENSATION)
    except (ImageCms.PyCMSError, OSError, ValueError, TypeError, AttributeError) as exc:
        log.warning('Perfil ICC no utilizable (%s); se asume sRGB.', exc)
        return image


def _over_white(image: Image.Image) -> Image.Image:
    rgba = image.convert('RGBA')
    background = Image.new('RGBA', rgba.size, (255, 255, 255, 255))
    return Image.alpha_composite(background, rgba).convert('RGB')


def _gray_16(image: Image.Image) -> np.ndarray:
    """Encoded [0, 1] HxW floats from 16/32-bit integer grayscale, without overflowing."""
    data = np.asarray(image).astype(np.float32)
    top = 65535.0 if data.size == 0 or data.max() <= 65535 else float(data.max())
    return np.clip(data / top, 0.0, 1.0)


def _encoded_rgb(image: Image.Image, icc: bytes | None) -> np.ndarray:
    """Encoded (sRGB gamma) float32 HxWx3 in [0, 1], or the 8-bit table index array."""
    mode = image.mode
    if mode in _GRAY_16:
        gray = _gray_16(image)
        return np.repeat(gray[..., None], 3, axis=2)
    if mode == 'F':
        gray = np.clip(np.asarray(image, dtype=np.float32), 0.0, 1.0)
        return np.repeat(gray[..., None], 3, axis=2)
    if mode in _ALPHA or (mode == 'P' and 'transparency' in image.info):
        image = _over_white(image)
    elif mode == 'CMYK':
        image = _to_srgb(image, icc) if icc else image
        if image.mode != 'RGB':
            image = image.convert('RGB')
        icc = None
    elif mode != 'RGB':
        image = image.convert('RGB')
    image = _to_srgb(image, icc)
    return np.asarray(image)  # uint8


class ImageDecoder:
    extensions = tuple(FORMAT_LABELS)
    label = 'Imagen'

    @staticmethod
    def format_label(path: Path) -> str:
        return FORMAT_LABELS.get(Path(path).suffix.lower(), 'Imagen')

    def decode(self, path: Path) -> tuple[np.ndarray, None]:
        """Oriented HxWx3 float32 linear sRGB in [0, 1] and no camera preview (None)."""
        try:
            with Image.open(path) as opened:
                if opened.width * opened.height > MAX_PIXELS:
                    raise ValueError('imagen demasiado grande')
                opened.load()  # truncated or corrupt data raises here
                icc = opened.info.get('icc_profile')
                image = ImageOps.exif_transpose(opened)
            data = _encoded_rgb(image, icc)
            if data.dtype == np.uint8:
                linear = _lut()[data]
            else:
                linear = srgb_to_linear(data)
        except (OSError, SyntaxError, ValueError, TypeError, EOFError, KeyError, MemoryError,
                Image.DecompressionBombError) as exc:
            raise ValueError(
                f'No se pudo abrir «{Path(path).name}»: el archivo está dañado, es demasiado '
                'grande o su formato de imagen no es compatible.') from exc
        return np.ascontiguousarray(linear, dtype=np.float32), None


register_decoder(ImageDecoder())
