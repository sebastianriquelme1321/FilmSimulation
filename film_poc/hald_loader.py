# Adapted from film-lab by Mark Koellmann, copyright (c) 2026.
# MIT license; see assets/film-stocks/FILM_LAB_CODE_LICENSE.txt.
# Revision 3015fd3b2561d279d46bdadcabc3f2a3f5724188. Read-only PNG/Hald loader.
import struct
import zlib
from pathlib import Path
import numpy as np
from PIL import Image
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"

def _iter_png_chunks(data: bytes):
    pos = len(_PNG_SIGNATURE)
    while pos < len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        ctype = data[pos + 4:pos + 8]
        cdata = data[pos + 8:pos + 8 + length]
        yield ctype, cdata
        pos += 12 + length

def _paeth_predictor(a, b, c):
    """PNG Paeth predictor (int32 arrays); a=left, b=above, c=above-left."""
    p = a + b - c
    pa = np.abs(p - a)
    pb = np.abs(p - b)
    pc = np.abs(p - c)
    return np.where((pa <= pb) & (pa <= pc), a, np.where(pb <= pc, b, c))

def _unfilter_scanlines(raw: bytes, width: int, height: int, bpp: int) -> np.ndarray:
    """Reverse PNG per-scanline filtering. Returns (height, width, bpp) int32."""
    stride = width * bpp
    prev = np.zeros((width, bpp), dtype=np.int32)
    out = np.empty((height, width, bpp), dtype=np.int32)
    pos = 0

    for y in range(height):
        ftype = raw[pos]
        row = np.frombuffer(raw, dtype=np.uint8, count=stride, offset=pos + 1)
        row = row.astype(np.int32).reshape(width, bpp)
        pos += 1 + stride

        if ftype == 0:  # None
            recon = row
        elif ftype == 1:  # Sub: left neighbour, same scanline
            recon = np.cumsum(row, axis=0) % 256
        elif ftype == 2:  # Up: pixel directly above
            recon = (row + prev) % 256
        elif ftype in (3, 4):  # Average / Paeth: horizontal + vertical recurrence
            recon = np.empty_like(row)
            left = np.zeros(bpp, dtype=np.int32)
            zeros = np.zeros(bpp, dtype=np.int32)
            for x in range(width):
                above = prev[x]
                above_left = prev[x - 1] if x > 0 else zeros
                if ftype == 3:
                    predictor = (left + above) // 2
                else:
                    predictor = _paeth_predictor(left, above, above_left)
                recon[x] = (row[x] + predictor) % 256
                left = recon[x]
        else:
            raise ValueError(f"unsupported PNG filter type {ftype}")

        out[y] = recon
        prev = recon

    return out

def _png_bit_depth(path: Path):
    """Peek at a PNG's IHDR bit depth without decoding it. None if not a PNG."""
    with open(path, "rb") as f:
        header = f.read(29)
    if header[:8] != _PNG_SIGNATURE or header[12:16] != b"IHDR":
        return None
    return header[24]

def _read_png16_rgb(path: Path) -> np.ndarray:
    """Decode a 16-bit-per-channel RGB(A) PNG at full precision. Returns (H,W,3) uint16."""
    data = path.read_bytes()
    if data[:8] != _PNG_SIGNATURE:
        raise ValueError(f"{path.name}: not a PNG file")

    ihdr = None
    idat = bytearray()
    for ctype, cdata in _iter_png_chunks(data):
        if ctype == b"IHDR":
            width, height, bit_depth, color_type, _comp, _filt, interlace = \
                struct.unpack(">IIBBBBB", cdata)
            ihdr = (width, height, bit_depth, color_type, interlace)
        elif ctype == b"IDAT":
            idat += cdata
        elif ctype == b"PLTE":
            raise ValueError(f"{path.name}: palette-based PNGs are not supported")

    if ihdr is None:
        raise ValueError(f"{path.name}: missing IHDR chunk")
    width, height, bit_depth, color_type, interlace = ihdr

    if interlace != 0:
        raise ValueError(f"{path.name}: interlaced PNGs are not supported")
    if color_type not in (2, 6):
        raise ValueError(f"{path.name}: expected an RGB(A) colour type, got {color_type}")

    channels = 3 if color_type == 2 else 4
    bpp = channels * 2  # 16-bit samples: 2 bytes per channel

    raw = zlib.decompress(bytes(idat))
    unfiltered = _unfilter_scanlines(raw, width, height, bpp)  # (H, W, channels*2)

    hi = unfiltered[:, :, 0::2].astype(np.uint16)
    lo = unfiltered[:, :, 1::2].astype(np.uint16)
    samples = (hi << 8) | lo
    return samples[:, :, :3]

def load_hald(path: Path) -> np.ndarray:
    """Load a HaldCLUT PNG into a (S,S,S,3) float32 cube indexed [r, g, b]."""
    path = Path(path)

    if _png_bit_depth(path) == 16:
        arr = _read_png16_rgb(path)
        scale = np.float32(65535.0)
    else:
        img = Image.open(path)
        if img.mode != "RGB":
            img = img.convert("RGB")

        arr = np.asarray(img)
        if arr.ndim != 3 or arr.shape[2] < 3:
            raise ValueError(f"{path.name}: not an RGB image")
        arr = arr[:, :, :3]
        scale = np.float32(255.0)

    height, width = arr.shape[:2]
    if height != width:
        raise ValueError(f"{path.name}: HaldCLUT must be square, got {width}x{height}")

    # width == level**3, so level is its cube root.
    level = int(round(width ** (1.0 / 3.0)))
    if level ** 3 != width:
        raise ValueError(
            f"{path.name}: {width}px is not a cube number — not a HaldCLUT"
        )

    size = level * level
    flat = arr.reshape(-1, 3).astype(np.float32) / scale

    if flat.shape[0] != size ** 3:
        raise ValueError(f"{path.name}: expected {size ** 3} entries, got {flat.shape[0]}")

    # Raster order is [b, g, r]; we want [r, g, b].
    return np.ascontiguousarray(flat.reshape(size, size, size, 3).transpose(2, 1, 0, 3))
