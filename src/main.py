"""
main.py
=======
CLI entry point for the Zeutara Inflection Detector.

Reads either:
  - a CSV of companies (--input)
  - or a single funding announcement URL (--url)

For each company, runs the pipeline:

    fetch pages  ->  extract signals  ->  score  ->  route  ->  brief  ->  export

Default mode:    rule-based extraction, offline sample files. Zero setup.
--live mode:     live HTTP fetches + Claude extraction if ANTHROPIC_API_KEY set.

The orchestrator is intentionally thin. Each stage is a function with one
job. That makes the system extensible: a Day-2 task could swap the fetcher
for a Clay / Apollo enrichment hop, or swap the rule-based scorer for a
learned one calibrated on closed-won data, without touching anything else.

Usage:

    # Default (offline, runs in 15 sec on any laptop):
    python src/main.py --input sample_inputs/companies.csv --output outputs/

    # Live (fetches real pages; uses Claude if ANTHROPIC_API_KEY is set):
    python src/main.py --input sample_inputs/companies.csv --output outputs/ --live

    # Single-URL mode:
    python src/main.py --url "https://example.com/funding-announcement" \\
        --company-name "Example Co" --output outputs/ --live
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import List, Optional

# Make `src/` imports work whether you run from repo root or from inside src/.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from schema import CompanyRecord
from fetcher import fetch_company_pages
from extractor import extract
from scorer import score_signals
from router import route
from brief_generator import write_brief
from exporter import export_csv, export_json


# ---------------------------------------------------------------------------
# Input loading
# ---------------------------------------------------------------------------

def load_companies_from_csv(path: Path) -> List[CompanyRecord]:
    records: List[CompanyRecord] = []
    with path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = (row.get("company_name") or "").strip()
            if not name:
                continue
            records.append(CompanyRecord(
                company_name=name,
                company_url=(row.get("company_url") or "").strip() or None,
                funding_announcement_url=(row.get("funding_announcement_url") or "").strip() or None,
                notes=(row.get("notes") or "").strip() or None,
            ))
    return records


# ---------------------------------------------------------------------------
# Pipeline (per company)
# ---------------------------------------------------------------------------

def process_company(
    record: CompanyRecord,
    live: bool,
    mode: str,
    sample_dir: Path,
    briefs_dir: Path,
) -> CompanyRecord:
    """
    Run the full pipeline for a single company. Each stage is a function call,
    not a method on a god-object — that is the difference between this and
    a static scorer, and it is what makes the pipeline extensible.
    """
    # Stage 1 — fetch
    pages = fetch_company_pages(
        company_url=record.company_url,
        funding_announcement_url=record.funding_announcement_url,
        live=live,
        sample_dir=sample_dir,
        company_name=record.company_name,
        notes=record.notes or "",
    )

    # Stage 2 — extract (rule-based by default, Claude live if --live + key)
    signals, evidence, extraction_mode = extract(
        pages=pages,
        company_name=record.company_name,
        mode=mode,
    )
    record.signals = signals
    record.evidence = evidence
    record.extraction_mode = extraction_mode

    # Stage 3 — score
    score, conf, penalty, reasons = score_signals(signals, evidence)
    record.inflection_score = score
    record.confidence_score = conf
    record.disqualifier_penalty = penalty
    record.reason_codes = reasons

    # Stage 4 — route
    route_label, constraint, buyer_path, dq, angle = route(signals, score, conf)
    record.route = route_label
    record.primary_structural_constraint = constraint
    record.suggested_buyer_path = buyer_path
    record.discovery_questions = dq
    record.recommended_outreach_angle = angle

    # Stage 5 — brief
    brief_path = write_brief(record, evidence, briefs_dir)
    # Store relative to repo root for readability in the CSV.
    try:
        record.brief_path = str(brief_path.relative_to(briefs_dir.parent.parent))
    except ValueError:
        record.brief_path = str(brief_path)

    return record


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Zeutara Inflection Detector — turn messy public signals about a "
                    "company into a routed BD decision and a diagnostic brief.",
    )
    parser.add_argument("--input", type=Path,
                        help="CSV of companies with company_name, company_url, "
                             "funding_announcement_url, notes")
    parser.add_argument("--url", type=str,
                        help="A single funding-announcement URL to analyze "
                             "(use --company-name to label the output).")
    parser.add_argument("--company-name", type=str, default="Single URL Target",
                        help="Display name when using --url.")
    parser.add_argument("--output", type=Path, default=Path("outputs"),
                        help="Output directory (default: outputs/)")
    parser.add_argument("--live", action="store_true",
                        help="Hit live HTTP and use Claude for extraction if "
                             "ANTHROPIC_API_KEY is set. Default is offline.")
    parser.add_argument("--sample-dir", type=Path, default=Path("sample_inputs"),
                        help="Where the bundled offline samples live.")
    args = parser.parse_args(argv)

    if not args.input and not args.url:
        parser.error("Provide either --input <csv> or --url <funding-announcement-url>.")

    # Resolve paths
    output_dir: Path = args.output
    briefs_dir = output_dir / "briefs"
    briefs_dir.mkdir(parents=True, exist_ok=True)

    sample_dir: Path = args.sample_dir
    if not sample_dir.exists():
        # Helpful failure for reviewers running from inside src/
        candidate = Path(__file__).resolve().parent.parent / "sample_inputs"
        if candidate.exists():
            sample_dir = candidate

    extraction_mode = "claude_live" if args.live else "rule_based"

    # Build records
    if args.input:
        records = load_companies_from_csv(args.input)
    else:
        records = [CompanyRecord(
            company_name=args.company_name,
            funding_announcement_url=args.url,
        )]

    if not records:
        print("No companies to process. Exiting.")
        return 1

    print(f"Running Zeutara Inflection Detector on {len(records)} companies "
          f"(mode={extraction_mode}, live={args.live}).")
    print(f"  sample_dir = {sample_dir}")
    print(f"  output_dir = {output_dir}")
    print()

    for i, rec in enumerate(records, 1):
        print(f"[{i}/{len(records)}] {rec.company_name} ...")
        process_company(
            record=rec,
            live=args.live,
            mode=extraction_mode,
            sample_dir=sample_dir,
            briefs_dir=briefs_dir,
        )
        print(f"   score={rec.inflection_score}  conf={rec.confidence_score}  "
              f"route={rec.route}  constraint={rec.primary_structural_constraint}")

    # Export
    csv_path = output_dir / "scored_companies.csv"
    json_path = output_dir / "scored_companies.json"
    export_csv(records, csv_path)
    export_json(records, json_path)

    print()
    print(f"Done. Outputs:")
    print(f"  {csv_path}")
    print(f"  {json_path}")
    print(f"  {briefs_dir}/ ({len(records)} briefs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
