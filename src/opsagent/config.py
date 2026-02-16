from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class OpsAgentConfig:
    root: Path
    runlog_path: Path
    runlog_state_path: Path
    policy_bindings_path: Path
    governance_ledger_path: Path
    evidence_root: Path
    manifests_root: Path


DEFAULT_ROOT = Path(__file__).resolve().parents[2]


def default_config(root: Path | None = None) -> OpsAgentConfig:
    resolved_root = (root or DEFAULT_ROOT).resolve()
    governance_root = resolved_root / "governance-ledger"
    return OpsAgentConfig(
        root=resolved_root,
        runlog_path=resolved_root / "logs" / "RUNLOG.jsonl",
        runlog_state_path=resolved_root / "logs" / "RUNLOG.state.json",
        policy_bindings_path=resolved_root / "opsagent-core" / "config" / "policy-bindings.json",
        governance_ledger_path=governance_root,
        evidence_root=governance_root / "evidence",
        manifests_root=governance_root / "seals" / "manifests",
    )


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)
