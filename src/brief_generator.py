"""
brief_generator.py
==================
Produces the diagnostic brief — the artifact that, in the operating model, gets
forwarded by an investor partner to a founder, or sent directly to a founder
in the second-best case.

The brief is intentionally short (one page) and structured so a non-author
can read it and reach the same routing decision. That is the
communication-axis test in Zeutara's scoring rubric.

Sections:
  - Header (company, score, route, confidence)
  - Why this company now (primary structural constraint + evidence)
  - Reason codes (audit trail)
  - Suggested buyer path
  - Recommended outreach angle
  - Discovery-call questions
  - Human review checklist (what an analyst must verify before sending)
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import List

from schema import CompanyRecord, Evidence


HUMAN_REVIEW_CHECKLIST = [
    "Verify the funding date and round size against an independent source (Crunchbase, PitchBook, or the announcement itself).",
    "Confirm the founder is still the operating owner of GTM (LinkedIn role descriptions, recent founder posts).",
    "Check whether any of the disqualifier signals were missed — fractional COO/CRO recently announced, VC platform team engaged, competitor advisory firm visible.",
    "Confirm there is no active fundraise underway (founder distraction). LinkedIn fundraising posts, recent press, calendar of investor demo days.",
    "If routing as warm_intro_candidate, confirm a real investor relationship path exists before forwarding.",
]


def render_brief(record: CompanyRecord, evidence: List[Evidence]) -> str:
    now = datetime.utcnow().strftime("%Y-%m-%d")
    constraint = record.primary_structural_constraint or "operational_complexity_growth"

    # Header
    parts: List[str] = []
    parts.append(f"# Diagnostic Brief — {record.company_name}")
    parts.append("")
    parts.append(f"*Generated {now} — Zeutara Inflection Detector — extraction mode: `{record.extraction_mode}`*")
    parts.append("")
    parts.append(f"- **Inflection score:** {record.inflection_score} / 100")
    parts.append(f"- **Confidence:** {record.confidence_score} / 100")
    parts.append(f"- **Disqualifier penalty applied:** {record.disqualifier_penalty}")
    parts.append(f"- **Route:** `{record.route}`")
    parts.append(f"- **Primary structural constraint:** `{constraint}`")
    parts.append(f"- **Source confidence:** {record.signals.source_confidence}")
    if record.company_url:
        parts.append(f"- **Company URL:** {record.company_url}")
    if record.funding_announcement_url:
        parts.append(f"- **Funding announcement:** {record.funding_announcement_url}")
    parts.append("")

    # Why this company now
    parts.append("## Why this company, now")
    parts.append("")
    parts.append(_constraint_narrative(record))
    parts.append("")

    # Evidence
    if evidence:
        parts.append("### Evidence")
        parts.append("")
        for e in evidence:
            parts.append(f"- **{e.signal}** ({e.confidence}): \"{e.snippet}\"")
            if e.source_url:
                parts.append(f"  - Source: {e.source_url}")
        parts.append("")
    else:
        parts.append("### Evidence")
        parts.append("")
        parts.append("- (No specific evidence snippets captured. This brief is built on aggregate signals only; raise source confidence by adding inputs.)")
        parts.append("")

    # Reason codes
    parts.append("### Reason codes (audit trail)")
    parts.append("")
    if record.reason_codes:
        for r in record.reason_codes:
            parts.append(f"- `{r}`")
    else:
        parts.append("- (none)")
    parts.append("")

    # Buyer path
    parts.append("## Suggested buyer path")
    parts.append("")
    parts.append(record.suggested_buyer_path or "(not set)")
    parts.append("")

    # Outreach angle
    parts.append("## Recommended outreach angle")
    parts.append("")
    parts.append(f"> {record.recommended_outreach_angle or '(not set)'}")
    parts.append("")

    # Discovery questions
    parts.append("## Discovery-call questions")
    parts.append("")
    if record.discovery_questions:
        for q in record.discovery_questions:
            parts.append(f"- {q}")
    else:
        parts.append("- (No outreach scheduled — see route.)")
    parts.append("")

    # Human review
    parts.append("## Human review checkpoint")
    parts.append("")
    parts.append("Before this brief is forwarded or used in outreach, the assigned analyst must complete the following:")
    parts.append("")
    for item in HUMAN_REVIEW_CHECKLIST:
        parts.append(f"- [ ] {item}")
    parts.append("")

    # Footer
    parts.append("---")
    parts.append("")
    parts.append(
        "*This brief is a routing recommendation, not a sales pitch. The "
        "system is designed to fail toward `watchlist` and `disqualified` "
        "before forwarding low-confidence accounts into senior attention.*"
    )

    return "\n".join(parts)


def _constraint_narrative(record: CompanyRecord) -> str:
    """A single short paragraph that explains the constraint in plain English,
    grounded in which signals fired."""
    sig = record.signals
    constraint = record.primary_structural_constraint

    bits: List[str] = []

    if constraint == "gtm_leader_transition":
        bits.append(
            f"{record.company_name} appears to be hiring its first dedicated "
            f"GTM leader. This is the moment Zeutara's product is most "
            f"valuable — the operating architecture the new hire inherits in "
            f"the first 90 days determines whether they succeed or churn."
        )
    elif constraint == "founder_led_gtm_bottleneck":
        bits.append(
            f"{record.company_name} shows founder-led sales as the primary "
            f"motion. Funded companies in this state typically face a 6–9 "
            f"month window before founder-bandwidth becomes the growth ceiling."
        )
    elif constraint == "enterprise_motion_emerging":
        bits.append(
            f"{record.company_name} is signalling movement up-market into "
            f"enterprise. Every revenue process — pricing, pipeline, deal "
            f"review, forecasting — needs to be rebuilt for the new motion, "
            f"and the cost of doing it after the first lost deal is high."
        )
    elif constraint == "capital_to_operating_translation":
        bits.append(
            f"{record.company_name} has recent capital plus multiple open "
            f"GTM-adjacent roles. The next 90 days set whether the round is "
            f"converted into installed operating control or burned through "
            f"by hiring without architecture."
        )
    else:
        bits.append(
            f"{record.company_name} shows operational complexity rising "
            f"faster than the operating cadence in place to absorb it. "
            f"Specific signal set is in the reason codes below."
        )

    # Add a sentence about funding stage if known
    if sig.estimated_stage in ("seed", "series_a"):
        bits.append(
            f" Stage is consistent with Zeutara's sweet spot "
            f"({sig.estimated_stage.replace('_', ' ')})."
        )
    elif sig.estimated_stage == "pre_seed":
        bits.append(" Stage is pre-seed — eligible but watch-listed by default until traction is visible.")
    elif sig.estimated_stage == "series_b_plus":
        bits.append(" Stage is Series B+ — above Zeutara's stated sweet spot; verify before pursuing.")

    return "".join(bits)


def write_brief(record: CompanyRecord, evidence: List[Evidence], briefs_dir: Path) -> Path:
    briefs_dir.mkdir(parents=True, exist_ok=True)
    fname = "".join(c if c.isalnum() else "_" for c in record.company_name).strip("_").lower()
    fname = fname or "company"
    out = briefs_dir / f"{fname}_brief.md"
    out.write_text(render_brief(record, evidence), encoding="utf-8")
    return out
