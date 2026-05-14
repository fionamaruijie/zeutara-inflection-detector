"""
Tests for scorer.py — verify the deterministic scoring math.

Run with:  python -m pytest tests/ -v
Or:        python tests/test_scorer.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from schema import Signals, Evidence
from scorer import score_signals


def test_empty_signals_score_zero():
    s = Signals()
    score, conf, penalty, reasons = score_signals(s, [])
    # b2b_revenue_motion_unclear gives half credit (6) even when empty
    assert score <= 10, f"empty signals should score very low, got {score}"
    assert conf == 0
    assert penalty == 0


def test_strong_inflection_account_scores_high():
    s = Signals(
        estimated_stage="series_a",
        business_model="B2B SaaS",
        headcount_estimate=42,
        recent_funding=True,
        hiring_first_gtm_leader=True,
        hiring_operations_role=True,
        founder_led_sales_signal=True,
        enterprise_expansion_signal=True,
        multiple_open_gtm_roles=True,
        sources_used=["Homepage", "Careers", "Funding announcement"],
        source_confidence="high",
    )
    score, conf, penalty, reasons = score_signals(s, [
        Evidence("hiring_first_gtm_leader", "Head of Sales", "url", "high"),
        Evidence("recent_funding", "raised $14M Series A", "url", "high"),
    ])
    assert score >= 80, f"strong account should score >=80, got {score}"
    assert penalty == 0
    assert any("hiring_first_gtm_leader" in r for r in reasons)


def test_severe_disqualifier_crashes_score():
    s = Signals(
        estimated_stage="series_a",
        business_model="B2B SaaS",
        headcount_estimate=42,
        recent_funding=True,
        hiring_first_gtm_leader=True,
        mature_revops_in_place=True,  # severe disqualifier
        sources_used=["Homepage"],
    )
    score, conf, penalty, reasons = score_signals(s, [])
    assert penalty <= -30, f"severe disqualifier should apply >=30 penalty, got {penalty}"
    assert score < 70, f"score should drop below warm-intro threshold, got {score}"


def test_multiple_disqualifiers_stack():
    s = Signals(
        estimated_stage="seed",
        business_model="B2B",
        recent_funding=True,
        local_smb_only=True,
        operating_partner_already_engaged=True,
    )
    score, conf, penalty, reasons = score_signals(s, [])
    # Two severe disqualifiers (-35 + -45 = -80)
    assert penalty <= -70, f"two severe disqualifiers should stack, got {penalty}"
    assert score == 0


def test_confidence_scales_with_sources():
    base = Signals(estimated_stage="seed", sources_used=["one"])
    s_low = score_signals(base, [])[1]

    base2 = Signals(estimated_stage="seed", sources_used=["a", "b", "c"])
    s_high = score_signals(base2, [
        Evidence("x", "y", "z", "high"),
        Evidence("x", "y", "z", "high"),
    ])[1]

    assert s_high > s_low, "more sources + evidence should raise confidence"


def test_pre_seed_lower_weight_than_series_a():
    a = Signals(estimated_stage="series_a", business_model="B2B")
    p = Signals(estimated_stage="pre_seed", business_model="B2B")
    score_a, *_ = score_signals(a, [])
    score_p, *_ = score_signals(p, [])
    assert score_a > score_p, "series_a should outscore pre_seed at parity"


if __name__ == "__main__":
    test_empty_signals_score_zero()
    test_strong_inflection_account_scores_high()
    test_severe_disqualifier_crashes_score()
    test_multiple_disqualifiers_stack()
    test_confidence_scales_with_sources()
    test_pre_seed_lower_weight_than_series_a()
    print("All scorer tests passed.")
