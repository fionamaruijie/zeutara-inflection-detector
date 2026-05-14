"""
exporter.py
===========
Writes scored CompanyRecord objects to disk.

  - scored_companies.csv  : flat one-row-per-company table the analyst opens
                            in a spreadsheet or pushes to Airtable/HubSpot.
  - scored_companies.json : full nested objects for downstream tooling.

Markdown briefs are written by brief_generator.py, one file per company under
outputs/briefs/. The CSV references the brief path so the analyst can jump
straight from a row to the supporting artifact.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import List

from schema import CompanyRecord


CSV_COLUMNS = [
    "company_name",
    "company_url",
    "estimated_stage",
    "sector",
    "headcount_estimate",
    "inflection_score",
    "confidence_score",
    "disqualifier_penalty",
    "route",
    "primary_structural_constraint",
    "suggested_buyer_path",
    "recommended_outreach_angle",
    "reason_codes",
    "sources_used",
    "source_confidence",
    "extraction_mode",
    "brief_path",
]


def export_csv(records: List[CompanyRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        for r in records:
            writer.writerow(r.to_flat_row())


def export_json(records: List[CompanyRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump([r.to_dict() for r in records], f, indent=2)
