"""Use case: carry the source photo's EXIF into the exported JPEG."""
import logging
from pathlib import Path

from PIL import Image

from .. import adapters
from ..core import raw

log = logging.getLogger(__name__)

_IFD0_KEEP = (0x010E, 0x010F, 0x0110, 0x0131, 0x0132, 0x013B, 0x8298)  # description, make,
# model, software, date, artist, copyright. Structural TIFF tags (strips, compression...) go.
_EXIF_IFD, _GPS_IFD, _ORIENTATION = 0x8769, 0x8825, 0x0112
_EXIF_DROP = (0x927C, 0xA005, 0xA002, 0xA003)  # MakerNote (offsets break), interop, pixel size


def read_exif(path: Path) -> bytes | None:
    """EXIF block for the exported JPEG, or None (RAW sources, no EXIF, unreadable EXIF).

    Keeps camera, lens, date and exposure fields; orientation is reset to 1 because the
    decoded pixels are already upright; the embedded thumbnail is not copied."""
    path = Path(path)
    adapters.load_decoders()
    if not raw.is_supported(path) or raw.format_label(path) == 'RAW':
        return None
    try:
        with Image.open(path) as image:
            source = image.getexif()
            if not source:
                return None
            out = Image.Exif()
            for tag in _IFD0_KEEP:
                if tag in source:
                    out[tag] = source[tag]
            out[_ORIENTATION] = 1
            details = {k: v for k, v in source.get_ifd(_EXIF_IFD).items() if k not in _EXIF_DROP}
            if details:
                out.get_ifd(_EXIF_IFD).update(details)
            gps = dict(source.get_ifd(_GPS_IFD))
            if gps:
                out.get_ifd(_GPS_IFD).update(gps)
            return out.tobytes()
    except Exception as exc:  # noqa: BLE001 - odd metadata must never block an export
        log.warning('EXIF de «%s» no utilizable (%s); se exporta sin él.', path.name, exc)
        return None
