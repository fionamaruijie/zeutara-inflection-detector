"""
router.py
=========
Routing maps a scored Signals object to one of four buckets:

  - warm_intro_candidate
  - direct_outreach_candidate
  - watchlist
  - disqualified

It also picks the single primary structural constraint to lead the
diagnostic brief with. A brief that says "you have ten problems" is useless;
a brief that says "your one constraint is X, here is the evidence" is the
artifact a partner is willing to forward.
"""

from __future__ import annotations

from typing import Tuple

from schema import Signals
from config import (
    ROUTE_THRESHOLDS,
    SEVERE_DISQUALIFIERS,
    OUTREACH_ANGLES,
    DISCOVERY_QUESTIONS,
    BUYER_PATHS,
)


# ---------------------------------------------------------------------------
# Constraint inference
# ---------------------------------------------------------------------------
# Priority order matters. If multiple constraints fire, we lead with the most
# specific one. Founder-led GTM is the highest-conviction lead because it
# directly maps to Zeutara's product.

def infer_primary_constraint(signals: Signals) -> str:
    if signals.hiring_first_gtm_leader:
        return "gtm_leader_transition"
    if signals.founder_led_sales_signal:
        return "founder_led_gtm_bottleneck"
    if signals.enterprise_expansion_signal:
        return "enterprise_motion_emerging"
    if signals.recent_funding and signals.multiple_open_gtm_roles:
        return "capital_to_operating_translation"
    if signals.multiple_open_gtm_roles or signals.hiring_operations_role:
        return "operational_complexity_growth"
    if signals.recent_funding:
        return "capital_to_operating_translation"
    return "operational_complexity_growth"


def has_severe_disqualifier(signals: Signals) -> bool:
    return any(getattr(signals, f, False) for f in SEVERE_DISQUALIFIERS)


# ---------------------------------------------------------------------------
# Main routing function
# ---------------------------------------------------------------------------

def route(
    signals: Signals,
    inflection_score: int,
    confidence_score: int,
) -> Tuple[str, str, str, list, str]:
    """
    Returns:
      (route_label, primary_constraint, suggested_buyer_path,
       discovery_questions, recommended_outreach_angle)
    """

    # Hard gate: severe disqualifier short-circuits everything.
    if has_severe_disqualifier(signals):
        constraint = infer_primary_constraint(signals)
        return (
            "disqualified",
            constraint,
            BUYER_PATHS["disqualified"],
            [],
            "(no outreach — severe disqualifier present)",
        )

    constraint = infer_primary_constraint(signals)

    # Warm intro path: highest score + confidence floor + no severe DQ
    if (
        inflection_score >= ROUTE_THRESHOLDS["warm_intro_min_score"]
        and confidence_score >= ROUTE_THRESHOLDS["warm_intro_min_confidence"]
    ):
        return (
            "warm_intro_candidate",
            constraint,
            BUYER_PATHS["warm_intro_candidate"],
            DISCOVERY_QUESTIONS.get(constraint, []),
            OUTREACH_ANGLES.get(constraint, ""),
        )

    # Direct outreach: meaningful score but lower confidence or score
    if (
        inflection_score >= ROUTE_THRESHOLDS["direct_outreach_min_score"]
        and confidence_score >= ROUTE_THRESHOLDS["direct_outreach_min_confidence"]
    ):
        return (
            "direct_outreach_candidate",
            constraint,
            BUYER_PATHS["direct_outreach_candidate"],
            DISCOVERY_QUESTIONS.get(constraint, []),
            OUTREACH_ANGLES.get(constraint, ""),
        )

    # Watchlist: real signal but not actionable yet
    if inflection_score >= ROUTE_THRESHOLDS["watchlist_min_score"]:
        return (
            "watchlist",
            constraint,
            BUYER_PATHS["watchlist"],
            [],
            "(track quarterly until next inflection event)",
        )

    # Below watchlist threshold
    return (
        "disqualified",
        constraint,
        BUYER_PATHS["disqualified"],
        [],
        "(no outreach — score below watchlist threshold)",
    )
