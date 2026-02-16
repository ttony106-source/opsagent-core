from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json_bytes(value: Any) -> bytes:
    """Return canonical JSON bytes for stable hashing."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash_json(value: Any) -> str:
    return sha256_hex(canonical_json_bytes(value))


def chained_entry_hash(entry_for_hash: dict[str, Any], hash_prev: str) -> str:
    payload = canonical_json_bytes(entry_for_hash) + hash_prev.encode("utf-8")
    return sha256_hex(payload)
