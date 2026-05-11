import os
from filedgr_pkg_utils.images.hashing.image_hash_algorithm import ImageHashAlgorithm


class ImageHashUtils:
    def __init__(self, algorithm: ImageHashAlgorithm):
        self.algorithm = algorithm

    def hash_image(self, image_path: str) -> str:
        """
        Generates a perceptual hash for the given image.
        """
        if not os.path.isfile(image_path):
            raise FileNotFoundError(f"Image not found: {image_path}")
        return self.algorithm.hash_image(image_path)

    def compute_distance(self, hash1: str, hash2: str) -> int:
        """
        Computes the Hamming distance between two hashes.
        A distance of 0 means the hashes are identical.
        """
        # Cast to a native Python int to prevent leaking NumPy integer types
        return int(self.algorithm.compute_distance(hash1, hash2))

    def is_similar(self, hash1: str, hash2: str, max_distance: int = 5) -> bool:
        """
        Determines if two hashes are considered "similar".
        """
        distance = self.compute_distance(hash1, hash2)
        # Cast to a native Python bool to prevent leaking NumPy np.True_ / np.False_
        return bool(distance <= max_distance)
