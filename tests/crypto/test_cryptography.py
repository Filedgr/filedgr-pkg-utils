from filedgr_pkg_utils.cryptography.signing.secp256k1_signature_algorithm import Secp256k1Algorithm


def test_signing_verifying():
    import hashlib

    from cryptography.hazmat.primitives.asymmetric import ec

    from filedgr_pkg_utils.cryptography.signing.signature_utils import SignatureUtils

    private_key = ec.generate_private_key(ec.SECP256K1())
    sign_key_hex = private_key.private_numbers().private_value.to_bytes(32, "big").hex()
    public_numbers = private_key.public_key().public_numbers()
    verify_key_hex = (
        public_numbers.x.to_bytes(32, "big") + public_numbers.y.to_bytes(32, "big")
    ).hex()

    signature_utils = SignatureUtils(algo=Secp256k1Algorithm(
        sign_key_hex=sign_key_hex,
        verify_key_hex=verify_key_hex
    ))

    # message to sign
    message = "ECDSA message to sign"
    message_hash = hashlib.sha256(message.encode())
    message_hash_hex = message_hash.digest().hex()
    signature = signature_utils.sign(message_hash_hex)
    result = signature_utils.verify(message_hash_hex, signature)

    assert result


def test_verify_rejects_tampered_signature():
    import hashlib

    from cryptography.hazmat.primitives.asymmetric import ec

    from filedgr_pkg_utils.cryptography.signing.signature_utils import SignatureUtils

    private_key = ec.generate_private_key(ec.SECP256K1())
    sign_key_hex = private_key.private_numbers().private_value.to_bytes(32, "big").hex()
    public_numbers = private_key.public_key().public_numbers()
    verify_key_hex = (
        public_numbers.x.to_bytes(32, "big") + public_numbers.y.to_bytes(32, "big")
    ).hex()

    signature_utils = SignatureUtils(algo=Secp256k1Algorithm(
        sign_key_hex=sign_key_hex,
        verify_key_hex=verify_key_hex
    ))

    digest_hex = hashlib.sha256(b"a message").digest().hex()
    other_digest_hex = hashlib.sha256(b"another message").digest().hex()
    signature = signature_utils.sign(digest_hex)

    assert signature_utils.verify(other_digest_hex, signature) is False
