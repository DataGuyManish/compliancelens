import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from compliancelens.compliance.scoring import compute_score, load_weights

WEIGHTS = load_weights(os.path.join(os.path.dirname(__file__), "..", "config", "score_weights.yaml"))


def test_perfect_data_scores_100():
    metrics = {"null_rates": [0.0], "failed_checks": 0, "total_checks": 6,
               "unmasked_pii": 0, "drift_events": 0, "orphan_rows": 0, "total_child_rows": 100}
    score, breakdown = compute_score(metrics, WEIGHTS)
    assert score == 100.0 and all(v == 0.0 for v in breakdown.values())


def test_worst_data_scores_0():
    metrics = {"null_rates": [1.0], "failed_checks": 10, "total_checks": 10,
               "unmasked_pii": 100, "drift_events": 50, "orphan_rows": 50, "total_child_rows": 50}
    score, _ = compute_score(metrics, WEIGHTS)
    assert score == 0.0


def test_masking_improves_score():
    base = {"null_rates": [0.04], "failed_checks": 1, "total_checks": 7,
            "drift_events": 1, "orphan_rows": 2, "total_child_rows": 100}
    before, _ = compute_score(dict(base, unmasked_pii=12), WEIGHTS)
    after, _ = compute_score(dict(base, unmasked_pii=0), WEIGHTS)
    assert after > before
