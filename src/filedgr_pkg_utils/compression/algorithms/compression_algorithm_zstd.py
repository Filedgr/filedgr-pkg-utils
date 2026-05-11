import zstandard as zstd


class ZstdAlgorithm:
    name = "zstd"

    def __init__(self, level: int = 3):
        """
        :param level: 1 (fastest) to 22 (slowest/highest). Default is usually 3.
        """
        self.level = level

    def compress(self, data: bytes) -> bytes:
        compressor = zstd.ZstdCompressor(level=self.level)
        return compressor.compress(data)

    def decompress(self, data: bytes) -> bytes:
        decompressor = zstd.ZstdDecompressor()
        return decompressor.decompress(data)

    def compress_file(self, src: str, dest: str) -> None:
        cctx = zstd.ZstdCompressor(level=self.level)
        with open(src, 'rb') as f_in, open(dest, 'wb') as f_out:
            cctx.copy_stream(f_in, f_out)

    def decompress_file(self, src: str, dest: str) -> None:
        dctx = zstd.ZstdDecompressor()
        with open(src, 'rb') as f_in, open(dest, 'wb') as f_out:
            dctx.copy_stream(f_in, f_out)

    def compress_folder(self, src: str, dest: str) -> None:
        raise NotImplementedError("Zstd does not natively support folder compression. Use a tarball instead.")

    def decompress_folder(self, src: str, dest: str) -> None:
        raise NotImplementedError("Zstd does not natively support folder decompression. Use a tarball instead.")
