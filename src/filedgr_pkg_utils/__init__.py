from importlib.metadata import PackageNotFoundError, version as _version

# Set at build time from the release tag (setuptools-scm), read from the
# installed package's metadata.
try:
    __version__ = _version("filedgr-pkg-utils")
except PackageNotFoundError:  # running from a source checkout without installing
    __version__ = "0.0.0+unknown"
