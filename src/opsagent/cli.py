from __future__ import annotations

import argparse
import json
from pathlib import Path

from opsagent.config import default_config
from opsagent.evidence import ensure_genesis_ledger, write_evidence_bundle, write_manifest
from opsagent.policy_engine import PolicyError, evaluate_policy, load_and_validate_policyset
from opsagent.runlog import append_runlog_entry, build_run_entry, next_run_id, write_state


class FailClosedError(RuntimeError):
    pass


def _load_payload(path: str) -> dict:
    payload_path = Path(path)
    with payload_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise FailClosedError("payload must be a JSON object")
    return data


def _execute(action: str, payload_file: str, actor: str, mode: str, simulate: bool = False) -> int:
    config = default_config()
    payload = _load_payload(payload_file)

    ensure_genesis_ledger(config)

    try:
        policyset = load_and_validate_policyset(config)
    except PolicyError as exc:
        decision = {"allow": False, "decision": "DENY", "reason": f"policy_validation_failed:{exc}"}
        return _record_and_exit(config, action, actor, mode, payload, decision)

    decision_obj = evaluate_policy(policyset, action=action, payload=payload, actor=actor, mode=mode)
    decision = decision_obj.as_dict()
    if simulate:
        decision["simulated"] = True

    return _record_and_exit(config, action, actor, mode, payload, decision)


def _record_and_exit(config, action: str, actor: str, mode: str, payload: dict, decision: dict) -> int:
    run_id, state = next_run_id(config)
    prev_hash = state.get("last_hash", "GENESIS")
    temp_entry = build_run_entry(
        run_id=run_id,
        prev_hash=prev_hash,
        action=action,
        actor=actor,
        mode=mode,
        payload=payload,
        decision=decision,
        evidence_files=[],
    )
    evidence_files = write_evidence_bundle(config, run_id, payload, decision, temp_entry)
    manifest_path = write_manifest(config, run_id, evidence_files)

    final_entry = build_run_entry(
        run_id=run_id,
        prev_hash=prev_hash,
        action=action,
        actor=actor,
        mode=mode,
        payload=payload,
        decision=decision,
        evidence_files=[
            {"path": str(path.relative_to(config.root)).replace("\\", "/")}
            for path in [*evidence_files, manifest_path]
        ],
    )

    write_evidence_bundle(config, run_id, payload, decision, final_entry)
    append_runlog_entry(config, final_entry)
    write_state(config, run_id, final_entry["hash_curr"])

    print(json.dumps(final_entry, indent=2))
    if decision.get("allow"):
        return 0
    return 2


def _validate() -> int:
    config = default_config()
    ensure_genesis_ledger(config)
    try:
        load_and_validate_policyset(config)
    except PolicyError as exc:
        print(f"DENY: {exc}")
        return 2
    print("ALLOW: policy artifacts valid")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="opsagent")
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run")
    run_parser.add_argument("--action", required=True)
    run_parser.add_argument("--payload", required=True)
    run_parser.add_argument("--actor", required=True)
    run_parser.add_argument("--mode", choices=["FAIL_CLOSED", "DRY_RUN"], required=True)

    validate_parser = sub.add_parser("validate")
    validate_parser.add_argument("--mode", choices=["FAIL_CLOSED", "DRY_RUN"], default="FAIL_CLOSED")

    sim_parser = sub.add_parser("simulate")
    sim_parser.add_argument("--action", required=True)
    sim_parser.add_argument("--payload", required=True)
    sim_parser.add_argument("--actor", required=True)
    sim_parser.add_argument("--mode", choices=["FAIL_CLOSED", "DRY_RUN"], default="DRY_RUN")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "validate":
        return _validate()
    if args.command == "run":
        return _execute(args.action, args.payload, args.actor, args.mode, simulate=False)
    if args.command == "simulate":
        return _execute(args.action, args.payload, args.actor, args.mode, simulate=True)
    raise FailClosedError("unsupported command")


if __name__ == "__main__":
    raise SystemExit(main())
