from filedgr_pkg_utils._optional import require

Image = require("PIL.Image", "images", "AHashAlgorithm")
imagehash = require("imagehash", "images", "AHashAlgorithm")


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
