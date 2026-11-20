"""
The base install must work without any optional dependency, and each optional
feature must fail with an ImportError naming the extra to install.

Each check runs in a fresh interpreter in which the optional packages are made
unimportable, simulating `pip install filedgr-pkg-utils` without extras.
"""
import subprocess
import sys
import textwrap
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

# Top-level modules provided by each extra
EXTRA_MODULES = {
    "canonical": ["pydantic", "pydantic_core", "orjson", "rfc8785"],
    "crypto": ["cryptography"],
    "evm": ["eth_account", "eth_hash", "web3"],
    "compression": ["zstandard", "brotli"],
    "async": ["aiofiles"],
    "images": ["PIL", "imagehash"],
}
ALL_OPTIONAL = sorted({m for mods in EXTRA_MODULES.values() for m in mods})

BLOCKER = textwrap.dedent("""
    import sys
    BLOCKED = set({blocked!r})

    class _Blocker:
        def find_spec(self, name, path=None, target=None):
            if name.split(".")[0] in BLOCKED:
                raise ModuleNotFoundError(f"No module named {{name!r}} (blocked by test)", name=name)
            return None

    sys.meta_path.insert(0, _Blocker())
    sys.path.insert(0, {src!r})
""")


def run_without(blocked, code):
    script = BLOCKER.format(blocked=sorted(blocked), src=str(ROOT / "src")) + textwrap.dedent(code)
    return subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, cwd=ROOT)


def test_base_features_work_without_any_extra():
    result = run_without(ALL_OPTIONAL, """
        import io
        from filedgr_pkg_utils import __version__
        from filedgr_pkg_utils.caching import ttl_cache
        from filedgr_pkg_utils.resilience import retry, circuit_breaker, rate_limit, timeout, fallback
        from filedgr_pkg_utils.hooks.decorators import post_action, fire_and_forget
        from filedgr_pkg_utils.security.sanitizer import sanitize_data
        from filedgr_pkg_utils.security.sanitizer_decorators import sanitize_return
        from filedgr_pkg_utils.fldgr_logging import LoggerFactory, JsonFormatter
        from filedgr_pkg_utils.filesystem import TarUtils
        from filedgr_pkg_utils.filesystem.atomic import atomic_write, async_atomic_write
        from filedgr_pkg_utils.evm import normalize_hex
        from filedgr_pkg_utils.mixins.without_keys_mixin import WithoutKeysMixin
        from filedgr_pkg_utils.converters.abstract_converter import AbstractConverter
        from filedgr_pkg_utils.compression import CompressionUtils, GzipAlgorithm, ZipAlgorithm
        from filedgr_pkg_utils.cryptography.hashing.hash_algorithm import (
            Sha256Algorithm, Sha512Algorithm, Blake2bAlgorithm, Keccak256Algorithm,
        )
        from filedgr_pkg_utils.cryptography.hashing.hash_utils import HashUtils
        from filedgr_pkg_utils.cryptography.hashing.conversion_utils import convert_hex_str_to_bytes32
        from filedgr_pkg_utils.cryptography.signing import HmacAlgorithm, SignatureUtils, sig_hex_to_vrs
        from filedgr_pkg_utils.images.hashing import ImageHashUtils

        assert CompressionUtils(GzipAlgorithm()).decompress(CompressionUtils(GzipAlgorithm()).compress(b"x")) == b"x"
        assert HashUtils(Sha256Algorithm()).hash_message("a").startswith("0x")
        assert SignatureUtils(HmacAlgorithm(b"k")).sign("0x" + "00" * 32).startswith("0x")
        assert sanitize_data({"password": "p"}) == {"password": "*****"}
        print("ok")
    """)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "ok"


@pytest.mark.parametrize("extra, statement", [
    ("canonical", "from filedgr_pkg_utils.canonicalization import CanonicalJsonMixin"),
    ("canonical", "from filedgr_pkg_utils.canonicalization import CanonicalJsonMixinV2"),
    ("crypto", "from filedgr_pkg_utils.cryptography.signing import Secp256k1Algorithm"),
    ("evm", "from filedgr_pkg_utils.cryptography.signing import Secp256k1EvmAlgorithm"),
    ("evm", "from filedgr_pkg_utils.cryptography.hashing.hash_algorithm import Keccak256Algorithm; Keccak256Algorithm()"),
    ("compression", "from filedgr_pkg_utils.compression import ZstdAlgorithm"),
    ("compression", "from filedgr_pkg_utils.compression import BrotliAlgorithm"),
    ("async", """
        import asyncio
        from filedgr_pkg_utils.filesystem.atomic import async_atomic_write
        async def main():
            async with async_atomic_write("x.txt"):
                pass
        asyncio.run(main())
    """),
    ("images", "from filedgr_pkg_utils.images.hashing import PHashAlgorithm"),
])
def test_missing_extra_gives_install_hint(extra, statement):
    result = run_without(EXTRA_MODULES[extra], statement)
    assert result.returncode != 0
    assert "ImportError" in result.stderr
    assert f'pip install "filedgr-pkg-utils[{extra}]"' in result.stderr, result.stderr


def test_each_extra_only_needs_its_own_packages():
    """With only one extra's packages available, that extra's features import."""
    features = {
        "canonical": "from filedgr_pkg_utils.canonicalization import CanonicalJsonMixin, CanonicalJsonMixinV2",
        "crypto": "from filedgr_pkg_utils.cryptography.signing import Secp256k1Algorithm",
        "evm": (
            "from filedgr_pkg_utils.cryptography.signing import Secp256k1EvmAlgorithm\n"
            "from filedgr_pkg_utils.cryptography.hashing.hash_algorithm import Keccak256Algorithm\n"
            "Keccak256Algorithm().hash_bytes(b'')"
        ),
        "compression": "from filedgr_pkg_utils.compression import ZstdAlgorithm, BrotliAlgorithm",
        "async": "import aiofiles",
        "images": "from filedgr_pkg_utils.images.hashing import AHashAlgorithm, DHashAlgorithm, PHashAlgorithm",
    }
    failures = {}
    for extra, code in features.items():
        # evm's eth_account itself needs pydantic, so don't block what the extra pulls in
        blocked = [m for m in ALL_OPTIONAL if m not in EXTRA_MODULES[extra]]
        if extra == "evm":
            blocked = [m for m in blocked if m not in ("pydantic", "pydantic_core")]
        result = run_without(blocked, code)
        if result.returncode != 0:
            failures[extra] = result.stderr[-500:]
    assert failures == {}


def test_pyproject_all_extra_covers_every_extra():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    assert project["dependencies"] == []
    extras = project["optional-dependencies"]
    assert set(EXTRA_MODULES) <= set(extras)
    (all_spec,) = extras["all"]
    listed = set(all_spec.split("[", 1)[1].rstrip("]").split(","))
    assert listed == set(EXTRA_MODULES)


def test_requirements_txt_matches_all_extra():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())["project"]
    extras = project["optional-dependencies"]

    def names(specs):
        return {s.split(">")[0].split("[")[0].split("=")[0].strip().lower() for s in specs}

    from_extras = names(s for e in EXTRA_MODULES for s in extras[e])
    lines = (ROOT / "requirements.txt").read_text().splitlines()
    from_requirements = names(line for line in lines if line.strip() and not line.startswith("#"))
    assert from_requirements == from_extras
