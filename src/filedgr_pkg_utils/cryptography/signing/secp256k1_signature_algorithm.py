# Third party imports
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import (
    decode_dss_signature,
    encode_dss_signature,
)

_CURVE = ec.SECP256K1()
_HASH = hashes.SHA256()
_ORDER_BYTES = 32


class Secp256k1Algorithm:
    """secp256k1 signer/verifier backed by OpenSSL (``cryptography``).

    Keys are exchanged as raw hex: the private key is the 32-byte scalar and
    the public key is the uncompressed point ``x || y`` (64 bytes, no prefix).
    Signatures are the raw ``r || s`` pair (64 bytes).
    """

    def __init__(self,
                 sign_key_hex: str = None,
                 verify_key_hex: str = None):
        if sign_key_hex:
            secret = int.from_bytes(bytes.fromhex(sign_key_hex), "big")
            self.__priv = ec.derive_private_key(secret, _CURVE)
        if verify_key_hex:
            point = b"\x04" + bytes.fromhex(verify_key_hex)
            self.__pub = ec.EllipticCurvePublicKey.from_encoded_point(_CURVE, point)

    def sign(self, digest: bytes) -> bytes:
        der_signature = self.__priv.sign(digest, ec.ECDSA(_HASH))
        r, s = decode_dss_signature(der_signature)
        return r.to_bytes(_ORDER_BYTES, "big") + s.to_bytes(_ORDER_BYTES, "big")

    def verify(self, digest: bytes, signature: bytes) -> bool:
        r = int.from_bytes(signature[:_ORDER_BYTES], "big")
        s = int.from_bytes(signature[_ORDER_BYTES:], "big")
        der_signature = encode_dss_signature(r, s)
        try:
            self.__pub.verify(der_signature, digest, ec.ECDSA(_HASH))
            return True
        except InvalidSignature:
            return False
