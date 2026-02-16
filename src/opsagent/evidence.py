from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from opsagent.config import OpsAgentConfig
from opsagent.runlog import atomic_write_text


GENESIS_LEDGER_ENTRY = {
    "entry_id": "GEN-000001",
    "timestamp": "2026-01-01T00:00:00Z",
    "change_type": "policy_create",
    "subject": "opsagent-genesis",
    "decision": "approved",
    "approvers": ["system:bootstrap"],
    "evidence_refs": ["governance-ledger/ledger/GEN-000001.json"],
    "entry_hash": "0" * 64,
    "prev_hash": "GENESIS",
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def ensure_genesis_ledger(config: OpsAgentConfig) -> Path:
    genesis_path = config.governance_ledger_path / "ledger" / "GEN-000001.json"
    if not genesis_path.exists():
        atomic_write_text(genesis_path, json.dumps(GENESIS_LEDGER_ENTRY, indent=2) + "\n")
    return genesis_path


def write_evidence_bundle(
    config: OpsAgentConfig,
    run_id: str,
    payload: dict[str, Any],
    decision: dict[str, Any],
    entry: dict[str, Any],
) -> list[Path]:
    now = datetime.now(timezone.utc)
    month = now.strftime("%Y-%m")
    evidence_dir = config.evidence_root / month / f"RUN-{run_id}"
    evidence_dir.mkdir(parents=True, exist_ok=True)

    run_entry_path = evidence_dir / "run_entry.json"
    payload_path = evidence_dir / "payload.json"
    decision_path = evidence_dir / "decision.json"

    atomic_write_text(run_entry_path, json.dumps(entry, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")
    atomic_write_text(payload_path, json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")
    atomic_write_text(decision_path, json.dumps(decision, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n")

    return [run_entry_path, payload_path, decision_path]


def write_manifest(config: OpsAgentConfig, run_id: str, files: list[Path]) -> Path:
    now = datetime.now(timezone.utc)
    month = now.strftime("%Y-%m")
    day = now.strftime("%Y-%m-%d")
    manifest_path = config.manifests_root / month / f"MANIFEST-{day}.yaml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        f"- run_id: '{run_id}'",
        f"  generated_at: '{now.isoformat().replace('+00:00', 'Z')}'",
        "  files:",
    ]
    for item in files:
        rel = item.relative_to(config.root)
        lines.append(f"    - path: '{rel.as_posix()}'")
        lines.append(f"      sha256: '{sha256_file(item)}'")
    text = "\n".join(lines) + "\n"

    if manifest_path.exists():
        existing = manifest_path.read_text(encoding="utf-8")
        if existing.strip():
            text = existing.rstrip() + "\n" + text
    atomic_write_text(manifest_path, text)
    return manifest_path
