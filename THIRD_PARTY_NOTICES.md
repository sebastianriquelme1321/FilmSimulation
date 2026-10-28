# Third-party source attribution

## Film stocks added in v3.6

Kodak Gold 200 LUT: Andrea Volpato / spektrafilm, baked by Film Lab; CC BY-SA 4.0. Portra 160/400/800, Kodachrome 64 and Ilford HP5 Plus 400: Pat David collection via NatronGitHub/clut, CC BY-SA 4.0. These assets retain separate CC licensing and are not relicensed as application code. Per-file origin, pinned revisions, checksums and unmodified license notices are in `film_poc/assets/film-stocks/ATTRIBUTION.md` and its adjacent files.

`film_poc/hald_loader.py` adapts selected Film Lab PNG/Hald reading functions, copyright (c) 2026 Mark Koellmann, MIT; complete notice in `film_poc/assets/film-stocks/FILM_LAB_CODE_LICENSE.txt`. This addition does not remove the GPL terms of the combined application or earlier MIT notices.

`film_poc/profiles.py` and `film_poc/profile_transforms.py` contain adapted portions of [sohan-shingade/fujiLUT](https://github.com/sohan-shingade/fujiLUT), revision `f3bead9b6d8dbc3f8ea489b70850fbc42fb4db46` (retrieved 2026-10-27).

Upstream README declares **MIT**. No standalone LICENSE or copyright notice was present in the inspected checkout; this notice records the repository author/owner as sohan-shingade without inventing a copyright statement. The upstream README declaration and this attribution must remain with these sources. The upstream declaration is reproduced in `film_poc/assets/FUJILUT_LICENSE_DECLARATION.txt`.

Retained: all 14 base film profile parameters; RGB/HSL conversion, curve interpolation, tints, base saturation, hue range definitions and transform pipeline functions needed for those profiles.

Local modifications: cosine hue weights continuous at boundaries; hue-range weights computed from original hue to avoid order-dependent weighting; local imports/types; linear-sRGB adapter; float32 output. Original profile coefficients are unchanged. Sepia skips the final zero-saturation stage so its upstream matrix/tints remain warm instead of becoming grayscale. No upstream web/API/parser, CUBE exporter or HaldCLUT exporter is bundled.

These are unofficial approximations. Neither upstream nor this project establishes equivalence to Fujifilm camera processing. Other runtime dependencies keep their own licenses; consult their installed package metadata.

## darktable Classic Chrome integration (v3.2)

Expanded in v3.5 to the Astia, Monochrome, Provia and Velvia presets from the same pinned module/revision. Decoded patch data is in `darktable_astia.json`, `darktable_mchrome.json`, `darktable_provia.json`, `darktable_velvia.json`; all share the GPL-3.0-or-later attribution and source snapshot below. The six ACROS/Monochrome color-filter variants are local approximations using the MIT-derived profiles with locally chosen RGB mixing weights; they are not official Fujifilm extracted data.

`film_poc/darktable_chrome.json` contains the decoded Classic Chrome preset from darktable `src/iop/colorchecker.c`, revision `69d5214b33112655c73f3504a5f97c0491f82588`. `film_poc/darktable_look.py` adapts its thin-plate-spline interpolation in Python/SciPy. Copyright (C) 2016-2026 darktable developers. GPL-3.0-or-later. The original module credits Jo's Fuji film emulations, without the tone curve (https://jo.dreggn.org/blog/darktable-fuji-styles.tar.xz).

The original module is included as `vendor/darktable/colorchecker.c`; full GNU GPL version 3 text is in `LICENSE`. This combined POC is provided under GPL-3.0-or-later for its original code and darktable-derived parts; third-party MIT portions retain their notices. Distributed without warranty, including without implied warranties of merchantability or fitness for a particular purpose. Preserve corresponding source, notices and license when redistributing the combined work.

Local changes: decoded 49 source/target Lab patches; double-precision SciPy fit instead of darktable float coefficients/fastlog; explicit sRGB/D50 Lab adapter; cached 49³ trilinear LUT for performance; gamut clipping. No darktable RAW processing, tone curve, sharpening, noise or local adjustments are reproduced. Numerical patch fitting is verified; equivalence to the complete darktable renderer is not claimed.
