import pytest
from filedgr_pkg_utils.filesystem.atomic import atomic_write, async_atomic_write
from pathlib import Path


def test_atomic_write_success(tmp_path: Path):
    """Test that a successful write correctly replaces the file."""
    target_file = tmp_path / "data.txt"

    with atomic_write(target_file) as f:
        f.write("Hello World")

    assert target_file.exists()
    assert target_file.read_text() == "Hello World"

    # Ensure no temp files are left lingering
    assert len(list(tmp_path.iterdir())) == 1


def test_atomic_write_prevents_corruption_on_failure(tmp_path: Path):
    """Test that a crash during write leaves the original file untouched."""
    target_file = tmp_path / "critical_data.txt"

    # 1. Create the original file
    target_file.write_text("Original pristine data")

    # 2. Attempt an atomic write, but simulate a crash halfway through
    with pytest.raises(ValueError, match="System crash!"):
        with atomic_write(target_file) as f:
            f.write("New corrupted half-written ")
            raise ValueError("System crash!")

    # 3. Verify the original file is perfectly untouched
    assert target_file.read_text() == "Original pristine data"

    # 4. Verify the temp file was cleaned up properly
    assert len(list(tmp_path.iterdir())) == 1


def test_atomic_write_binary_mode(tmp_path: Path):
    """Test that it handles 'wb' mode without encoding conflicts."""
    target_file = tmp_path / "image.bin"

    binary_data = b"\x00\x01\x02\x03"

    with atomic_write(target_file, mode="wb") as f:
        f.write(binary_data)

    assert target_file.read_bytes() == binary_data


def test_atomic_write_creates_parent_directories(tmp_path: Path):
    """Test that it automatically builds the folder structure if it's missing."""
    target_file = tmp_path / "deeply" / "nested" / "folder" / "data.txt"

    with atomic_write(target_file) as f:
        f.write("Nested")

    assert target_file.exists()
    assert target_file.read_text() == "Nested"


@pytest.mark.asyncio
async def test_async_atomic_write_success(tmp_path: Path):
    target_file = tmp_path / "async_data.txt"

    async with async_atomic_write(target_file) as f:
        await f.write("Async Hello World")

    assert target_file.exists()
    assert target_file.read_text() == "Async Hello World"


@pytest.mark.asyncio
async def test_async_atomic_write_prevents_corruption(tmp_path: Path):
    target_file = tmp_path / "async_critical.txt"
    target_file.write_text("Pristine Data")

    with pytest.raises(RuntimeError, match="Async Crash"):
        async with async_atomic_write(target_file) as f:
            await f.write("Half written corrupt data...")
            raise RuntimeError("Async Crash")

    # File remains unharmed
    assert target_file.read_text() == "Pristine Data"
    # Temp files cleaned up
    assert len(list(tmp_path.iterdir())) == 1


@pytest.mark.asyncio
async def test_async_atomic_write_binary(tmp_path: Path):
    target_file = tmp_path / "async_image.bin"
    binary_data = b"\x00\xff\x00\xff"

    async with async_atomic_write(target_file, mode="wb") as f:
        await f.write(binary_data)

    assert target_file.read_bytes() == binary_data