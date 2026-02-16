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
