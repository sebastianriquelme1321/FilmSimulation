"""Named values shared across modules."""
import numpy as np

REC709_LUMA = (0.2126, 0.7152, 0.0722)
REC709_LUMA_F32 = np.array(REC709_LUMA, dtype=np.float32)
STRIP_ROWS = 256
JPEG_QUALITY = 95
