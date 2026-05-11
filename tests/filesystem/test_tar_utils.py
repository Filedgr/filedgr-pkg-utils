import pytest
from pathlib import Path

from filedgr_pkg_utils.filesystem.tar_utils import TarUtils


@pytest.fixture
def sample_data() -> bytes:
    return b"dummy data for tarball testing."


@pytest.fixture
def test_file(tmp_path: Path, sample_data: bytes) -> Path:
    file_path = tmp_path / "target_file.txt"
    file_path.write_bytes(sample_data)
    return file_path


@pytest.fixture
def test_dir(tmp_path: Path, sample_data: bytes) -> Path:
    dir_path = tmp_path / "target_dir"
    dir_path.mkdir()

    (dir_path / "file1.txt").write_bytes(sample_data)

    nested_dir = dir_path / "nested"
    nested_dir.mkdir()
    (nested_dir / "file2.txt").write_bytes(sample_data)

    return dir_path


class TestTarUtils:

    @pytest.mark.parametrize("compression, extension", [
        ("gz", ".tar.gz"),
        ("", ".tar"),  # Test uncompressed tarball
        ("bz2", ".tar.bz2")
    ])
    def test_create_and_extract_file(self, test_file, tmp_path, sample_data, compression, extension):
        archive_path = tmp_path / f"archive{extension}"
        output_dir = tmp_path / "output_dir"

        # Create tarball
        TarUtils.create_tarball(
            source_path=str(test_file),
            dest_path=str(archive_path),
            compression=compression
        )
        assert archive_path.exists()
        assert archive_path.stat().st_size > 0

        # Extract tarball
        TarUtils.extract_tarball(str(archive_path), str(output_dir))
        assert output_dir.exists()

        # Verify extracted file contents
        extracted_file = output_dir / test_file.name
        assert extracted_file.exists()
        assert extracted_file.read_bytes() == sample_data

    def test_create_and_extract_directory(self, test_dir, tmp_path, sample_data):
        archive_path = tmp_path / "folder_archive.tar.gz"
        output_dir = tmp_path / "output_dir"

        # Create folder tarball
        TarUtils.create_tarball(str(test_dir), str(archive_path), compression="gz")
        assert archive_path.exists()

        # Extract folder tarball
        TarUtils.extract_tarball(str(archive_path), str(output_dir))

        # Reconstruct paths to check
        extracted_root = output_dir / test_dir.name

        assert (extracted_root / "file1.txt").exists()
        assert (extracted_root / "file1.txt").read_bytes() == sample_data

        assert (extracted_root / "nested" / "file2.txt").exists()
        assert (extracted_root / "nested" / "file2.txt").read_bytes() == sample_data

    def test_missing_source_raises_error(self, tmp_path):
        bad_source = tmp_path / "does_not_exist.txt"
        dest_archive = tmp_path / "out.tar.gz"

        with pytest.raises(FileNotFoundError, match="Source path not found"):
            TarUtils.create_tarball(str(bad_source), str(dest_archive))

    def test_missing_archive_raises_error(self, tmp_path):
        bad_archive = tmp_path / "does_not_exist.tar.gz"
        dest_dir = tmp_path / "out"

        with pytest.raises(FileNotFoundError, match="Archive file not found"):
            TarUtils.extract_tarball(str(bad_archive), str(dest_dir))
