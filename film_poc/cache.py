"""Disposable local caches; failed/corrupt caches always fall back to calculation."""
import hashlib
import os
from pathlib import Path
import tempfile
import numpy as np
from .user_library import library_dir


def cached_array(namespace, token, build, shape):
    path=library_dir()/'cache'/namespace/(hashlib.sha256(token.encode()).hexdigest()+'.npy')
    try:
        result=np.load(path,allow_pickle=False,mmap_mode='r')
        if result.shape==shape and result.dtype in (np.dtype('float32'),np.dtype('float64')) and np.isfinite(result).all():
            return result
    except (OSError,ValueError,EOFError):
        pass
    result=build()
    temporary=None
    try:
        path.parent.mkdir(parents=True,exist_ok=True)
        fd,temporary=tempfile.mkstemp(suffix='.npy',dir=path.parent)
        with os.fdopen(fd,'wb') as stream:
            np.save(stream,result,allow_pickle=False)
        os.replace(temporary,path)
    except OSError:
        pass
    finally:
        if temporary and os.path.exists(temporary):
            try: os.unlink(temporary)
            except OSError: pass
    return result
