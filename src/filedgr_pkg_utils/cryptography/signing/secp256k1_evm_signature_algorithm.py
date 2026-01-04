from eth_account import Account


class Secp256k1EvmAlgorithm:

    def __init__(self,
                 sign_key_hex: str = None,
                 verify_key_hex: str = None):
        if sign_key_hex:
            self.__priv = sign_key_hex if sign_key_hex.startswith("0x") else "0x" + sign_key_hex

    def sign(self, digest: str) -> str:
        digest = bytes.fromhex(digest[2:] if digest.startswith("0x") else digest)
        if len(digest) != 32:
            raise ValueError("digest must be 32 bytes")
        signed = Account.unsafe_sign_hash(digest, private_key=self.__priv)
        return signed.signature.hex()

    def verify(self, digest: bytes, signature: bytes) -> bool:
        raise NotImplementedError()
