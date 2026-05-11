try:
    from PIL import Image
    import imagehash
    _HAS_IMAGE_DEPS = True
except ImportError:
    _HAS_IMAGE_DEPS = False

def _require_image_deps():
    if not _HAS_IMAGE_DEPS:
        raise ImportError(
            "Image hashing dependencies are missing. "
            "To use this feature, install the package with the 'images' extra: "
            "pip install 'filedgr-pkg-utils[images]'"
        )

class DHashAlgorithm:
    """
    Difference Hash (dHash) - Tracks gradients.
    Extremely fast and highly resistant to brightness/contrast changes.
    """
    name = "dhash"

    def __init__(self, hash_size: int = 8):
        self.hash_size = hash_size

    def hash_image(self, image_path: str) -> str:
        with Image.open(image_path) as img:
            return str(imagehash.dhash(img, hash_size=self.hash_size))

    def compute_distance(self, hash1: str, hash2: str) -> int:
        return imagehash.hex_to_hash(hash1) - imagehash.hex_to_hash(hash2)
