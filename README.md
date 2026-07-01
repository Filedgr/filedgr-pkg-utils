# filedgr-pkg-utils

![Build Status](https://img.shields.io/github/actions/workflow/status/Filedgr/filedgr-pkg-utils/cd-main.yml?branch=main)
![Coverage](./coverage.svg)
![Python Version](https://img.shields.io/badge/python-%3E%3D3.11-blue.svg)
[![PyPI version](https://badge.fury.io/py/filedgr-pkg-utils.svg)](https://pypi.org/project/filedgr-pkg-utils/)
![License](https://img.shields.io/badge/license-MIT-blue.svg)

A comprehensive, production-ready Python utility toolkit for modern distributed systems, Web3 integrations, and data-heavy microservices.

`filedgr-pkg-utils` provides a unified, protocol-driven API for cryptography, resilient networking, deterministic data serialization, compression, and structured logging.

## 📦 Installation

Install the base package (extremely lightweight, ideal for AWS Lambda):

```bash
pip install filedgr-pkg-utils
```

Install with optional image perceptual hashing support (includes Pillow and ImageHash):

```bash
pip install "filedgr-pkg-utils[images]"
```

## 🚀 Prominent Features & Examples

### 1. Resilience & Aspect-Oriented Hooks

Stop writing try/except blocks with `time.sleep()`. Stack our context-aware decorators to build bulletproof network calls and clean up your business logic.

```python
from filedgr_pkg_utils.resilience.decorators import retry, circuit_breaker, fallback
from filedgr_pkg_utils.hooks.post_action import post_action

def audit_log(result, *args, **kwargs):
    print(f"Audit: Successfully fetched data {result}")

def serve_stale_data(*args, **kwargs):
    return {"status": "stale", "data": []}

@post_action(callback=audit_log)
@fallback(fallback_function=serve_stale_data)
@circuit_breaker(failure_threshold=5, recovery_timeout_seconds=30)
@retry(max_attempts=3, backoff_multiplier=2.0)
async def fetch_web3_data(node_url: str):
    # This function is completely protected.
    # It will retry on failure, trip a circuit breaker if the node is down,
    # serve stale data if all else fails, and log the result when successful.
    pass
```

### 2. Unified Compression

A single, clean protocol for zip, gzip, zstd, and brotli. Easily swap algorithms without changing your application code.

```python
from filedgr_pkg_utils.compression import CompressionUtils, ZstdAlgorithm, ZipAlgorithm

# Swap from standard Zip to high-performance Zstd in one line
utils = CompressionUtils(ZstdAlgorithm(level=3))

# Compress bytes
compressed_data = utils.compress(b"Hello World")

# Compress files and directories
utils.compress_file("data.json", "data.json.zst")
```

### 3. Canonical Serialization & Cryptography

Generate deterministic, whitespace-free, and alphabetically sorted JSON payloads—perfect for creating verifiable hashes and blockchain signatures.

```python
from filedgr_pkg_utils.canonicalization.canonical_json_mixin import CanonicalJsonMixin
from datetime import datetime, timezone

class BlockchainPayload(CanonicalJsonMixin):
    z_field: str
    a_field: int
    timestamp: datetime

payload = BlockchainPayload(
    z_field="last",
    a_field=1,
    timestamp=datetime(2023, 10, 25, 12, 30, 0, tzinfo=timezone.utc)
)

# Output is strictly deterministic: {"a_field":1,"timestamp":"2023-10-25T12:30:00.000Z","z_field":"last"}
json_string = payload.canonical_json()
```

### 4. Zero-Config Structured JSON Logging

Output logs as deterministic JSON for flawless Datadog or AWS CloudWatch ingestion. Fully integrates with Python's standard logging library.

```python
from filedgr_pkg_utils.logging import LoggerFactory

# Automatically reads FILEDGR_LOGGING_ENABLED env var
logger = LoggerFactory.get_logger(__name__)

logger.info("Processing file", extra={"file_id": "ABC-123", "correlation_id": "999"})
# Output: {"timestamp": "2026-05-14T12:00:00.000Z", "level": "INFO", "logger": "__main__", "message": "Processing file", "file_id": "ABC-123", "correlation_id": "999"}
```

### 5. Perceptual Image Hashing (Optional)

Detect visually similar images, compression artifacts, and resized duplicates using Hamming distance.

```python
from filedgr_pkg_utils.images.hashing import PHashAlgorithm, ImageHashUtils

utils = ImageHashUtils(PHashAlgorithm())

hash_orig = utils.hash_image("original.png")
hash_comp = utils.hash_image("compressed_artifact.jpg")

if utils.is_similar(hash_orig, hash_comp, max_distance=5):
    print("These images are visually similar!")
```

## 🛠️ Development & Testing

This project enforces high coverage and clean coding standards.

To run the test suite with coverage:

```bash
make test-coverage
```

To run the linter:

```bash
make lint
```