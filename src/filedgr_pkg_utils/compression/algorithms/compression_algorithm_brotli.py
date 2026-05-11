import brotli


class BrotliAlgorithm:
    name = "brotli"

    def __init__(self, quality: int = 11):
        """
        :param quality: 0 (fastest/lowest) to 11 (slowest/highest). Default is 11.
        """
        self.quality = quality

    def compress(self, data: bytes) -> bytes:
        return brotli.compress(data, quality=self.quality)

    def decompress(self, data: bytes) -> bytes:
        return brotli.decompress(data)

    def compress_file(self, src: str, dest: str) -> None:
        with open(src, 'rb') as f_in, open(dest, 'wb') as f_out:
            f_out.write(brotli.compress(f_in.read(), quality=self.quality))

    def decompress_file(self, src: str, dest: str) -> None:
        with open(src, 'rb') as f_in, open(dest, 'wb') as f_out:
            f_out.write(brotli.decompress(f_in.read()))

    def compress_folder(self, src: str, dest: str) -> None:
        raise NotImplementedError("Brotli does not natively support folder compression. Use a tarball instead.")

    def decompress_folder(self, src: str, dest: str) -> None:
        raise NotImplementedError("Brotli does not natively support folder decompression. Use a tarball instead.")
