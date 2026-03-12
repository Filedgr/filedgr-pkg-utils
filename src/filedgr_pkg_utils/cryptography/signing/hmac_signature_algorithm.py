import hashlib
import hmac


class HmacAlgorithm:

    def __init__(self, secret: bytes):
        self.__secret = secret

    def sign(self, digest: bytes) -> bytes:
        return hmac.new(self.__secret, digest, hashlib.sha256).digest()

    def verify(self, digest: bytes, signature: bytes) -> bool:
        expected_signature = self.sign(digest)
        return hmac.compare_digest(expected_signature, signature)
