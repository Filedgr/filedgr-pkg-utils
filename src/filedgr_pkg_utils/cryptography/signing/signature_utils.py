from filedgr_pkg_utils.cryptography.signing.signature_algorithm import SignatureAlgorithm


class SignatureUtils:

    def __init__(self, algo: SignatureAlgorithm):
        self.algo = algo

    def sign(self, digest: str) -> str:
        """
        :param digest: The hash as a hex string
        :return: The signature as a hex string
        """
        if digest.startswith("0x"):
            digest = digest[2:]
        digest = bytes.fromhex(digest)
        return f"0x{self.algo.sign(digest).hex()}"

    def verify(self, digest: str, signature: str) -> bool:
        """
        :param digest: The hash as a hex string
        :param signature: The signature as a hex string
        :return: True/False
        """
        if signature.startswith("0x"):
            signature = signature[2:]
        signature = bytes.fromhex(signature)
        if digest.startswith("0x"):
            digest = digest[2:]
        digest = bytes.fromhex(digest)
        return self.algo.verify(digest, signature)
