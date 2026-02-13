from typing import Union, BinaryIO

from filedgr_pkg_utils.cryptography.hashing.hash_algorithm import HashAlgorithm


class HashUtils:
    def __init__(self, algorithm: HashAlgorithm):
        self.algorithm = algorithm

    def hash_message(self, message: Union[str, bytes], *, encoding: str = "utf-8") -> str:
        data = message.encode(encoding) if isinstance(message, str) else message
        return f"0x{self.algorithm.hash_bytes(data).hex()}"

    def hash_file(self, path: str, *, chunk_size: int = 1024 * 1024) -> str:
        return f"0x{self.algorithm.hash_file(path, chunk_size=chunk_size).hex()}"

    def hash_stream(self, stream: BinaryIO, *, chunk_size: int = 1024 * 1024) -> str:
        return f"0x{self.algorithm.hash_stream(stream, chunk_size=chunk_size).hex()}"
