import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from compliancelens.policy.engine import (
    load_policy, evaluate, execute, PolicyError, BlockPromotion,
)

POLICY_YAML = os.path.join(os.path.dirname(__file__), "..", "config", "policy.yaml")


def _finding(**kw):
    base = {"finding": "quality_check_failed", "layer": "silver",
            "table": "patients", "column": "age", "severity": "high"}
    base.update(kw)
    return base


def test_load_real_policy_file():
    policy = load_policy(POLICY_YAML)
    assert len(policy["rules"]) >= 4


def test_missing_key_raises_named_error(tmp_path):
    p = tmp_path / "bad.yaml"
    p.write_text("rules:\n  - name: x\n    when:\n      finding: a\n")  # no actions
    try:
        load_policy(p)
        raised = False
    except PolicyError as e:
        raised = "actions" in str(e)
    assert raised


def test_unknown_action_rejected(tmp_path):
    p = tmp_path / "bad.yaml"
    p.write_text("rules:\n  - name: x\n    when:\n      finding: a\n    actions: [explode]\n")
    try:
        load_policy(p)
        raised = False
    except PolicyError as e:
        raised = "explode" in str(e)
    assert raised


def test_min_severity_matching():
    policy = {"rules": [{"name": "high_plus", "when": {"finding": "quality_check_failed", "min_severity": "high"}, "actions": ["quarantine"]}]}
    assert evaluate([_finding(severity="medium")], policy) == []
    dec = evaluate([_finding(severity="critical")], policy)
    assert dec and dec[0]["actions"] == ["quarantine"]


def test_pii_in_gold_triggers_mask_and_alert():
    policy = load_policy(POLICY_YAML)
    dec = evaluate([_finding(finding="pii_exposed", layer="gold", pii_type="phone")], policy)
    actions = [a for d in dec for a in d["actions"]]
    assert "mask" in actions and "alert_critical" in actions


def test_critical_drift_blocks_promotion():
    policy = load_policy(POLICY_YAML)
    dec = evaluate([_finding(finding="schema_drift", change_type="column_removed",
                             severity="critical")], policy)
    try:
        execute(dec)
        raised = False
    except BlockPromotion:
        raised = True
    assert raised


def test_low_score_alerts():
    policy = load_policy(POLICY_YAML)
    dec = evaluate([{"finding": "compliance_score", "score": 62.0}], policy)
    assert any("alert_critical" in d["actions"] for d in dec)
