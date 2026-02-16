from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from opsagent.config import OpsAgentConfig


@dataclass(frozen=True)
class Decision:
    allow: bool
    reason: str
    policy_id: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "allow": self.allow,
            "decision": "ALLOW" if self.allow else "DENY",
            "reason": self.reason,
            "policy_id": self.policy_id,
        }


class PolicyError(RuntimeError):
    pass


def validate_json_schema_instance(instance: Any, schema: dict[str, Any], path: str = "<root>") -> list[str]:
    """Small fail-closed schema validator aligned to repo schemas."""
    errors: list[str] = []

    expected_type = schema.get("type")
    if expected_type == "object" and not isinstance(instance, dict):
        return [f"{path}: expected object"]
    if expected_type == "array" and not isinstance(instance, list):
        return [f"{path}: expected array"]
    if expected_type == "string" and not isinstance(instance, str):
        return [f"{path}: expected string"]

    if "enum" in schema and instance not in schema["enum"]:
        errors.append(f"{path}: invalid enum value {instance!r}")

    if isinstance(instance, dict):
        props = schema.get("properties", {})
        required = schema.get("required", [])
        for key in required:
            if key not in instance:
                errors.append(f"{path}: missing required property {key}")
        if schema.get("additionalProperties") is False:
            unknown = set(instance).difference(props)
            for key in sorted(unknown):
                errors.append(f"{path}: unexpected property {key}")
        for key, value in instance.items():
            if key in props and isinstance(props[key], dict):
                errors.extend(validate_json_schema_instance(value, props[key], f"{path}.{key}"))

    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errors.append(f"{path}: expected at least {schema['minItems']} items")
        item_schema = schema.get("items")
        if isinstance(item_schema, dict):
            for idx, item in enumerate(instance):
                errors.extend(validate_json_schema_instance(item, item_schema, f"{path}[{idx}]"))

    return errors


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_and_validate_policyset(config: OpsAgentConfig) -> dict[str, Any]:
    if not config.policy_bindings_path.exists():
        raise PolicyError(f"missing policy bindings: {config.policy_bindings_path}")

    bindings = _load_json(config.policy_bindings_path)
    policy_ref = bindings.get("policy_artifact")
    policy_schema_ref = bindings.get("policy_schema")
    if not policy_ref or not policy_schema_ref:
        raise PolicyError("policy-bindings.json missing required fields policy_artifact/policy_schema")

    policy_path = (config.root / policy_ref).resolve()
    schema_path = (config.root / policy_schema_ref).resolve()
    if not policy_path.exists():
        raise PolicyError(f"missing referenced policy artifact: {policy_path}")
    if not schema_path.exists():
        raise PolicyError(f"missing referenced policy schema: {schema_path}")

    policyset = _load_json(policy_path)
    schema = _load_json(schema_path)
    errors = validate_json_schema_instance(policyset, schema)
    if errors:
        raise PolicyError("invalid policy artifact: " + "; ".join(errors))
    return policyset


def actor_roles(actor: str) -> set[str]:
    roles: set[str] = set()
    if actor.startswith("ceo:"):
        roles.add("CEO")
    if actor.startswith("trustee:"):
        roles.add("TRUSTEE")
    return roles


def evaluate_policy(policyset: dict[str, Any], action: str, payload: dict[str, Any], actor: str, mode: str) -> Decision:
    if mode not in {"FAIL_CLOSED", "DRY_RUN"}:
        return Decision(allow=False, reason="invalid_mode")

    policies = policyset.get("policies", [])
    matches = [p for p in policies if p.get("action") == action]
    if len(matches) != 1:
        return Decision(allow=False, reason="missing_policy" if len(matches) == 0 else "ambiguous_policy")

    policy = matches[0]
    required_mode = policy.get("mode")
    if required_mode not in {"FAIL_CLOSED", "DRY_RUN", "ANY"}:
        return Decision(allow=False, reason="ambiguous_policy_mode", policy_id=policy.get("policy_id"))
    if required_mode != "ANY" and required_mode != mode:
        return Decision(allow=False, reason="mode_mismatch", policy_id=policy.get("policy_id"))

    required_role = policy.get("requires", {}).get("authority_role")
    if required_role and required_role not in actor_roles(actor):
        return Decision(allow=False, reason="insufficient_authority", policy_id=policy.get("policy_id"))

    required_fields = policy.get("requires", {}).get("payload_fields", [])
    if not isinstance(required_fields, list):
        return Decision(allow=False, reason="ambiguous_required_fields", policy_id=policy.get("policy_id"))

    for field in required_fields:
        if field not in payload:
            return Decision(allow=False, reason=f"missing_required_field:{field}", policy_id=policy.get("policy_id"))

    return Decision(allow=True, reason="policy_matched", policy_id=policy.get("policy_id"))
