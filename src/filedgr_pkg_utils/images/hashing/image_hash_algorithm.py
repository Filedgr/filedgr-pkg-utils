from typing import Protocol

# --- Optional Dependency Guard ---
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

class ImageHashAlgorithm(Protocol):
    """Protocol for perceptual image hashing algorithms."""
    name: str

    def hash_image(self, image_path: str) -> str:
        """Generates a perceptual hash as a hex string."""
        ...

    def compute_distance(self, hash1: str, hash2: str) -> int:
        """Computes the Hamming distance between two hex hashes."""
        ...
