"""
scorer.py
=========
Deterministic scoring on top of an extracted Signals object.

Scoring is deliberately rule-based — even when we use Claude for extraction.
This is the central architectural decision: the AI is allowed to read messy
text, but the routing decision must be auditable. A Zeutara partner has to
be able to look at a brief and ask "why did this score 82?" and get a
straight answer from the reason codes, without re-running the model.

Three outputs:
  - inflection_score (0-100, positive contributions minus disqualifier penalties)
  - confidence_score (0-100, function of how many sources + how fresh)
  - reason_codes (the human-readable why)
"""

from __future__ import annotations

from typing import List, Tuple

from schema import Signals, Evidence
from config import (
    POSITIVE_WEIGHTS,
    DISQUALIFIER_PENALTIES,
    CONFIDENCE_WEIGHTS,
    CONFIDENCE_MAX,
    SEVERE_DISQUALIFIERS,
)


def score_signals(signals: Signals, evidence: List[Evidence]
                  ) -> Tuple[int, int, int, List[str]]:
    """
    Returns: (inflection_score, confidence_score, disqualifier_penalty, reason_codes)

    inflection_score is the final 0-100 number after disqualifier penalties are
    applied. disqualifier_penalty is reported separately so the brief can show
    "raw 82, minus 35 for X = final 47".
    """
    reasons: List[str] = []

    # -----------------------------------------------------------------------
    # Positive contributions
    # -----------------------------------------------------------------------
    raw_positive = 0

    # Stage fit
    if signals.estimated_stage in ("seed", "series_a"):
        raw_positive += POSITIVE_WEIGHTS["stage_seed_or_series_a"]
        reasons.append(f"stage_fit: estimated stage = {signals.estimated_stage}")
    elif signals.estimated_stage == "pre_seed":
        raw_positive += POSITIVE_WEIGHTS["stage_pre_seed"]
        reasons.append("stage_fit_partial: pre-seed (in eligible band, lower weight)")

    # B2B motion
    if signals.business_model and "b2b" in (signals.business_model or "").lower():
        raw_positive += POSITIVE_WEIGHTS["b2b_revenue_motion"]
        reasons.append("b2b_revenue_motion_detected")
    elif not signals.no_b2b_revenue_motion:
        # We did not affirmatively detect B2B motion but also did not flag the
        # absence. Give half credit; tells the reviewer "ambiguous, verify."
        raw_positive += POSITIVE_WEIGHTS["b2b_revenue_motion"] // 2
        reasons.append("b2b_revenue_motion_unclear (half credit; verify)")

    # Headcount band
    hc = signals.headcount_estimate
    if hc is not None and 10 <= hc <= 75:
        raw_positive += POSITIVE_WEIGHTS["headcount_in_band"]
        reasons.append(f"headcount_in_band: ~{hc}")

    # Inflection signals
    if signals.recent_funding:
        raw_positive += POSITIVE_WEIGHTS["recent_funding"]
        reasons.append("recent_funding_signal")
    if signals.hiring_first_gtm_leader:
        raw_positive += POSITIVE_WEIGHTS["hiring_first_gtm_leader"]
        reasons.append("hiring_first_gtm_leader_signal (strong)")
    if signals.hiring_operations_role:
        raw_positive += POSITIVE_WEIGHTS["hiring_operations_role"]
        reasons.append("hiring_operations_role_signal")
    if signals.multiple_open_gtm_roles:
        raw_positive += POSITIVE_WEIGHTS["multiple_open_gtm_roles"]
        reasons.append("multiple_open_gtm_roles_signal")
    if signals.founder_led_sales_signal:
        raw_positive += POSITIVE_WEIGHTS["founder_led_sales_signal"]
        reasons.append("founder_led_sales_signal")
    if signals.enterprise_expansion_signal:
        raw_positive += POSITIVE_WEIGHTS["enterprise_expansion_signal"]
        reasons.append("enterprise_expansion_signal")
    if signals.board_or_investor_pressure:
        raw_positive += POSITIVE_WEIGHTS["board_or_investor_pressure"]
        reasons.append("board_or_investor_pressure_signal")

    positive_capped = min(raw_positive, 100)

    # -----------------------------------------------------------------------
    # Disqualifier penalties
    # -----------------------------------------------------------------------
    total_penalty = 0
    for field, penalty in DISQUALIFIER_PENALTIES.items():
        if getattr(signals, field, False):
            total_penalty += penalty  # penalty is negative
            severity = "SEVERE" if field in SEVERE_DISQUALIFIERS else "soft"
            reasons.append(f"disqualifier_{severity}: {field} ({penalty})")

    inflection_score = max(0, positive_capped + total_penalty)

    # -----------------------------------------------------------------------
    # Confidence score
    # -----------------------------------------------------------------------
    conf = 0
    n_sources = len(signals.sources_used)
    conf += n_sources * CONFIDENCE_WEIGHTS["per_source_used"]

    n_evidence = min(len(evidence), 6)  # diminishing returns above 6
    conf += n_evidence * CONFIDENCE_WEIGHTS["per_evidence_snippet"]

    if signals.data_freshness_days is not None:
        if signals.data_freshness_days <= 30:
            conf += CONFIDENCE_WEIGHTS["fresh_within_30_days"]
            conf += CONFIDENCE_WEIGHTS["fresh_within_90_days"]
        elif signals.data_freshness_days <= 90:
            conf += CONFIDENCE_WEIGHTS["fresh_within_90_days"]

    confidence_score = min(conf, CONFIDENCE_MAX)

    return inflection_score, confidence_score, total_penalty, reasons
