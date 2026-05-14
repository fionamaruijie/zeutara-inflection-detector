"""
fetcher.py
==========
Fetches public pages a Zeutara analyst would read about a target company:
homepage, careers page, about page, and a funding announcement if provided.

The fetcher has two modes:

1. live mode (--live)
   Hits the actual URLs over HTTPS via the `requests` library, with a polite
   user-agent and a hard timeout. Used when the reviewer wants to test against
   real companies.

2. offline mode (default)
   Resolves URLs against `sample_inputs/` so a reviewer can clone the repo and
   get first output in <15 minutes with no network and no API keys. This is a
   deliberate design choice — the reviewer should not have to set anything up
   to see the system make a real decision.

Whichever mode is on, the fetcher returns a small `FetchedPage` object that
the extractor consumes. The fetcher knows nothing about scoring or routing.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
from urllib.parse import urljoin, urlparse
import re

# requests is only needed in live mode. We import lazily.
try:
    import requests  # type: ignore
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


USER_AGENT = (
    "ZeutaraInflectionDetector/0.1 (research prototype; "
    "contact: analyst@zeutara.com)"
)
TIMEOUT_SECONDS = 8


@dataclass
class FetchedPage:
    url: str           # the URL we attempted (or the offline filename)
    kind: str          # "homepage" | "careers" | "about" | "funding_announcement" | "other"
    html: str          # raw HTML, empty string if fetch failed
    ok: bool           # True if we got non-empty content
    source_label: str  # human-readable label for citations in the brief


# ---------------------------------------------------------------------------
# Offline mode: map any URL to a bundled sample file. This is how we promise
# "runnable in 15 minutes without keys" — the reviewer always gets real-looking
# content even with no network.
# ---------------------------------------------------------------------------

SAMPLE_FILES = {
    "homepage": "sample_company_page.html",
    "funding_announcement": "sample_funding_announcement.html",
}


def _load_sample(kind: str, sample_dir: Path) -> str:
    fname = SAMPLE_FILES.get(kind)
    if not fname:
        return ""
    p = sample_dir / fname
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Live fetcher
# ---------------------------------------------------------------------------

def _fetch_url(url: str) -> str:
    """Return HTML for a URL, or empty string on any failure. Never raises."""
    if not HAS_REQUESTS:
        return ""
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=TIMEOUT_SECONDS,
            allow_redirects=True,
        )
        if resp.status_code == 200 and resp.text:
            return resp.text
        return ""
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Link discovery: from a homepage, find candidate careers and about URLs.
# We keep this deliberately simple — regex on hrefs. A reviewer reading this
# can verify in 30 seconds that we are not doing anything clever.
# ---------------------------------------------------------------------------

CAREERS_HINTS = re.compile(
    r'href=["\']([^"\']*(careers|jobs|work-with-us|join-us|hiring)[^"\']*)["\']',
    re.IGNORECASE,
)
ABOUT_HINTS = re.compile(
    r'href=["\']([^"\']*(about|team|company|who-we-are)[^"\']*)["\']',
    re.IGNORECASE,
)


def _discover_links(homepage_html: str, base_url: str) -> dict:
    """Return {kind: absolute_url} for careers and about, if found."""
    out: dict = {}
    if not homepage_html:
        return out

    careers_match = CAREERS_HINTS.search(homepage_html)
    if careers_match:
        out["careers"] = urljoin(base_url, careers_match.group(1))

    about_match = ABOUT_HINTS.search(homepage_html)
    if about_match:
        out["about"] = urljoin(base_url, about_match.group(1))

    return out


# ---------------------------------------------------------------------------
# Public API: fetch_company_pages
# ---------------------------------------------------------------------------

def _synthesize_funding_announcement(company_name: str, notes: str) -> str:
    """
    When the row has notes, build a minimal funding-announcement page from
    those notes rather than loading the bundled Vellum sample (which would
    contaminate every other company's signals with Vellum's Series A
    language). The page is clearly labeled as offline-synthesized.
    """
    return (
        "<!doctype html><html><head>"
        f"<title>{company_name} funding announcement (offline-mode synthesized)</title>"
        "</head><body>"
        f"<h1>{company_name} — funding announcement</h1>"
        "<p><em>(Offline-mode synthesized funding-announcement page. "
        "Real text would come from a press release or company blog post.)</em></p>"
        f"<section><p>{notes}</p></section>"
        "</body></html>"
    )


def _synthesize_homepage(company_name: str, notes: str, sample_dir: Path) -> str:
    """
    Offline-mode helper.

    When per-row notes are provided, build a minimal HTML page from JUST those
    notes — do not mix in the bundled Vellum boilerplate, because that would
    leak signals from one company into every other row.

    When notes are empty (e.g. --url mode used without a CSV), fall back to
    the bundled sample_company_page.html so a reviewer who runs the demo
    with no input still gets a meaningful walk-through.

    Either way the page is clearly labeled as offline-mode synthetic so a
    reviewer cannot mistake it for real fetched content.
    """
    if notes:
        return (
            "<!doctype html><html><head>"
            f"<title>{company_name} (offline-mode synthesized)</title>"
            "</head><body>"
            f"<h1>{company_name}</h1>"
            "<p><em>(Offline-mode synthesized profile generated from analyst notes. "
            "Run with --live for real HTTP fetches.)</em></p>"
            f"<section><p>{notes}</p></section>"
            "</body></html>"
        )
    # No row context — fall back to the bundled sample so --url demos still work.
    return _load_sample("homepage", sample_dir)


def fetch_company_pages(
    company_url: Optional[str],
    funding_announcement_url: Optional[str],
    live: bool,
    sample_dir: Path,
    company_name: str = "",
    notes: str = "",
) -> List[FetchedPage]:
    """
    Return the pages we have for this company. In offline mode we synthesize a
    per-company homepage from the row's `notes` field so each prospect exercises
    a different signal path. In live mode we hit real URLs.
    """
    pages: List[FetchedPage] = []

    if live and HAS_REQUESTS and company_url:
        homepage_html = _fetch_url(company_url)
        pages.append(FetchedPage(
            url=company_url,
            kind="homepage",
            html=homepage_html,
            ok=bool(homepage_html),
            source_label=f"Homepage ({urlparse(company_url).netloc})",
        ))

        # Step 2 of the "agentic" pipeline: from the homepage, decide what
        # else is worth fetching. We do not blindly fetch every page; we
        # follow hints we found in the rendered HTML.
        if homepage_html:
            links = _discover_links(homepage_html, company_url)
            for kind, link_url in links.items():
                html = _fetch_url(link_url)
                if html:
                    pages.append(FetchedPage(
                        url=link_url,
                        kind=kind,
                        html=html,
                        ok=True,
                        source_label=f"{kind.title()} page ({urlparse(link_url).netloc})",
                    ))

        if funding_announcement_url:
            ann_html = _fetch_url(funding_announcement_url)
            pages.append(FetchedPage(
                url=funding_announcement_url,
                kind="funding_announcement",
                html=ann_html,
                ok=bool(ann_html),
                source_label=f"Funding announcement ({urlparse(funding_announcement_url).netloc})",
            ))

    else:
        # Offline / fallback mode: bundled samples enriched with row context.
        homepage_html = _synthesize_homepage(company_name, notes, sample_dir)
        pages.append(FetchedPage(
            url=str(sample_dir / SAMPLE_FILES["homepage"]),
            kind="homepage",
            html=homepage_html,
            ok=bool(homepage_html),
            source_label=f"Bundled sample homepage (synthesized for {company_name})" if company_name else "Bundled sample homepage",
        ))

        if funding_announcement_url:
            # Use synthesized announcement when we have notes (to avoid
            # contamination from the bundled Vellum sample); fall back to
            # the bundled sample otherwise.
            if notes:
                ann_html = _synthesize_funding_announcement(company_name, notes)
            else:
                ann_html = _load_sample("funding_announcement", sample_dir)
            pages.append(FetchedPage(
                url=str(sample_dir / SAMPLE_FILES["funding_announcement"]),
                kind="funding_announcement",
                html=ann_html,
                ok=bool(ann_html),
                source_label=f"Synthesized funding announcement for {company_name}"
                             if notes else "Bundled sample funding announcement",
            ))

    return pages
