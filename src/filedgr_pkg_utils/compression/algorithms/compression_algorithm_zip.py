import os
import shutil
import zipfile
import zlib


class ZipAlgorithm:
    name = "zip"

    def __init__(self, compresslevel: int = 6):
        """
        :param compresslevel: 0 (no compression), 1 (fastest) to 9 (slowest/highest).
                              Default is 6 zlib default.
        """
        self.compresslevel = compresslevel

    def compress(self, data: bytes) -> bytes:
        return zlib.compress(data, level=self.compresslevel)

    def decompress(self, data: bytes) -> bytes:
        return zlib.decompress(data)

    def compress_file(self, src: str, dest: str) -> None:
        with zipfile.ZipFile(dest, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=self.compresslevel) as zf:
            zf.write(src, arcname=os.path.basename(src))

    def decompress_file(self, src: str, dest: str) -> None:
        with zipfile.ZipFile(src, 'r') as zf:
            names = zf.namelist()
            if not names:
                return
            with zf.open(names[0]) as f_in, open(dest, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

    def compress_folder(self, src: str, dest: str) -> None:
        with zipfile.ZipFile(dest, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=self.compresslevel) as zf:
            for root, _, files in os.walk(src):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, start=src)
                    zf.write(file_path, arcname=arcname)

    def decompress_folder(self, src: str, dest: str) -> None:
        with zipfile.ZipFile(src, 'r') as zf:
            zf.extractall(path=dest)
