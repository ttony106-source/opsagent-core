from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from opsagent.config import OpsAgentConfig
from opsagent.hashing import canonical_json_bytes, chained_entry_hash, hash_json


GENESIS_HASH = "GENESIS"


def _fsync_file(path: Path) -> None:
    with path.open("rb") as handle:
        os.fsync(handle.fileno())


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
        dir_fd = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def load_runlog_state(config: OpsAgentConfig) -> dict[str, Any]:
    if not config.runlog_state_path.exists():
        return {"last_run_id": 0, "last_hash": GENESIS_HASH}
    with config.runlog_state_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def next_run_id(config: OpsAgentConfig) -> tuple[str, dict[str, Any]]:
    state = load_runlog_state(config)
    current = int(state.get("last_run_id", 0)) + 1
    run_id = f"{current:06d}"
    return run_id, state


def build_run_entry(
    run_id: str,
    prev_hash: str,
    action: str,
    actor: str,
    mode: str,
    payload: dict[str, Any],
    decision: dict[str, Any],
    evidence_files: list[dict[str, str]],
) -> dict[str, Any]:
    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    entry = {
        "run_id": run_id,
        "timestamp": ts,
        "actor": actor,
        "action": action,
        "mode": mode,
        "payload_hash": hash_json(payload),
        "decision_hash": hash_json(decision),
        "hash_prev": prev_hash,
        "decision": decision,
        "evidence": evidence_files,
    }
    entry["hash_curr"] = chained_entry_hash(entry, prev_hash)
    return entry


def append_runlog_entry(config: OpsAgentConfig, entry: dict[str, Any]) -> None:
    existing = ""
    if config.runlog_path.exists():
        existing = config.runlog_path.read_text(encoding="utf-8")
    line = canonical_json_bytes(entry).decode("utf-8") + "\n"
    atomic_write_text(config.runlog_path, existing + line)


def write_state(config: OpsAgentConfig, run_id: str, curr_hash: str) -> None:
    data = {"last_run_id": int(run_id), "last_hash": curr_hash}
    atomic_write_text(config.runlog_state_path, canonical_json_bytes(data).decode("utf-8") + "\n")
