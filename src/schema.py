"""
schema.py
=========
The data model for the Zeutara Inflection Detector.

A SignalSchema is the structured representation of a prospect that we extract
from messy public information (a homepage, a careers page, a funding
announcement, a news mention). Everything downstream — scoring, routing, brief
generation — operates on this schema.

The schema is deliberately small. Each field exists because it changes the
decision Zeutara would make about the account. Fields that "would be nice"
but do not change the routing decision are kept out.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any


# ---------------------------------------------------------------------------
# Enumerated values used by extractor + scorer. Strings, not Enums, so the
# JSON output stays portable (a reviewer can paste it into a spreadsheet).
# ---------------------------------------------------------------------------

STAGES = ("idea", "pre_seed", "seed", "series_a", "series_b_plus", "unknown")

ROUTES = (
    "warm_intro_candidate",
    "direct_outreach_candidate",
    "watchlist",
    "disqualified",
)

CONFIDENCE_LEVELS = ("high", "medium", "low")


# ---------------------------------------------------------------------------
# Evidence: every signal carries a snippet + source URL so a human reviewer
# can audit the decision. Without this the system is a black box and Zeutara
# cannot trust it at partner level.
# ---------------------------------------------------------------------------

@dataclass
class Evidence:
    signal: str           # short label, e.g. "hiring_first_sales_leader"
    snippet: str          # the actual text we found (trimmed)
    source_url: str       # where we found it
    confidence: str = "medium"   # high | medium | low

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Signals: a small set of boolean / categorical fields the scorer cares about.
# Each one maps to a specific question Zeutara would ask before forwarding an
# account to a partner.
# ---------------------------------------------------------------------------

@dataclass
class Signals:
    # --- Inflection signals (positive evidence we want a high score on) ---
    recent_funding: bool = False             # raised in last ~12 months
    funding_age_months: Optional[int] = None # how old the round is
    hiring_first_gtm_leader: bool = False    # first head of sales / RevOps / CRO
    hiring_operations_role: bool = False     # COO / Ops / Chief of Staff
    founder_led_sales_signal: bool = False   # founder still owns pipeline
    enterprise_expansion_signal: bool = False  # moving up-market
    multiple_open_gtm_roles: bool = False    # 3+ open GTM roles
    board_or_investor_pressure: bool = False # next-round prep visible

    # --- Disqualifier signals (negative evidence) ---
    no_b2b_revenue_motion: bool = False      # pure consumer / no commercial signal
    local_smb_only: bool = False             # geographically tiny, low retainer cap
    mature_revops_in_place: bool = False     # has VP RevOps, COO, CRO already
    operating_partner_already_engaged: bool = False  # fractional COO/CRO announced
    competitor_advisory_engaged: bool = False  # public mention of another firm
    mid_fundraise: bool = False              # actively raising right now
    raise_too_old: bool = False              # >18 mo since last round, no movement
    purely_technical_founder_no_gtm: bool = False  # founder profile has no GTM signal
    investor_has_platform_team: bool = False  # backed by a16z/USV/FR/Sequoia/NFX-tier

    # --- Categorical fields ---
    estimated_stage: str = "unknown"         # one of STAGES
    sector: Optional[str] = None             # e.g. "B2B SaaS", "fintech infra"
    business_model: Optional[str] = None     # "SaaS", "marketplace", "infra"
    headcount_estimate: Optional[int] = None
    headquarters_region: Optional[str] = None  # e.g. "US-NY", "US-CA"

    # --- Metadata ---
    sources_used: List[str] = field(default_factory=list)
    data_freshness_days: Optional[int] = None  # how recent is the freshest source
    source_confidence: str = "medium"          # high | medium | low

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# The full record for a single company: input identifiers + extracted signals
# + scoring + routing + brief. This is what gets exported.
# ---------------------------------------------------------------------------

@dataclass
class CompanyRecord:
    # Input
    company_name: str
    company_url: Optional[str] = None
    funding_announcement_url: Optional[str] = None
    notes: Optional[str] = None  # analyst-provided context, if any

    # Extracted
    signals: Signals = field(default_factory=Signals)
    evidence: List[Evidence] = field(default_factory=list)

    # Scoring
    inflection_score: int = 0          # 0-100
    confidence_score: int = 0          # 0-100
    disqualifier_penalty: int = 0      # negative integer applied to score
    reason_codes: List[str] = field(default_factory=list)

    # Routing
    route: str = "watchlist"           # one of ROUTES
    primary_structural_constraint: Optional[str] = None
    suggested_buyer_path: Optional[str] = None
    recommended_outreach_angle: Optional[str] = None
    discovery_questions: List[str] = field(default_factory=list)

    # Output
    brief_path: Optional[str] = None
    extraction_mode: str = "rule_based"   # "rule_based" | "claude_live"

    def to_flat_row(self) -> Dict[str, Any]:
        """Flatten for CSV export. Lists are joined with ' | '."""
        return {
            "company_name": self.company_name,
            "company_url": self.company_url or "",
            "estimated_stage": self.signals.estimated_stage,
            "sector": self.signals.sector or "",
            "headcount_estimate": self.signals.headcount_estimate or "",
            "inflection_score": self.inflection_score,
            "confidence_score": self.confidence_score,
            "disqualifier_penalty": self.disqualifier_penalty,
            "route": self.route,
            "primary_structural_constraint": self.primary_structural_constraint or "",
            "suggested_buyer_path": self.suggested_buyer_path or "",
            "recommended_outreach_angle": self.recommended_outreach_angle or "",
            "reason_codes": " | ".join(self.reason_codes),
            "sources_used": " | ".join(self.signals.sources_used),
            "source_confidence": self.signals.source_confidence,
            "extraction_mode": self.extraction_mode,
            "brief_path": self.brief_path or "",
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "company_name": self.company_name,
            "company_url": self.company_url,
            "funding_announcement_url": self.funding_announcement_url,
            "notes": self.notes,
            "signals": self.signals.to_dict(),
            "evidence": [e.to_dict() for e in self.evidence],
            "inflection_score": self.inflection_score,
            "confidence_score": self.confidence_score,
            "disqualifier_penalty": self.disqualifier_penalty,
            "reason_codes": self.reason_codes,
            "route": self.route,
            "primary_structural_constraint": self.primary_structural_constraint,
            "suggested_buyer_path": self.suggested_buyer_path,
            "recommended_outreach_angle": self.recommended_outreach_angle,
            "discovery_questions": self.discovery_questions,
            "brief_path": self.brief_path,
            "extraction_mode": self.extraction_mode,
        }
