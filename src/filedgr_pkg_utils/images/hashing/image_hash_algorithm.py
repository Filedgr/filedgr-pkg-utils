from typing import Protocol
from PIL import Image
import imagehash


class ImageHashAlgorithm(Protocol):
    """Protocol for perceptual image hashing algorithms."""
    name: str

    def hash_image(self, image_path: str) -> str:
        """Generates a perceptual hash as a hex string."""
        ...

    def compute_distance(self, hash1: str, hash2: str) -> int:
        """Computes the Hamming distance between two hex hashes."""
        ...


class PHashAlgorithm:
    """
    Perceptual Hash (pHash) - Uses Discrete Cosine Transform (DCT).
    Great for general image similarity, highly resistant to compression and resizing.
    """
    name = "phash"

    def __init__(self, hash_size: int = 8):
        self.hash_size = hash_size

    def hash_image(self, image_path: str) -> str:
        with Image.open(image_path) as img:
            return str(imagehash.phash(img, hash_size=self.hash_size))

    def compute_distance(self, hash1: str, hash2: str) -> int:
        return imagehash.hex_to_hash(hash1) - imagehash.hex_to_hash(hash2)


class AHashAlgorithm:
    """
    Average Hash (aHash) - Fast but less accurate.
    Good for finding exact duplicates that might have slight color shifts.
    """
    name = "ahash"

    def __init__(self, hash_size: int = 8):
        self.hash_size = hash_size

    def hash_image(self, image_path: str) -> str:
        with Image.open(image_path) as img:
            return str(imagehash.average_hash(img, hash_size=self.hash_size))

    def compute_distance(self, hash1: str, hash2: str) -> int:
        return imagehash.hex_to_hash(hash1) - imagehash.hex_to_hash(hash2)


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
