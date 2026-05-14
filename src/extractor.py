"""
extractor.py
============
Turns a bag of fetched HTML pages into a structured Signals object.

Two modes, with the same output schema:

1. rule_based  (default)
   Regex + keyword matching against the HTML text. Deterministic, fast, runs
   with zero external dependencies beyond the stdlib + BeautifulSoup. Used in
   tests and in any reviewer environment without an API key.

2. claude_live  (--live with ANTHROPIC_API_KEY set)
   Sends the cleaned text content to Claude with a strict JSON schema and
   asks it to populate the Signals fields and produce evidence snippets with
   inline citations. This is the agentic / AI-leverage path. The same schema
   comes back out, so the rest of the pipeline is mode-agnostic.

The defensible split: extraction is the layer where AI adds the most value
(messy unstructured -> structured). Scoring is deterministic on purpose so
the reasons are auditable. We do not ask Claude to do the scoring.
"""

from __future__ import annotations

import json
import os
import re
from typing import List, Tuple

from schema import Signals, Evidence
from fetcher import FetchedPage
from config import VCS_WITH_STRONG_PLATFORM_TEAMS

# bs4 is a small, ubiquitous dep. Soft import so the module still loads if it
# is missing — we just degrade to using raw HTML, which is uglier but works.
try:
    from bs4 import BeautifulSoup  # type: ignore
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False

try:
    import anthropic  # type: ignore
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False


# ---------------------------------------------------------------------------
# Text utilities
# ---------------------------------------------------------------------------

def _html_to_text(html: str) -> str:
    """Strip HTML to readable text. Falls back to a naive tag-strip if bs4 is
    missing so the extractor still works in minimal environments."""
    if not html:
        return ""
    if HAS_BS4:
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text = soup.get_text(separator=" ", strip=True)
    else:
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text).strip()
    return text


def _find_snippet(text: str, pattern: re.Pattern, window: int = 120) -> str:
    """Return a short snippet around the first regex match, for the evidence trail."""
    m = pattern.search(text)
    if not m:
        return ""
    start = max(0, m.start() - window // 2)
    end = min(len(text), m.end() + window // 2)
    snippet = text[start:end].strip()
    return re.sub(r"\s+", " ", snippet)


# ---------------------------------------------------------------------------
# Rule-based signal patterns
# ---------------------------------------------------------------------------
# Each pattern is paired with the Signals field it populates and a short
# label for the reason code. Patterns are intentionally readable, not clever.

GTM_LEADER_PATTERN = re.compile(
    r"\b(head of (sales|revenue|gtm)|vp (of )?sales|chief revenue officer|"
    r"cro\b|first sales hire|founding (account executive|ae))",
    re.IGNORECASE,
)

OPS_LEADER_PATTERN = re.compile(
    r"\b(chief operating officer|coo\b|head of operations|chief of staff|"
    r"vp (of )?operations|head of revenue operations|revops)",
    re.IGNORECASE,
)

FOUNDER_LED_SALES_PATTERN = re.compile(
    r"\b(founder[- ]led (sales|pipeline|growth)|ceo (owns|runs) sales|"
    r"founder still closes|founder[- ]selling)",
    re.IGNORECASE,
)

ENTERPRISE_EXPANSION_PATTERN = re.compile(
    r"\b(enterprise|fortune 500|fortune 1000|mid[- ]market|"
    r"large customers|moving up[- ]market|enterprise tier)",
    re.IGNORECASE,
)

RECENT_FUNDING_PATTERN = re.compile(
    r"(?:"
    # Form 1: "raised $14M Series A" / "closed a $4M seed round" — word boundary
    # before the verb so we don't trigger inside other words.
    r"\b(?:raised|closed|announced|secured)\s+(?:a\s+)?\$?\d+(?:\.\d+)?"
    r"\s*(?:m|million|k|thousand|b|billion)?\s*(?:seed|series\s*[abcde]|round)?"
    r"|"
    # Form 2: "$4M raised from" / "$14M Series A" / "$4M in seed funding" —
    # starts with a literal $; word boundary doesn't apply.
    r"\$\d+(?:\.\d+)?\s*(?:m|million|k|thousand|b|billion)"
    r"\s+(?:raised|in\s+(?:funding|seed|series)|seed|series\s*[abcde]|round)"
    r")",
    re.IGNORECASE,
)

# Stage patterns: accept hyphen-separated forms ("Seed-stage", "Series-A").
STAGE_SEED_PATTERN = re.compile(r"\bseed[\s\-]+(round|funding|stage)", re.IGNORECASE)
STAGE_SERIES_A_PATTERN = re.compile(r"\bseries[\s\-]*a\b", re.IGNORECASE)
STAGE_SERIES_B_PATTERN = re.compile(r"\bseries[\s\-]*[bcde]\b", re.IGNORECASE)
STAGE_PRE_SEED_PATTERN = re.compile(r"\bpre[\s\-]*seed\b", re.IGNORECASE)

B2B_MOTION_PATTERN = re.compile(
    r"\b(b2b|enterprise|saas|platform for (teams|companies|businesses)|"
    r"for (sales|finance|operations|hr|engineering) teams)",
    re.IGNORECASE,
)

MATURE_REVOPS_PATTERN = re.compile(
    r"\b(vp (of )?revenue operations|head of revenue operations|"
    r"director of revops|chief operating officer.{0,40}announced|"
    r"appointed (our|their) (coo|cro|vp sales))",
    re.IGNORECASE,
)

# Words that, when nearby, signal an OPEN ROLE rather than a filled seat.
# Used to suppress false positives on the mature-RevOps disqualifier.
_OPEN_ROLE_CONTEXT = re.compile(
    r"\b(hiring|looking for|seeking|searching for|recruit(?:ing)?|"
    r"first|new|open role|job posting|join us as|we're hiring)\b",
    re.IGNORECASE,
)


def _is_open_role_context(text: str, match_start: int, window: int = 60) -> bool:
    """True if 'hiring', 'first', etc. appears just before the match — meaning
    the title refers to an open role, not a filled seat."""
    pre = text[max(0, match_start - window):match_start]
    return bool(_OPEN_ROLE_CONTEXT.search(pre))

FRACTIONAL_OPERATOR_PATTERN = re.compile(
    r"\b(fractional (coo|cro|cmo|cfo)|interim (coo|cro|cfo)|"
    r"operating partner.{0,60}(joined|engaged))",
    re.IGNORECASE,
)

LOCAL_SMB_PATTERN = re.compile(
    r"\b(local (business|customers|community)|family[- ]owned|"
    r"serving the .{0,20} area|brick[- ]and[- ]mortar only)",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Headcount extraction — looks for explicit team-size mentions.
# ---------------------------------------------------------------------------

HEADCOUNT_PATTERN = re.compile(
    r"\b(?:team of|we are|now)\s+(\d{1,3})"
    r"(?:\s+(?:people|employees|engineers|teammates|staff|across))?\b",
    re.IGNORECASE,
)


def _extract_headcount(text: str) -> int | None:
    m = HEADCOUNT_PATTERN.search(text)
    if not m:
        return None
    try:
        return int(m.group(1))
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Stage inference
# ---------------------------------------------------------------------------

def _infer_stage(text: str) -> str:
    if STAGE_SERIES_B_PATTERN.search(text):
        return "series_b_plus"
    if STAGE_SERIES_A_PATTERN.search(text):
        return "series_a"
    if STAGE_SEED_PATTERN.search(text):
        return "seed"
    if STAGE_PRE_SEED_PATTERN.search(text):
        return "pre_seed"
    return "unknown"


# ---------------------------------------------------------------------------
# Investor / VC platform team detection
# ---------------------------------------------------------------------------

def _detect_vc_platform_team(text: str) -> Tuple[bool, str]:
    """Return (has_platform_team, matched_vc_name).

    Uses word-boundary regex matching so 'accel' inside 'accelerate' does not
    fire the Accel false positive. Multi-word VC names are matched on the
    full phrase.
    """
    text_lower = text.lower()
    for vc in VCS_WITH_STRONG_PLATFORM_TEAMS:
        # Escape spaces -> require word boundaries on both ends.
        pattern = r"\b" + re.escape(vc) + r"\b"
        if re.search(pattern, text_lower):
            return True, vc
    return False, ""


# ---------------------------------------------------------------------------
# Open-role counting (rough — counts careers page job-title-like patterns)
# ---------------------------------------------------------------------------

JOB_TITLE_HINT = re.compile(
    r"\b(senior\s+|staff\s+|principal\s+|lead\s+)?(account executive|sdr|bdr|"
    r"customer success|sales engineer|sales operations|revenue operations|"
    r"head of growth|growth marketer|content marketer)\b",
    re.IGNORECASE,
)


def _count_open_gtm_roles(careers_text: str) -> int:
    if not careers_text:
        return 0
    return len(JOB_TITLE_HINT.findall(careers_text))


# ===========================================================================
# Rule-based extraction
# ===========================================================================

def extract_signals_rule_based(pages: List[FetchedPage]) -> Tuple[Signals, List[Evidence]]:
    """
    Walk every fetched page, run the patterns, populate Signals + Evidence.
    Order of pages does not matter; signals are OR'd across pages.
    """
    signals = Signals()
    evidence: List[Evidence] = []

    all_text_chunks: List[Tuple[str, str, str]] = []  # (text, source_url, source_label)
    careers_text = ""
    funding_text = ""

    for page in pages:
        if not page.ok:
            continue
        text = _html_to_text(page.html)
        all_text_chunks.append((text, page.url, page.source_label))
        signals.sources_used.append(page.source_label)
        if page.kind == "careers":
            careers_text = text
        elif page.kind == "funding_announcement":
            funding_text = text

    full_text = "  ".join(t for t, _, _ in all_text_chunks)

    # --- Stage
    signals.estimated_stage = _infer_stage(full_text)

    # --- B2B motion (with negation check: "no B2B", "not B2B" should NOT
    # count as a positive B2B match).
    b2b_match = B2B_MOTION_PATTERN.search(full_text)
    b2b_negated = False
    if b2b_match:
        pre = full_text[max(0, b2b_match.start() - 20):b2b_match.start()].lower()
        if re.search(r"\b(no|not|without|lack(?:s|ing)?)\b\s*$", pre):
            b2b_negated = True

    if b2b_match and not b2b_negated:
        signals.business_model = "B2B"
        snip = _find_snippet(full_text, B2B_MOTION_PATTERN)
        if snip:
            evidence.append(Evidence(
                signal="b2b_revenue_motion",
                snippet=snip,
                source_url=all_text_chunks[0][1] if all_text_chunks else "",
                confidence="medium",
            ))
    else:
        # Either no B2B match at all, or explicitly negated.
        if full_text:
            signals.no_b2b_revenue_motion = True
            evidence.append(Evidence(
                signal="no_b2b_revenue_motion",
                snippet="No B2B revenue-motion language detected on fetched pages."
                        if not b2b_negated else
                        "B2B language present but explicitly negated in source.",
                source_url=all_text_chunks[0][1] if all_text_chunks else "",
                confidence="low",
            ))

    # --- Recent funding
    if RECENT_FUNDING_PATTERN.search(full_text):
        signals.recent_funding = True
        snip = _find_snippet(full_text, RECENT_FUNDING_PATTERN)
        evidence.append(Evidence(
            signal="recent_funding",
            snippet=snip,
            source_url=_first_url_for(all_text_chunks, snip),
            confidence="medium",
        ))

    # --- Hiring signals
    if GTM_LEADER_PATTERN.search(careers_text or full_text):
        signals.hiring_first_gtm_leader = True
        snip = _find_snippet(careers_text or full_text, GTM_LEADER_PATTERN)
        evidence.append(Evidence(
            signal="hiring_first_gtm_leader",
            snippet=snip,
            source_url=_first_url_for(all_text_chunks, snip),
            confidence="high" if careers_text else "medium",
        ))

    if OPS_LEADER_PATTERN.search(careers_text or full_text):
        signals.hiring_operations_role = True
        snip = _find_snippet(careers_text or full_text, OPS_LEADER_PATTERN)
        evidence.append(Evidence(
            signal="hiring_operations_role",
            snippet=snip,
            source_url=_first_url_for(all_text_chunks, snip),
            confidence="medium",
        ))

    if FOUNDER_LED_SALES_PATTERN.search(full_text):
        signals.founder_led_sales_signal = True
        snip = _find_snippet(full_text, FOUNDER_LED_SALES_PATTERN)
        evidence.append(Evidence(
            signal="founder_led_sales_signal",
            snippet=snip,
            source_url=_first_url_for(all_text_chunks, snip),
            confidence="medium",
        ))

    if ENTERPRISE_EXPANSION_PATTERN.search(full_text):
        signals.enterprise_expansion_signal = True
        snip = _find_snippet(full_text, ENTERPRISE_EXPANSION_PATTERN)
        evidence.append(Evidence(
            signal="enterprise_expansion_signal",
            snippet=snip,
            source_url=_first_url_for(all_text_chunks, snip),
            confidence="medium",
        ))

    # --- Open GTM role count
    open_role_count = _count_open_gtm_roles(careers_text)
    if open_role_count >= 3:
        signals.multiple_open_gtm_roles = True
        evidence.append(Evidence(
            signal="multiple_open_gtm_roles",
            snippet=f"Detected {open_role_count} open GTM-style roles on careers page.",
            source_url=_first_url_for(all_text_chunks, "careers"),
            confidence="medium",
        ))

    # --- Headcount
    signals.headcount_estimate = _extract_headcount(full_text)

    # --- Mature RevOps disqualifier (suppressed if the title is in an
    # "open role" / "hiring" context — that means they're hiring one, not
    # have one already).
    mr_match = MATURE_REVOPS_PATTERN.search(full_text)
    if mr_match and not _is_open_role_context(full_text, mr_match.start()):
        signals.mature_revops_in_place = True
        snip = _find_snippet(full_text, MATURE_REVOPS_PATTERN)
        evidence.append(Evidence(
            signal="mature_revops_in_place",
            snippet=snip,
            source_url=_first_url_for(all_text_chunks, snip),
            confidence="medium",
        ))

    # --- Fractional/operating partner already engaged
    if FRACTIONAL_OPERATOR_PATTERN.search(full_text):
        signals.operating_partner_already_engaged = True
        snip = _find_snippet(full_text, FRACTIONAL_OPERATOR_PATTERN)
        evidence.append(Evidence(
            signal="operating_partner_already_engaged",
            snippet=snip,
            source_url=_first_url_for(all_text_chunks, snip),
            confidence="medium",
        ))

    # --- Local SMB
    if LOCAL_SMB_PATTERN.search(full_text):
        signals.local_smb_only = True
        snip = _find_snippet(full_text, LOCAL_SMB_PATTERN)
        evidence.append(Evidence(
            signal="local_smb_only",
            snippet=snip,
            source_url=_first_url_for(all_text_chunks, snip),
            confidence="medium",
        ))

    # --- VC platform team
    has_platform, vc_name = _detect_vc_platform_team(full_text)
    if has_platform:
        signals.investor_has_platform_team = True
        evidence.append(Evidence(
            signal="investor_has_platform_team",
            snippet=f"Company is backed by '{vc_name}', which runs an in-house operating/platform team.",
            source_url=_first_url_for(all_text_chunks, vc_name),
            confidence="high",
        ))

    # --- Source confidence (heuristic)
    signals.source_confidence = (
        "high" if len(signals.sources_used) >= 3
        else "medium" if len(signals.sources_used) == 2
        else "low"
    )

    # Funding text strengthens recent_funding evidence; if present and we did
    # not already mark it, do it now.
    if funding_text and not signals.recent_funding:
        signals.recent_funding = True
        evidence.append(Evidence(
            signal="recent_funding",
            snippet=_find_snippet(funding_text, re.compile(r"\b\$\d", re.IGNORECASE)) or
                    "Funding announcement provided as input.",
            source_url="(funding announcement page)",
            confidence="high",
        ))

    return signals, evidence


def _first_url_for(chunks: List[Tuple[str, str, str]], needle: str) -> str:
    """Return the source URL of the first chunk that contains the needle, else ''."""
    if not needle or not chunks:
        return chunks[0][1] if chunks else ""
    for text, url, _ in chunks:
        if needle.lower() in text.lower():
            return url
    return chunks[0][1]


# ===========================================================================
# Claude live extraction
# ===========================================================================

CLAUDE_SYSTEM_PROMPT = """You are an analyst at Zeutara, a growth-strategy firm \
that installs execution architecture for B2B founders at seed to Series A.

You will be given the text content of several public pages about a single \
company: typically a homepage, a careers/jobs page, and optionally a funding \
announcement.

Your job is to extract a strict JSON object describing the company's \
inflection signals. Do not invent facts. If a field cannot be determined from \
the provided text, set it to false / null / "unknown" as appropriate.

For every signal you mark as true, include at least one evidence snippet \
(<=240 chars) that justifies it, with the source label it came from.

Return ONLY valid JSON, no commentary, no markdown fences."""


CLAUDE_USER_TEMPLATE = """Company name: {company_name}

Pages provided:
{pages_block}

Return JSON matching this shape exactly:

{{
  "estimated_stage": "pre_seed|seed|series_a|series_b_plus|unknown",
  "sector": "string or null",
  "business_model": "string or null",
  "headcount_estimate": int or null,
  "recent_funding": bool,
  "hiring_first_gtm_leader": bool,
  "hiring_operations_role": bool,
  "founder_led_sales_signal": bool,
  "enterprise_expansion_signal": bool,
  "multiple_open_gtm_roles": bool,
  "board_or_investor_pressure": bool,
  "no_b2b_revenue_motion": bool,
  "local_smb_only": bool,
  "mature_revops_in_place": bool,
  "operating_partner_already_engaged": bool,
  "competitor_advisory_engaged": bool,
  "mid_fundraise": bool,
  "raise_too_old": bool,
  "purely_technical_founder_no_gtm": bool,
  "investor_has_platform_team": bool,
  "evidence": [
    {{"signal": "field_name", "snippet": "<=240 char quote", "source_label": "which page"}}
  ]
}}"""


def extract_signals_claude(
    pages: List[FetchedPage],
    company_name: str,
) -> Tuple[Signals, List[Evidence]]:
    """
    Claude-based extraction. Falls back to rule-based silently if the API
    key is missing or the SDK is not installed — we never crash on optional
    infra, because the reviewer must always get an answer.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not (HAS_ANTHROPIC and api_key):
        signals, evidence = extract_signals_rule_based(pages)
        return signals, evidence

    # Build the pages_block input
    blocks = []
    for p in pages:
        if not p.ok:
            continue
        text = _html_to_text(p.html)
        # Trim aggressively to keep tokens sane.
        text = text[:6000]
        blocks.append(f"--- {p.source_label} ({p.kind}) ---\n{text}\n")
    pages_block = "\n".join(blocks) if blocks else "(no pages fetched)"

    client = anthropic.Anthropic(api_key=api_key)
    try:
        msg = client.messages.create(
            model=os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-7"),
            max_tokens=2000,
            system=CLAUDE_SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": CLAUDE_USER_TEMPLATE.format(
                    company_name=company_name,
                    pages_block=pages_block,
                ),
            }],
        )
        raw = "".join(b.text for b in msg.content if hasattr(b, "text"))
        # Strip any accidental code fences.
        raw = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw.strip(), flags=re.MULTILINE)
        data = json.loads(raw)
    except Exception:
        # Any failure -> fall back to rule-based and surface it in the source
        # confidence field. Better degraded answer than no answer.
        signals, evidence = extract_signals_rule_based(pages)
        signals.source_confidence = "low"
        return signals, evidence

    # Map JSON to our Signals object. We are tolerant of missing keys.
    signals = Signals()
    bool_fields = [
        "recent_funding", "hiring_first_gtm_leader", "hiring_operations_role",
        "founder_led_sales_signal", "enterprise_expansion_signal",
        "multiple_open_gtm_roles", "board_or_investor_pressure",
        "no_b2b_revenue_motion", "local_smb_only", "mature_revops_in_place",
        "operating_partner_already_engaged", "competitor_advisory_engaged",
        "mid_fundraise", "raise_too_old", "purely_technical_founder_no_gtm",
        "investor_has_platform_team",
    ]
    for f in bool_fields:
        setattr(signals, f, bool(data.get(f)))

    signals.estimated_stage = data.get("estimated_stage", "unknown") or "unknown"
    signals.sector = data.get("sector")
    signals.business_model = data.get("business_model")
    hc = data.get("headcount_estimate")
    if isinstance(hc, int):
        signals.headcount_estimate = hc

    signals.sources_used = [p.source_label for p in pages if p.ok]
    signals.source_confidence = "high" if len(signals.sources_used) >= 3 else "medium"

    evidence_list: List[Evidence] = []
    for e in data.get("evidence", []) or []:
        if not isinstance(e, dict):
            continue
        evidence_list.append(Evidence(
            signal=str(e.get("signal", ""))[:80],
            snippet=str(e.get("snippet", ""))[:240],
            source_url=str(e.get("source_label", ""))[:120],
            confidence="high",
        ))

    return signals, evidence_list


# ===========================================================================
# Public entry point
# ===========================================================================

def extract(pages: List[FetchedPage], company_name: str, mode: str
            ) -> Tuple[Signals, List[Evidence], str]:
    """
    Dispatch to the requested extraction mode. Returns the mode actually used
    so the caller can record it on the CompanyRecord.
    """
    if mode == "claude_live":
        # extract_signals_claude already self-degrades to rule-based if keys
        # are missing, but we still tag the record honestly.
        if not (HAS_ANTHROPIC and os.environ.get("ANTHROPIC_API_KEY")):
            signals, evidence = extract_signals_rule_based(pages)
            return signals, evidence, "rule_based"
        signals, evidence = extract_signals_claude(pages, company_name)
        return signals, evidence, "claude_live"

    signals, evidence = extract_signals_rule_based(pages)
    return signals, evidence, "rule_based"
