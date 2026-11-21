"""Reference sample images: bundled sample cards and the user's optional reference.jpg."""
import json
from pathlib import Path

import numpy as np
from PIL import Image

from .storage import library_dir

FOLDER = Path(__file__).parents[1]/'assets'/'reference'


def load_sample_cards(names) -> dict[str, np.ndarray]:
    """Precomputed sample cards (uint8 RGB) that exist for the given look names."""
    manifest_path = FOLDER/'manifest.json'
    manifest = (json.loads(manifest_path.read_text(encoding='utf-8'))
                if manifest_path.exists() else {})
    return {name: np.asarray(Image.open(FOLDER/manifest[name]).convert('RGB')).copy()
            for name in names if name in manifest and (FOLDER/manifest[name]).exists()}


def load_local_reference() -> Image.Image | None:
    """The user's own reference.jpg as a 240x160-bounded RGB image, or None."""
    local = library_dir()/'reference.jpg'
    if not local.exists():
        return None
    try:
        image = Image.open(local).convert('RGB')
        image.thumbnail((240, 160))
        return image
    except (OSError, ValueError):
        return None
