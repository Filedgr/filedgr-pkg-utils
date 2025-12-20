import abc


class SignatureUtils(abc.ABC):

    @abc.abstractmethod
    def factory(self):
        pass

    def sign_message(self, message_hash: str, sign_key_hex: str) -> str:
        util = self.factory()
        result = util.sign(message_hash=message_hash, sign_key_hex=sign_key_hex)
        return result

    def verify_signature(self, message_hash: str, signature: str, verifyKey_hex: str) -> bool:
        util = self.factory()
        result = util.verify_signature(message_hash=message_hash, signature=signature, verifyKey_hex=verifyKey_hex)
        return result
