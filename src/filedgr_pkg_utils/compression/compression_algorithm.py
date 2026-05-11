from typing import Protocol


class CompressionAlgorithm(Protocol):
    """Pure compression contract: handles bytes, files, and directories."""
    name: str

    def compress(self, data: bytes) -> bytes:
        ...

    def decompress(self, data: bytes) -> bytes:
        ...

    def compress_file(self, src: str, dest: str) -> None:
        ...

    def decompress_file(self, src: str, dest: str) -> None:
        ...

    def compress_folder(self, src: str, dest: str) -> None:
        ...

    def decompress_folder(self, src: str, dest: str) -> None:
        ...
