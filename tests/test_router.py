"""
Tests for router.py — verify the routing decisions hit the right buckets.

Run with:  python -m pytest tests/ -v
Or:        python tests/test_router.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from schema import Signals
from router import route, infer_primary_constraint, has_severe_disqualifier


def test_warm_intro_path():
    s = Signals(
        estimated_stage="series_a",
        business_model="B2B SaaS",
        hiring_first_gtm_leader=True,
        recent_funding=True,
    )
    label, constraint, buyer, dq, angle = route(s, inflection_score=85, confidence_score=80)
    assert label == "warm_intro_candidate"
    assert constraint == "gtm_leader_transition"
    assert "forwardable" in buyer.lower() or "investor" in buyer.lower()


def test_direct_outreach_when_score_solid_but_not_warm_intro():
    s = Signals(estimated_stage="seed", founder_led_sales_signal=True)
    label, *_ = route(s, inflection_score=60, confidence_score=55)
    assert label == "direct_outreach_candidate"


def test_watchlist_when_score_modest():
    s = Signals(estimated_stage="seed")
    label, *_ = route(s, inflection_score=40, confidence_score=20)
    assert label == "watchlist"


def test_disqualified_when_score_too_low():
    s = Signals()
    label, *_ = route(s, inflection_score=10, confidence_score=10)
    assert label == "disqualified"


def test_severe_disqualifier_short_circuits_high_score():
    s = Signals(
        estimated_stage="series_a",
        hiring_first_gtm_leader=True,
        mature_revops_in_place=True,  # severe
    )
    label, *_ = route(s, inflection_score=95, confidence_score=95)
    assert label == "disqualified", "severe DQ must short-circuit even a perfect score"


def test_constraint_priority_gtm_leader_first():
    # Both hiring + founder-led — should pick gtm_leader_transition first
    s = Signals(
        hiring_first_gtm_leader=True,
        founder_led_sales_signal=True,
        recent_funding=True,
    )
    assert infer_primary_constraint(s) == "gtm_leader_transition"


def test_constraint_falls_through_to_complexity():
    s = Signals()
    # No specific signals fire — should default
    assert infer_primary_constraint(s) == "operational_complexity_growth"


def test_has_severe_disqualifier():
    assert has_severe_disqualifier(Signals(local_smb_only=True))
    assert has_severe_disqualifier(Signals(mature_revops_in_place=True))
    assert not has_severe_disqualifier(Signals(mid_fundraise=True))  # soft DQ
    assert not has_severe_disqualifier(Signals())


if __name__ == "__main__":
    test_warm_intro_path()
    test_direct_outreach_when_score_solid_but_not_warm_intro()
    test_watchlist_when_score_modest()
    test_disqualified_when_score_too_low()
    test_severe_disqualifier_short_circuits_high_score()
    test_constraint_priority_gtm_leader_first()
    test_constraint_falls_through_to_complexity()
    test_has_severe_disqualifier()
    print("All router tests passed.")
