import gzip
import shutil


class GzipAlgorithm:
    name = "gzip"

    def __init__(self, compresslevel: int = 9):
        """
        :param compresslevel: 1 (fastest/lowest) to 9 (slowest/highest). Default is 9.
        """
        self.compresslevel = compresslevel

    def compress(self, data: bytes) -> bytes:
        return gzip.compress(data, compresslevel=self.compresslevel)

    def decompress(self, data: bytes) -> bytes:
        return gzip.decompress(data)

    def compress_file(self, src: str, dest: str) -> None:
        with open(src, 'rb') as f_in:
            with gzip.open(dest, 'wb', compresslevel=self.compresslevel) as f_out:
                shutil.copyfileobj(f_in, f_out)

    def decompress_file(self, src: str, dest: str) -> None:
        with gzip.open(src, 'rb') as f_in:
            with open(dest, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)

    def compress_folder(self, src: str, dest: str) -> None:
        raise NotImplementedError("Gzip does not natively support folder compression. Use a tarball instead.")

    def decompress_folder(self, src: str, dest: str) -> None:
        raise NotImplementedError("Gzip does not natively support folder decompression. Use a tarball instead.")
