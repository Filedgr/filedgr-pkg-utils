from typing import Tuple


def sig_hex_to_vrs(signature_hex: str) -> Tuple[int, bytes, bytes]:
    if signature_hex.startswith(("0x", "0X")):
        signature_hex = signature_hex[2:]

    sig = bytes.fromhex(signature_hex)

    if len(sig) != 65:
        raise ValueError(f"Expected 65-byte signature (r||s||v). Got {len(sig)} bytes.")

    r = int.from_bytes(sig[0:32], "big")
    s = int.from_bytes(sig[32:64], "big")
    v = sig[64]

    # Normalize v into what your Solidity expects.
    # Many contracts accept 27/28; many clients produce 0/1.
    if v in (0, 1):
        v += 27
    if v not in (27, 28):
        raise ValueError(f"Invalid v value: {v}")

    # Return as Solidity-ready types:
    r_bytes32 = r.to_bytes(32, "big")
    s_bytes32 = s.to_bytes(32, "big")
    return v, r_bytes32, s_bytes32
