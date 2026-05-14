"""
config.py
=========
Tunable parameters for the Inflection Detector.

Everything that a Zeutara analyst might want to recalibrate after seeing
closed-won / closed-lost data lives here, not buried inside the scorer. That
matters because the whole point of the feedback loop is to retune these
weights without rewriting the pipeline.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Scoring weights — positive contributions
# ---------------------------------------------------------------------------
# Total max if every positive signal fires: 100.
# Disqualifier penalties are applied separately and can drive the score below
# the route thresholds, ensuring a single hard-no can disqualify even an
# otherwise strong account.

POSITIVE_WEIGHTS = {
    # Stage fit: seed / series_a is the sweet spot.
    "stage_seed_or_series_a": 15,
    "stage_pre_seed": 5,           # eligible but lower base weight

    # Sector / business model — B2B revenue motion matters more than vertical.
    "b2b_revenue_motion": 12,

    # Headcount band 10–75 is Zeutara's stated sweet spot.
    "headcount_in_band": 8,

    # Inflection signals — the heart of the score.
    "recent_funding": 12,                  # raised in last ~12 months
    "hiring_first_gtm_leader": 18,         # the single strongest signal
    "hiring_operations_role": 8,
    "multiple_open_gtm_roles": 6,
    "founder_led_sales_signal": 10,
    "enterprise_expansion_signal": 7,
    "board_or_investor_pressure": 4,
}

# Maximum theoretical positive score if every weight fires (sanity check; the
# real cap is held to 100 by the scorer).
MAX_POSITIVE_SCORE = sum(POSITIVE_WEIGHTS.values())  # 105 — capped at 100


# ---------------------------------------------------------------------------
# Disqualifier penalties (negative)
# ---------------------------------------------------------------------------
# Each entry maps to a Signals field name. Severity is calibrated so a single
# severe disqualifier alone takes the score below the "warm intro" threshold
# even from a 95 starting point.

DISQUALIFIER_PENALTIES = {
    "no_b2b_revenue_motion": -45,
    "local_smb_only": -35,
    "mature_revops_in_place": -40,
    "operating_partner_already_engaged": -45,
    "competitor_advisory_engaged": -35,
    "mid_fundraise": -25,
    "raise_too_old": -20,
    "purely_technical_founder_no_gtm": -25,
    "investor_has_platform_team": -15,
}


# ---------------------------------------------------------------------------
# Route thresholds
# ---------------------------------------------------------------------------
# Inflection score combined with confidence determines the route.
#
# Confidence matters: a 90 with low confidence is a watchlist, not a partner
# forward. This is the single biggest lever against the 5x failure mode of
# pushing false positives into senior attention.

ROUTE_THRESHOLDS = {
    # Warm intro candidate: high score + high confidence + no severe disqualifier
    "warm_intro_min_score": 70,
    "warm_intro_min_confidence": 65,

    # Direct outreach candidate: solid score but lower confidence OR no warm path
    "direct_outreach_min_score": 55,
    "direct_outreach_min_confidence": 50,

    # Watchlist: real signal but not yet actionable
    "watchlist_min_score": 35,

    # Below watchlist_min_score with no other route triggered -> disqualified
}


# ---------------------------------------------------------------------------
# Confidence scoring
# ---------------------------------------------------------------------------
# Confidence is a function of: how many sources we pulled, how fresh they are,
# and whether the extractor produced direct evidence snippets.

CONFIDENCE_WEIGHTS = {
    "per_source_used": 18,         # each distinct page contributes
    "per_evidence_snippet": 6,     # cap applied in scorer
    "fresh_within_90_days": 15,
    "fresh_within_30_days": 25,    # additive with 90-day (so very fresh = both)
}

CONFIDENCE_MAX = 100


# ---------------------------------------------------------------------------
# Disqualifier severity classification (for reason codes and reviewer display)
# ---------------------------------------------------------------------------

SEVERE_DISQUALIFIERS = {
    "no_b2b_revenue_motion",
    "local_smb_only",
    "mature_revops_in_place",
    "operating_partner_already_engaged",
    "competitor_advisory_engaged",
}


# ---------------------------------------------------------------------------
# VC platform team list (illustrative, not exhaustive).
# Used by the rule-based extractor to flag the "investor_has_platform_team"
# disqualifier. Pulled from public knowledge of which funds run internal
# operating / platform teams; should be reviewed quarterly.
# ---------------------------------------------------------------------------

VCS_WITH_STRONG_PLATFORM_TEAMS = {
    "andreessen horowitz", "a16z",
    "sequoia", "sequoia capital",
    "first round", "first round capital",
    "union square ventures", "usv",
    "nfx",
    "greylock",
    "bessemer",
    "lightspeed",
    "accel",
    "index ventures",
    "bain capital ventures",
    "kleiner perkins",
    "founders fund",
    "general catalyst",
}


# ---------------------------------------------------------------------------
# Pre-baked outreach angles per primary structural constraint.
# These are intentionally short. The brief generator can override with
# Claude-generated copy in live mode.
# ---------------------------------------------------------------------------

OUTREACH_ANGLES = {
    "founder_led_gtm_bottleneck": (
        "Your next constraint may not be demand. It may be the operating system "
        "required to convert demand into repeatable pipeline."
    ),
    "gtm_leader_transition": (
        "The first head of sales fails 60%+ of the time. The deciding variable "
        "is the operating architecture they inherit on day one, not the hire."
    ),
    "enterprise_motion_emerging": (
        "Moving up-market changes every revenue process simultaneously — pricing, "
        "pipeline, deal review, forecasting. Most teams build it after the first "
        "lost deal. The ones who scale build it before."
    ),
    "capital_to_operating_translation": (
        "A fresh round is the easiest time to install operating control; it is "
        "also the easiest time to spend through one without it. The next 90 days "
        "decide which."
    ),
    "operational_complexity_growth": (
        "Growth is rarely killed by demand. It is killed by complexity outpacing "
        "the operating cadence built to absorb it."
    ),
}


# ---------------------------------------------------------------------------
# Discovery-call question templates per constraint. Used in the brief.
# ---------------------------------------------------------------------------

DISCOVERY_QUESTIONS = {
    "founder_led_gtm_bottleneck": [
        "Who owns the pipeline today, you or someone else?",
        "What percentage of closed deals in the last 90 days closed without you in the room?",
        "What is your hand-off process from marketing to sales today?",
    ],
    "gtm_leader_transition": [
        "How are you measuring the first 90 days of the new GTM hire?",
        "What does the pipeline review cadence look like once the hire starts?",
        "What is the agreed split of accountability between you and them?",
    ],
    "enterprise_motion_emerging": [
        "How is your pricing structured today, and is it working in deals above $50k ACV?",
        "Who owns enterprise deal review?",
        "What is your current cycle time from first conversation to signed contract?",
    ],
    "capital_to_operating_translation": [
        "What three operating systems are you planning to install with the new capital?",
        "Who owns the board reporting cadence?",
        "What metric do you most want to be able to defend at the next board meeting?",
    ],
    "operational_complexity_growth": [
        "Where is the cadence breaking — weekly review, monthly close, quarterly planning?",
        "Which decisions are still bottlenecked at the founder level?",
        "What is the largest unforced operating cost in the business right now?",
    ],
}


# ---------------------------------------------------------------------------
# Buyer path mapping. Who should the brief be addressed to / forwarded by?
# ---------------------------------------------------------------------------

BUYER_PATHS = {
    "warm_intro_candidate": (
        "Forwardable investor brief — to lead investor partner, who introduces "
        "to founder/CEO."
    ),
    "direct_outreach_candidate": (
        "Direct founder brief — to founder/CEO, with co-founder cc'd if visible."
    ),
    "watchlist": (
        "No outreach yet — track the inflection signals quarterly until the "
        "window opens (typically next funding milestone or first GTM hire)."
    ),
    "disqualified": (
        "Do not pursue. Reason codes above explain the disqualifier."
    ),
}
