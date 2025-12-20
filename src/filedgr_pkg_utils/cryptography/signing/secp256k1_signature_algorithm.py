from ecdsa import SigningKey, SECP256k1, VerifyingKey, BadSignatureError


class Secp256k1Algorithm:

    def __init__(self,
                 sign_key_hex: str = None,
                 verify_key_hex: str = None):
        if sign_key_hex:
            self.__priv = SigningKey.from_string(bytes.fromhex(sign_key_hex), curve=SECP256k1)
        if verify_key_hex:
            self.__pub = VerifyingKey.from_string(bytes.fromhex(verify_key_hex), curve=SECP256k1)

    def sign(self, digest: bytes) -> bytes:
        return self.__priv.sign(digest)

    def verify(self, digest: bytes, signature: bytes) -> bool:
        try:
            return self.__pub.verify(signature, digest)
        except BadSignatureError:
            return False
