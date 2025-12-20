from filedgr_pkg_utils.cryptography.signing.secp256k1_signature_algorithm import Secp256k1Algorithm


def test_signing_verifying():
    from filedgr_pkg_utils.cryptography.signing.signature_utils import SignatureUtils
    from ecdsa import SigningKey, SECP256k1
    import hashlib

    key_generate = SigningKey.generate(curve=SECP256k1)
    sign_key_hex = key_generate.to_string().hex()
    verify_key_hex = key_generate.verifying_key.to_string().hex()

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
