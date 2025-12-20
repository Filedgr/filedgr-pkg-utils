from filedgr_pkg_utils.cryptography.signing.signature_utils import SignatureUtils
from ecdsa import SigningKey, VerifyingKey, SECP256k1, BadSignatureError


class _SEPC256k1Signature:

    def sign_message(self, message_hash: str, sign_key_hex: str) -> str:
        privKey = SigningKey.from_string(bytes.fromhex(sign_key_hex), curve=SECP256k1)
        return privKey.sign(message_hash)

    def verify_message(self, message_hash: str, signature: str, verifyKey_hex: str) -> bool:
        # load pubkey from string
        pubKey = VerifyingKey.from_string(bytes.fromhex(verifyKey_hex), curve=SECP256k1)
        try:
            # verify
            pubKey.verify(signature, message_hash)
            return True
        except BadSignatureError:
            return False


class SECP256k1SignatureUtils(SignatureUtils):

    def factory(self):
        return _SEPC256k1Signature()
