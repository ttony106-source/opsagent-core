#!/usr/bin/env python3
"""Fail-closed schema validation for policy and governance artifacts."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

VALIDATION_TARGETS = (
    {
        "name": "automation policies",
        "schema": ROOT / "automation-policies/schemas/policy.schema.json",
        "directory": ROOT / "automation-policies/policies",
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


def _validate_date_time(value: str) -> bool:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        return True
    except ValueError:
        return False


def _matches_type(value: Any, expected_type: str) -> bool:
    mapping = {
        "object": lambda x: isinstance(x, dict),
        "array": lambda x: isinstance(x, list),
        "string": lambda x: isinstance(x, str),
        "number": lambda x: isinstance(x, (int, float)) and not isinstance(x, bool),
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
            errors.append(f"{path}: string length {len(payload)} is less than minLength {schema['minLength']}")
        if "pattern" in schema and not re.fullmatch(schema["pattern"], payload):
            errors.append(f"{path}: value {payload!r} does not match pattern {schema['pattern']!r}")
        if schema.get("format") == "date-time" and not _validate_date_time(payload):
            errors.append(f"{path}: value {payload!r} is not a valid date-time")

    if isinstance(payload, list):
        if "minItems" in schema and len(payload) < schema["minItems"]:
            errors.append(f"{path}: list has {len(payload)} item(s), below minItems {schema['minItems']}")
        if schema.get("uniqueItems") and len(payload) != len({json.dumps(item, sort_keys=True) for item in payload}):
            errors.append(f"{path}: list items must be unique")
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
        additional_allowed = schema.get("additionalProperties", True)
        if additional_allowed is False:
            unknown = set(payload) - set(properties)
            for key in sorted(unknown):
                errors.append(f"{path}: unexpected property {key!r}")

        for key, value in payload.items():
            if key in properties and isinstance(properties[key], dict):
                errors.extend(validate_against_schema(value, properties[key], f"{path}.{key}"))

    return errors


def validate_target(target: dict[str, Any]) -> list[str]:
    errors: list[str] = []

    schema_path: Path = target["schema"]
    if not schema_path.exists():
        return [f"missing schema: {schema_path}"]

    try:
        schema = load_json(schema_path)
    except json.JSONDecodeError as exc:
        return [f"invalid schema JSON {schema_path}: {exc}"]

    directory: Path = target["directory"]
    files = sorted(directory.glob(target["glob"]))

    if len(files) < target["minimum"]:
        errors.append(
            f"{target['name']} fail-closed: expected at least {target['minimum']} file(s) in {directory}, found {len(files)}"
        )
        return errors

    for file_path in files:
        try:
            payload = load_json(file_path)
        except json.JSONDecodeError as exc:
            errors.append(f"{file_path}: invalid JSON ({exc})")
            continue

        for error in validate_against_schema(payload, schema):
            errors.append(f"{file_path}: {error}")

    return errors


def main() -> int:
    all_errors: list[str] = []

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
