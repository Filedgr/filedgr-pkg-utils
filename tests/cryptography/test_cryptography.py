def test_signing_verifying():
    from filedgr_pkg_utils.cryptography.signing.secp256k1_signature_utils import SECP256k1SignatureUtils
    from ecdsa import SigningKey, SECP256k1
    import hashlib

    key_generate = SigningKey.generate(curve=SECP256k1)
    signKey_hex = key_generate.to_string().hex()
    verifyKey_hex = key_generate.verifying_key.to_string().hex()

    signatureUtils = SECP256k1SignatureUtils().factory()

    # message to sign
    message = "ECDSA message to sign"
    message_hash = hashlib.sha256(message.encode())
    message_hash_hex = message_hash.digest()
    signature = signatureUtils.sign_message(message_hash_hex, signKey_hex)
    result = signatureUtils.verify_message(message_hash_hex, signature, verifyKey_hex)

    assert result
