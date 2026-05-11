import pytest
from pathlib import Path
from PIL import Image, ImageDraw

from filedgr_pkg_utils.images.hashing import PHashAlgorithm, AHashAlgorithm, DHashAlgorithm
from filedgr_pkg_utils.images.hashing.image_hash_utils import ImageHashUtils


# --- Fixtures for Generating Test Images ---

@pytest.fixture
def original_image(tmp_path: Path) -> Path:
    """Creates a simple geometric image."""
    img_path = tmp_path / "original.png"
    img = Image.new('RGB', (100, 100), color='white')
    draw = ImageDraw.Draw(img)
    draw.rectangle([20, 20, 80, 80], fill="blue")
    img.save(img_path)
    return img_path


@pytest.fixture
def similar_image(tmp_path: Path) -> Path:
    """Creates an image very similar to the original (slight color shift)."""
    img_path = tmp_path / "similar.png"
    img = Image.new('RGB', (100, 100), color='white')
    draw = ImageDraw.Draw(img)

    # FIX: Use an RGB value that is practically identical to "blue" (0, 0, 255)
    # This simulates a minor compression artifact or slight color grading.
    draw.rectangle([20, 20, 80, 80], fill=(0, 0, 245))

    img.save(img_path)
    return img_path


@pytest.fixture
def different_image(tmp_path: Path) -> Path:
    """Creates a completely different image."""
    img_path = tmp_path / "different.png"
    img = Image.new('RGB', (100, 100), color='black')
    draw = ImageDraw.Draw(img)
    draw.ellipse([10, 10, 90, 90], fill="red")
    img.save(img_path)
    return img_path


# --- Parameterized Algorithm Tests ---

@pytest.mark.parametrize("algo_class", [
    PHashAlgorithm,
    AHashAlgorithm,
    DHashAlgorithm
])
class TestImageHashingAlgorithms:

    def test_hash_generation(self, algo_class, original_image):
        """Test that the algorithm successfully generates a hash string."""
        utils = ImageHashUtils(algo_class())

        img_hash = utils.hash_image(str(original_image))

        assert isinstance(img_hash, str)
        assert len(img_hash) > 0
        # By default, imagehash returns 16-character hex strings for hash_size=8
        assert len(img_hash) == 16

    def test_similarity_logic(self, algo_class, original_image, similar_image, different_image):
        """Test that distance calculations and similarity checks work accurately."""
        utils = ImageHashUtils(algo_class())

        hash_orig = utils.hash_image(str(original_image))
        hash_sim = utils.hash_image(str(similar_image))
        hash_diff = utils.hash_image(str(different_image))

        # 1. An image should be identical to itself (distance 0)
        assert utils.compute_distance(hash_orig, hash_orig) == 0
        assert utils.is_similar(hash_orig, hash_orig, max_distance=0) is True

        # 2. Similar images should have a low distance
        dist_sim = utils.compute_distance(hash_orig, hash_sim)
        assert dist_sim <= 5  # Usually 0-2 for simple color shifts depending on the algo
        assert utils.is_similar(hash_orig, hash_sim, max_distance=5) is True

        # 3. Completely different images should have a high distance
        dist_diff = utils.compute_distance(hash_orig, hash_diff)
        assert dist_diff > 10  # A high Hamming distance
        assert utils.is_similar(hash_orig, hash_diff, max_distance=5) is False


# --- Utility Validation Tests ---

def test_file_not_found_validation(tmp_path):
    """Test that ImageHashUtils catches missing files gracefully."""
    utils = ImageHashUtils(PHashAlgorithm())
    missing_file = tmp_path / "does_not_exist.jpg"

    with pytest.raises(FileNotFoundError, match="Image not found"):
        utils.hash_image(str(missing_file))


def test_custom_hash_size(original_image):
    """Test that modifying the hash_size impacts the resulting hash length."""
    # A hash_size of 16 produces a 256-bit hash (64 hex characters)
    algo = PHashAlgorithm(hash_size=16)
    utils = ImageHashUtils(algo)

    img_hash = utils.hash_image(str(original_image))
    assert len(img_hash) == 64
