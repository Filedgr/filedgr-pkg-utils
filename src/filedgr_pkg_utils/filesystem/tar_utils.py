import os
import tarfile


class TarUtils:

    @staticmethod
    def create_tarball(source_path: str, dest_path: str, compression: str = "gz") -> None:
        """
        Creates a tarball from a file or directory.

        :param source_path: Path to the file or directory to archive.
        :param dest_path: Path where the tarball will be saved.
        :param compression: Compression type: 'gz' (default for .tar.gz), 'bz2', 'xz',
                            or '' (empty string for an uncompressed .tar).
        """
        if not os.path.exists(source_path):
            raise FileNotFoundError(f"Source path not found: {source_path}")

        # Construct the mode string (e.g., 'w:gz' or 'w')
        mode = f"w:{compression}" if compression else "w"

        with tarfile.open(dest_path, mode) as tar:
            # Using os.path.basename for arcname ensures we don't store absolute
            # paths in the archive, which makes extraction much cleaner.
            tar.add(source_path, arcname=os.path.basename(source_path))

    @staticmethod
    def extract_tarball(archive_path: str, dest_path: str) -> None:
        """
        Extracts a tarball to a specified directory.

        :param archive_path: Path to the tar archive.
        :param dest_path: Directory where the contents will be extracted.
        """
        if not os.path.isfile(archive_path):
            raise FileNotFoundError(f"Archive file not found: {archive_path}")

        # Ensure the destination directory exists
        os.makedirs(dest_path, exist_ok=True)

        # 'r:*' tells tarfile to automatically determine the compression method
        # (uncompressed, gzip, bzip2, or xz) by inspecting the file headers.
        with tarfile.open(archive_path, "r:*") as tar:
            # Note: In Python 3.12+, a 'filter' argument was added for extraction security.
            # Since your pyproject.toml specifies Python >= 3.11, we use the standard extractall.
            if hasattr(tarfile, 'data_filter'):
                tar.extractall(path=dest_path, filter='data')
            else:
                tar.extractall(path=dest_path)
