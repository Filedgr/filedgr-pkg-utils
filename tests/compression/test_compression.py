import pytest
from pathlib import Path

from filedgr_pkg_utils.compression import GzipAlgorithm, ZstdAlgorithm, BrotliAlgorithm, ZipAlgorithm
from filedgr_pkg_utils.compression.compression_utils import CompressionUtils


# --- Fixtures ---

@pytest.fixture
def sample_data() -> bytes:
    """Provides some generic compressible byte data."""
    return b"hello world filedgr compression test. " * 100


@pytest.fixture
def test_file(tmp_path: Path, sample_data: bytes) -> Path:
    """Provides a temporary file filled with sample data."""
    file_path = tmp_path / "test_file.txt"
    file_path.write_bytes(sample_data)
    return file_path


@pytest.fixture
def test_dir(tmp_path: Path, sample_data: bytes) -> Path:
    """Provides a temporary directory containing multiple files."""
    dir_path = tmp_path / "test_dir"
    dir_path.mkdir()
    (dir_path / "file1.txt").write_bytes(sample_data)
    (dir_path / "file2.txt").write_bytes(sample_data)

    # Add a nested directory to ensure recursive folder compression works
    nested_dir = dir_path / "nested"
    nested_dir.mkdir()
    (nested_dir / "file3.txt").write_bytes(sample_data)

    return dir_path


# --- Parameterized Tests for Common Operations ---

# These tests will run once for EVERY compression algorithm
@pytest.mark.parametrize("algo_class", [
    GzipAlgorithm,
    ZipAlgorithm,
    ZstdAlgorithm,
    BrotliAlgorithm
])
class TestCommonCompression:

    def test_compress_decompress_bytes(self, algo_class, sample_data):
        algo = algo_class()
        utils = CompressionUtils(algo)

        # Test Compression
        compressed = utils.compress(sample_data)
        assert isinstance(compressed, bytes)
        assert compressed != sample_data
        assert len(compressed) > 0

        # Test Decompression
        decompressed = utils.decompress(compressed)
        assert decompressed == sample_data

    def test_compress_decompress_file(self, algo_class, test_file, tmp_path, sample_data):
        algo = algo_class()
        utils = CompressionUtils(algo)

        compressed_path = tmp_path / f"compressed_{algo.name}.bin"
        decompressed_path = tmp_path / f"decompressed_{algo.name}.txt"

        # Test File Compression
        utils.compress_file(str(test_file), str(compressed_path))
        assert compressed_path.exists()
        assert compressed_path.stat().st_size > 0

        # Test File Decompression
        utils.decompress_file(str(compressed_path), str(decompressed_path))
        assert decompressed_path.exists()
        assert decompressed_path.read_bytes() == sample_data


# --- Specific Tests for Folder Operations ---

def test_zip_folder_compression_decompression(test_dir, tmp_path, sample_data):
    """Zip natively supports directory structures, so we test it specifically."""
    utils = CompressionUtils(ZipAlgorithm())

    archive_path = tmp_path / "archive.zip"
    output_dir = tmp_path / "output_dir"

    # Test Folder Compression
    utils.compress_folder(str(test_dir), str(archive_path))
    assert archive_path.exists()

    # Test Folder Decompression
    utils.decompress_folder(str(archive_path), str(output_dir))
    assert output_dir.exists()

    # Verify all nested contents match the original
    assert (output_dir / "file1.txt").read_bytes() == sample_data
    assert (output_dir / "file2.txt").read_bytes() == sample_data
    assert (output_dir / "nested" / "file3.txt").read_bytes() == sample_data


@pytest.mark.parametrize("algo_class", [
    GzipAlgorithm,
    ZstdAlgorithm,
    BrotliAlgorithm
])
def test_unsupported_folder_compression_raises(algo_class, test_dir, tmp_path):
    """Ensure algorithms that don't support folders raise NotImplementedError."""
    utils = CompressionUtils(algo_class())
    archive_path = tmp_path / f"archive_{algo_class.name}.bin"

    with pytest.raises(NotImplementedError, match="natively support folder compression"):
        utils.compress_folder(str(test_dir), str(archive_path))

    # Fix: Create a real dummy file so we bypass the `os.path.isfile` validation check
    # and actually test the algorithm's NotImplementedError logic.
    dummy_file = tmp_path / "dummy_file.bin"
    dummy_file.write_bytes(b"")

    with pytest.raises(NotImplementedError, match="natively support folder decompression"):
        utils.decompress_folder(str(dummy_file), "dummy_dest")


# --- Edge Cases and Validation Tests ---

def test_utils_validation_errors():
    """Test the type guards and file-existence checks in CompressionUtils."""
    utils = CompressionUtils(GzipAlgorithm())

    # Bytes Type Validation
    with pytest.raises(TypeError, match="Data to compress must be bytes"):
        utils.compress("this is a string, not bytes")  # type: ignore

    with pytest.raises(TypeError, match="Data to decompress must be bytes"):
        utils.decompress("this is a string, not bytes")  # type: ignore

    # File Existence Validation
    with pytest.raises(FileNotFoundError, match="Source file not found"):
        utils.compress_file("non_existent_file.txt", "out.gz")

    with pytest.raises(FileNotFoundError, match="Source file not found"):
        utils.decompress_file("non_existent_archive.gz", "out.txt")

    # Folder Existence Validation
    with pytest.raises(NotADirectoryError, match="Source directory not found"):
        utils.compress_folder("non_existent_folder", "out.zip")