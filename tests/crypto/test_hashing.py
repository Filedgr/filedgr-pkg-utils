from io import BytesIO

from filedgr_pkg_utils.cryptography.hashing.hash_algorithm import Sha256Algorithm
from filedgr_pkg_utils.cryptography.hashing.hash_utils import HashUtils


def test_hashing_message():
    hash_utils = HashUtils(algorithm=Sha256Algorithm())

    msg_to_hash = "hello world"
    hash = hash_utils.hash_message(msg_to_hash)

    known_result = "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
    assert hash[2:] == known_result

def test_hashing_file():
    from pathlib import Path
    import pathlib
    patt = pathlib.Path(__file__).parent.resolve()
    file_path = Path(patt, "hash_test.txt")

    hash_utils = HashUtils(algorithm=Sha256Algorithm())

    hash = hash_utils.hash_file(str(file_path))
    known_result = "474ec887e7b3c4d899ad5b6b707097a0d828a2d0440c23781b06f31481797bbf"

    assert hash[2:] == known_result

def test_hash_stream():
    hash_utils = HashUtils(algorithm=Sha256Algorithm())

    data = b"hello world" * 1000  # Making it large enough to cross chunk boundaries
    stream = BytesIO(data)

    stream_hash = hash_utils.hash_stream(stream=stream, chunk_size=128)
    direct_hash = hash_utils.hash_message(message=data)

    assert stream_hash == direct_hash


# keccak256("") and keccak256("hello world") known-answer vectors (Ethereum keccak, not SHA3-256)
KECCAK_EMPTY = "c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470"
KECCAK_HELLO = "47173285a8d7341e5e972fc677286384f802f8ef42a5ec5f03bbfa254cb01fad"


def test_keccak_known_vectors():
    from filedgr_pkg_utils.cryptography.hashing.hash_algorithm import Keccak256Algorithm
    hash_utils = HashUtils(algorithm=Keccak256Algorithm())
    assert hash_utils.hash_message(b"") == "0x" + KECCAK_EMPTY
    assert hash_utils.hash_message("hello world") == "0x" + KECCAK_HELLO


def test_keccak_stream_matches_message():
    from filedgr_pkg_utils.cryptography.hashing.hash_algorithm import Keccak256Algorithm
    hash_utils = HashUtils(algorithm=Keccak256Algorithm())
    data = b"hello world" * 1000
    assert hash_utils.hash_stream(BytesIO(data), chunk_size=128) == hash_utils.hash_message(data)
    assert hash_utils.hash_stream(BytesIO(b"hello world"), chunk_size=3) == "0x" + KECCAK_HELLO


def test_keccak_file(tmp_path):
    from filedgr_pkg_utils.cryptography.hashing.hash_algorithm import Keccak256Algorithm
    path = tmp_path / "f.txt"
    path.write_bytes(b"hello world")
    hash_utils = HashUtils(algorithm=Keccak256Algorithm())
    assert hash_utils.hash_file(str(path), chunk_size=4) == "0x" + KECCAK_HELLO


def test_convert_hex_str_to_bytes32():
    import pytest
    from filedgr_pkg_utils.cryptography.hashing.conversion_utils import convert_hex_str_to_bytes32

    expected = bytes.fromhex(KECCAK_HELLO)
    assert convert_hex_str_to_bytes32("0x" + KECCAK_HELLO) == expected
    assert convert_hex_str_to_bytes32(KECCAK_HELLO.upper()) == expected
    with pytest.raises(ValueError):
        convert_hex_str_to_bytes32("0xab")
    with pytest.raises(ValueError):
        convert_hex_str_to_bytes32("0x" + "zz" * 32)
