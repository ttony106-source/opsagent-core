#!/usr/bin/env python3
"""Fail-closed validation for policy, run-log, and governance artifacts."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BINDINGS_PATH = ROOT / "opsagent-core/config/policy-bindings.json"

VALIDATION_TARGETS = (
    {
        "name": "automation policysets",
        "schema": ROOT / "automation-policies/schemas/policy.schema.json",
        "directory": ROOT / "automation-policies/policysets",
        "glob": "*.json",
        "minimum": 1,
    },
    {
        "name": "governance ledger entries",
        "schema": ROOT / "governance-ledger/schemas/ledger-entry.schema.json",
        "directory": ROOT / "governance-ledger/entries",
        "glob": "*.json",
        "minimum": 1,
    },
    {
        "name": "opsagent run logs",
        "schema": ROOT / "opsagent-core/schemas/run-log.schema.json",
        "directory": ROOT / "opsagent-core/run-logs",
        "glob": "*.json",
        "minimum": 1,
    },
)


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _matches_type(value: Any, expected_type: str) -> bool:
    mapping = {
        "object": lambda x: isinstance(x, dict),
        "array": lambda x: isinstance(x, list),
        "string": lambda x: isinstance(x, str),
        "integer": lambda x: isinstance(x, int) and not isinstance(x, bool),
        "boolean": lambda x: isinstance(x, bool),
    }
    checker = mapping.get(expected_type)
    return checker(value) if checker else True


def validate_against_schema(payload: Any, schema: dict[str, Any], path: str = "<root>") -> list[str]:
    errors: list[str] = []
    expected_type = schema.get("type")
    if expected_type and not _matches_type(payload, expected_type):
        return [f"{path}: expected type {expected_type}, got {type(payload).__name__}"]

    if "enum" in schema and payload not in schema["enum"]:
        errors.append(f"{path}: value {payload!r} is not in enum {schema['enum']}")

    if isinstance(payload, str):
        if "minLength" in schema and len(payload) < schema["minLength"]:
            errors.append(f"{path}: string length too short")
        if "pattern" in schema and not re.fullmatch(schema["pattern"], payload):
            errors.append(f"{path}: pattern mismatch")

    if isinstance(payload, list):
        if "minItems" in schema and len(payload) < schema["minItems"]:
            errors.append(f"{path}: list has too few items")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for idx, item in enumerate(payload):
                errors.extend(validate_against_schema(item, item_schema, f"{path}.{idx}"))

    if isinstance(payload, dict):
        required = schema.get("required", [])
        for key in required:
            if key not in payload:
                errors.append(f"{path}: missing required property {key!r}")

        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            unknown = set(payload).difference(properties)
            for key in sorted(unknown):
                errors.append(f"{path}: unexpected property {key!r}")

        for key, value in payload.items():
            if key in properties and isinstance(properties[key], dict):
                errors.extend(validate_against_schema(value, properties[key], f"{path}.{key}"))

    return errors


def validate_target(target: dict[str, Any]) -> list[str]:
    schema = load_json(target["schema"])
    files = sorted(target["directory"].glob(target["glob"]))
    errors: list[str] = []
    if len(files) < target["minimum"]:
        return [f"{target['name']} fail-closed: expected >= {target['minimum']} files"]
    for file_path in files:
        payload = load_json(file_path)
        errors.extend(f"{file_path}: {e}" for e in validate_against_schema(payload, schema))
    return errors


def validate_bindings() -> list[str]:
    errors: list[str] = []
    if not BINDINGS_PATH.exists():
        return [f"missing bindings file: {BINDINGS_PATH}"]
    bindings = load_json(BINDINGS_PATH)
    for key in ("policy_schema", "policy_artifact"):
        if key not in bindings:
            errors.append(f"bindings missing key: {key}")
            continue
        path = ROOT / bindings[key]
        if not path.exists():
            errors.append(f"bindings reference missing file: {path}")
    return errors


def main() -> int:
    all_errors: list[str] = []
    all_errors.extend(validate_bindings())
    for target in VALIDATION_TARGETS:
        all_errors.extend(validate_target(target))

    if all_errors:
        print("Policy validation failed (fail-closed):", file=sys.stderr)
        for error in all_errors:
            print(f" - {error}", file=sys.stderr)
        return 1

    print("Policy validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
