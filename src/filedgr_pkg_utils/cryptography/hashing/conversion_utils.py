def convert_hex_str_to_bytes32(input: str) -> bytes:
    from web3 import Web3
    bytes32_value = Web3.to_bytes(text=input)
    return bytes32_value
