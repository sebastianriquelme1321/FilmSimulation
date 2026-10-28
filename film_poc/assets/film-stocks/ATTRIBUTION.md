# Film stock asset attribution

These PNG files are creative grading data under **CC BY-SA 4.0**, separate from the application's GPL software license. Film-stock names describe the emulation target; no Kodak, Ilford or Fujifilm endorsement or official profile is claimed.

## Kodak Gold 200

`kodak_gold_200.png` copied unchanged from https://github.com/thedevmark/film-lab at revision `3015fd3b2561d279d46bdadcabc3f2a3f5724188`, path `luts/open/kodak_gold_200.png`.

Derived by Film Lab from Andrea Volpato's spektrafilm Gold 200 profile, printed through Kodak Portra Endura, baked for display-sRGB input/output at 2.47 stops above midgray. Full original attribution, licensing and bake changes are retained verbatim in GOLD_ATTRIBUTION.md, GOLD_LICENSE and GOLD_SPEKTRAFILM_LICENSE.txt. See https://github.com/andreavolpato/spektrafilm. No further modification to the PNG was made.

## Pat David collection

`kodak_portra_160.png`, `kodak_portra_400.png`, `kodak_portra_800.png`, `kodak_kodachrome_64.png`, `ilford_hp5_plus_400.png` copied unchanged from https://github.com/NatronGitHub/clut at revision `af7b50d4caf6244fb6895a647f5b6a84efe7931a`.

Author attribution: Pat David, as documented by the repository for Negative (new), Slide (color) and Black and White collections. Original work: https://patdavid.net/2013/08/film-emulation-presets-in-gmic-gimp.html. Repository README and license declaration preserved in NATRON_README.md. License: https://creativecommons.org/licenses/by-sa/4.0/ ; legal text https://creativecommons.org/licenses/by-sa/4.0/legalcode . No modifications to the PNGs. Any redistributed modified LUT must retain attribution, indicate changes and use compatible share-alike terms.

## Loader code

`../../hald_loader.py` contains selected read-only loading functions from Film Lab, copyright (c) 2026 Mark Koellmann, MIT license retained in FILM_LAB_CODE_LICENSE.txt. Functions extracted from filmlab/lut.py at the Film Lab revision above, with local imports/header; no interpolation/effects/server copied. Application interpolation uses SciPy trilinear evaluation, so results may differ slightly from Film Lab's tetrahedral interpolation.

`manifest.json` records original filenames and SHA-256 checksums. No LUT assets were downsampled, recolored or regenerated. 16-bit PNGs are decoded at 16-bit precision into the runtime cube; Gold's original asset is 8-bit.
