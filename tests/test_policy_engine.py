from __future__ import annotations

from opsagent.policy_engine import evaluate_policy


def test_policy_deny_on_ambiguity() -> None:
    policyset = {
        "policies": [
            {"policy_id": "a", "action": "deploy", "mode": "ANY", "requires": {}, "checks": [], "evidence_required": ["x"], "on_deny": "DENY"},
            {"policy_id": "b", "action": "deploy", "mode": "ANY", "requires": {}, "checks": [], "evidence_required": ["x"], "on_deny": "DENY"},
        ]
    }

    decision = evaluate_policy(policyset, action="deploy", payload={}, actor="user:1", mode="FAIL_CLOSED")
    assert decision.allow is False
    assert decision.reason == "ambiguous_policy"


def test_policy_deny_on_required_value_mismatch() -> None:
    policyset = {
        "policies": [
            {
                "policy_id": "POL-SOCIAL-001",
                "action": "social_post",
                "mode": "FAIL_CLOSED",
                "requires": {
                    "authority_role": "TRUSTEE",
                    "payload_fields": ["job_type", "platforms"],
                    "payload_equals": {"job_type": "SOCIAL_POST", "platforms": ["linkedin"]},
                },
                "checks": ["authority_role", "required_fields", "required_values"],
                "evidence_required": ["run_entry.json"],
                "on_deny": "DENY",
            }
        ]
    }

    decision = evaluate_policy(
        policyset,
        action="social_post",
        payload={"job_type": "SOCIAL_POST", "platforms": ["linkedin", "x"]},
        actor="trustee:ops",
        mode="FAIL_CLOSED",
    )
    assert decision.allow is False
    assert decision.reason == "invalid_required_value:platforms"


def test_policy_allow_on_required_values_match() -> None:
    policyset = {
        "policies": [
            {
                "policy_id": "POL-SOCIAL-001",
                "action": "social_post",
                "mode": "FAIL_CLOSED",
                "requires": {
                    "authority_role": "TRUSTEE",
                    "payload_fields": ["job_type", "platforms", "mode"],
                    "payload_equals": {
                        "job_type": "SOCIAL_POST",
                        "platforms": ["linkedin"],
                        "mode": "CAPITAL_RAISE_INVESTOR_CONVERSION",
                    },
                },
                "checks": ["authority_role", "required_fields", "required_values"],
                "evidence_required": ["run_entry.json"],
                "on_deny": "DENY",
            }
        ]
    }

    decision = evaluate_policy(
        policyset,
        action="social_post",
        payload={
            "job_type": "SOCIAL_POST",
            "platforms": ["linkedin"],
            "mode": "CAPITAL_RAISE_INVESTOR_CONVERSION",
        },
        actor="trustee:ops",
        mode="FAIL_CLOSED",
    )
    assert decision.allow is True
    assert decision.reason == "policy_matched"
