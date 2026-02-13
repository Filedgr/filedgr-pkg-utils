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
    algo = Sha256Algorithm()

    data = b"hello world" * 1000  # Making it large enough to cross chunk boundaries
    stream = BytesIO(data)

    stream_hash = algo.hash_stream(stream, chunk_size=128)
    direct_hash = algo.hash_bytes(data)

    assert stream_hash == direct_hash
