from typing import Protocol, BinaryIO
import hashlib

from eth_hash.auto import keccak


class HashAlgorithm(Protocol):
    """Pure hashing contract: bytes in, digest bytes out."""
    name: str

    def hash_bytes(self, data: bytes) -> bytes:
        ...

    def hash_file(self, path: str, chunk_size: int = 1024 * 1024) -> bytes:
        ...

    def hash_stream(self, stream: BinaryIO, chunk_size: int = 1024 * 1024) -> bytes:
        ...


class Sha256Algorithm:
    name = "sha256"

    def hash_bytes(self, data: bytes) -> bytes:
        return hashlib.sha256(data).digest()

    def hash_file(self, path: str, chunk_size: int = 1024 * 1024) -> bytes:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                h.update(chunk)
        return h.digest()

    def hash_stream(self, stream: BinaryIO, chunk_size: int = 1024 * 1024) -> bytes:
        h = hashlib.sha256()
        while chunk := stream.read(chunk_size):
            h.update(chunk)
        return h.digest()


class Sha512Algorithm:
    name = "sha512"

    def hash_bytes(self, data: bytes) -> bytes:
        return hashlib.sha512(data).digest()

    def hash_file(self, path: str, chunk_size: int = 1024 * 1024) -> bytes:
        h = hashlib.sha512()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                h.update(chunk)
        return h.digest()

    def hash_stream(self, stream: BinaryIO, chunk_size: int = 1024 * 1024) -> bytes:
        h = hashlib.sha512()
        while chunk := stream.read(chunk_size):
            h.update(chunk)
        return h.digest()


class Blake2bAlgorithm:
    name = "blake2b"

    def __init__(self, digest_size: int = 32):
        # 32 bytes == 256-bit, 64 bytes == 512-bit
        self.digest_size = digest_size

    def hash_bytes(self, data: bytes) -> bytes:
        return hashlib.blake2b(data, digest_size=self.digest_size).digest()

    def hash_file(self, path: str, chunk_size: int = 1024 * 1024) -> bytes:
        h = hashlib.blake2b(digest_size=self.digest_size)
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                h.update(chunk)
        return h.digest()

    def hash_stream(self, stream: BinaryIO, chunk_size: int = 1024 * 1024) -> bytes:
        h = hashlib.blake2b(digest_size=self.digest_size)
        while chunk := stream.read(chunk_size):
            h.update(chunk)
        return h.digest()


class Keccak256Algorithm:
    """
    Keccak-256 (Ethereum standard) via eth-hash.
    """
    name = "keccak256"

    def hash_bytes(self, data: bytes) -> bytes:
        return keccak(data)

    def hash_file(self, path: str, chunk_size: int = 1024 * 1024) -> bytes:
        raise NotImplementedError("keccak of the web3 libraries does not expose a streaming API")

    def hash_stream(self, stream: BinaryIO, chunk_size: int = 1024 * 1024) -> bytes:
        h = hashlib.sha256()
        while chunk := stream.read(chunk_size):
            h.update(chunk)
        return h.digest()

