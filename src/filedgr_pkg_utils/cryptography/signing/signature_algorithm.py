from typing import Protocol


class SignatureAlgorithm(Protocol):

    def sign(self, digest: bytes) -> bytes:
        ...

    def verify(self, digest: bytes, signature: bytes) -> bool:
        ...
