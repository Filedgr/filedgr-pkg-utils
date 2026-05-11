from typing import Protocol


class ImageHashAlgorithm(Protocol):
    """Protocol for perceptual image hashing algorithms."""
    name: str

    def hash_image(self, image_path: str) -> str:
        """Generates a perceptual hash as a hex string."""
        ...

    def compute_distance(self, hash1: str, hash2: str) -> int:
        """Computes the Hamming distance between two hex hashes."""
        ...
