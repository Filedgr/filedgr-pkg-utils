import os
from filedgr_pkg_utils.compression.compression_algorithm import CompressionAlgorithm


class CompressionUtils:
    def __init__(self, algorithm: CompressionAlgorithm):
        self.algorithm = algorithm

    def compress(self, data: bytes) -> bytes:
        if not isinstance(data, bytes):
            raise TypeError("Data to compress must be bytes.")
        return self.algorithm.compress(data)

    def decompress(self, data: bytes) -> bytes:
        if not isinstance(data, bytes):
            raise TypeError("Data to decompress must be bytes.")
        return self.algorithm.decompress(data)

    def compress_file(self, src_path: str, dest_path: str) -> None:
        if not os.path.isfile(src_path):
            raise FileNotFoundError(f"Source file not found: {src_path}")
        self.algorithm.compress_file(src_path, dest_path)

    def decompress_file(self, src_path: str, dest_path: str) -> None:
        if not os.path.isfile(src_path):
            raise FileNotFoundError(f"Source file not found: {src_path}")
        self.algorithm.decompress_file(src_path, dest_path)

    def compress_folder(self, src_path: str, dest_path: str) -> None:
        if not os.path.isdir(src_path):
            raise NotADirectoryError(f"Source directory not found: {src_path}")
        self.algorithm.compress_folder(src_path, dest_path)

    def decompress_folder(self, src_path: str, dest_path: str) -> None:
        if not os.path.isfile(src_path):
            raise FileNotFoundError(f"Compressed source file not found: {src_path}")
        self.algorithm.decompress_folder(src_path, dest_path)
