from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Iterable, Optional, Tuple


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_hash(prev_hash: Optional[str], payload: Dict[str, Any], algo: str = "sha256") -> str:
    if algo != "sha256":
        raise ValueError(f"Unsupported hash algorithm: {algo}")
    canonical = canonical_json(payload)
    material = f"{prev_hash or ''}|{canonical}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def derive_chain_id(payload: Dict[str, Any], default: str = "GLOBAL") -> str:
    run_id = payload.get("run_id")
    if isinstance(run_id, str) and run_id.strip():
        return run_id
    return default


def verify_chain(rows: Iterable[Dict[str, Any]], algo: str = "sha256") -> Tuple[bool, Optional[int], Optional[str]]:
    previous_hash: Optional[str] = None

    for index, row in enumerate(rows):
        payload_raw = row.get("payload")
        if not isinstance(payload_raw, str):
            return False, index, "missing_payload"

        stored_hash = row.get("hash")
        stored_prev_hash = row.get("prev_hash")

        if not isinstance(stored_hash, str) or not stored_hash:
            return False, index, "missing_hash"

        try:
            payload = json.loads(payload_raw)
        except Exception:
            return False, index, "invalid_payload_json"

        expected_prev_hash = previous_hash
        if (stored_prev_hash or None) != (expected_prev_hash or None):
            return False, index, "prev_hash_mismatch"

        recomputed = compute_hash(expected_prev_hash, payload, algo=algo)
        if recomputed != stored_hash:
            return False, index, "hash_mismatch"

        previous_hash = stored_hash

    return True, None, None
