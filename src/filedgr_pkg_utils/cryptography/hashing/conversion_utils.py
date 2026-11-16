def convert_hex_str_to_bytes32(input: str) -> bytes:
    """
    Convert a hex string (with or without ``0x`` prefix) holding exactly 32 bytes,
    e.g. a keccak256/sha256 digest, into its raw ``bytes32`` value.

    :raises ValueError: if the string is not valid hex or does not decode to 32 bytes.
    """
    hex_str = input[2:] if input.startswith(("0x", "0X")) else input
    value = bytes.fromhex(hex_str)
    if len(value) != 32:
        raise ValueError(f"Expected 32 bytes for bytes32, got {len(value)} bytes.")
    return value
