import hashlib
import numpy as np
from PIL import Image
from film_poc.hald_loader import load_hald
from film_poc.film_stocks import STOCKS,ASSETS,apply


def test_packaged_files_match_recorded_hashes():
    for info in STOCKS.values():
        assert hashlib.sha256((ASSETS/info['file']).read_bytes()).hexdigest()==info['sha256']


def test_hald_axis_order_with_identity(tmp_path):
    size=4
    n=np.arange(size**3)
    values=np.stack([n%size,(n//size)%size,n//size**2],axis=-1)/(size-1)
    path=tmp_path/'identity.png'
    Image.fromarray(np.rint(values.reshape(8,8,3)*255).astype(np.uint8)).save(path)
    cube=load_hald(path)
    np.testing.assert_allclose(cube[3,0,0],[1,0,0])
    np.testing.assert_allclose(cube[0,0,3],[0,0,1])


def test_film_stock_edges_and_strip_consistency():
    rgb=np.random.default_rng(22).random((20,30,3),dtype=np.float32)
    for stock in STOCKS:
        out=apply(rgb,stock)
        assert np.isfinite(out).all() and out.min()>=0 and out.max()<=1
        np.testing.assert_array_equal(out,np.concatenate([apply(rgb[:7],stock),apply(rgb[7:],stock)]))
        assert np.isfinite(apply(np.array([[[0,0,0],[1,1,1]]],dtype=np.float32),stock)).all()


def test_png16_reader_retains_low_bytes(tmp_path):
    import struct,zlib
    from film_poc.hald_loader import _read_png16_rgb
    pixels=np.array([[[257,512,65534],[1,32001,44003]]],dtype=np.uint16)
    def chunk(kind,data):
        return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data))
    raw=b'\x00'+pixels.astype('>u2').tobytes()
    data=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',2,1,16,2,0,0,0))+chunk(b'IDAT',zlib.compress(raw))+chunk(b'IEND',b'')
    path=tmp_path/'sixteen.png'
    path.write_bytes(data)
    np.testing.assert_array_equal(_read_png16_rgb(path),pixels)
