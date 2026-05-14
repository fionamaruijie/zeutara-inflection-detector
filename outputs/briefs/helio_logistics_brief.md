# Diagnostic Brief — Helio Logistics

*Generated 2026-05-13 — Zeutara Inflection Detector — extraction mode: `rule_based`*

- **Inflection score:** 5 / 100
- **Confidence:** 42 / 100
- **Disqualifier penalty applied:** -45
- **Route:** `disqualified`
- **Primary structural constraint:** `enterprise_motion_emerging`
- **Source confidence:** low
- **Company URL:** https://example-helio.com

## Why this company, now

Helio Logistics is signalling movement up-market into enterprise. Every revenue process — pricing, pipeline, deal review, forecasting — needs to be rebuilt for the new motion, and the cost of doing it after the first lost deal is high. Stage is consistent with Zeutara's sweet spot (series a).

### Evidence

- **b2b_revenue_motion** (medium): "from analyst notes. Run with --live for real HTTP fetches.) B2B logistics platform. Closed Series A 4 months ago. Strong en"
  - Source: sample_inputs/sample_company_page.html
- **hiring_operations_role** (medium): "enterprise customer base. Recently announced our fractional COO Sarah Kim has joined to scale operations. Team of 60."
  - Source: sample_inputs/sample_company_page.html
- **enterprise_expansion_signal** (medium): "2B logistics platform. Closed Series A 4 months ago. Strong enterprise customer base. Recently announced our fractional COO Sarah"
  - Source: sample_inputs/sample_company_page.html
- **operating_partner_already_engaged** (medium): "go. Strong enterprise customer base. Recently announced our fractional COO Sarah Kim has joined to scale operations. Team of 60."
  - Source: sample_inputs/sample_company_page.html

### Reason codes (audit trail)

- `stage_fit: estimated stage = series_a`
- `b2b_revenue_motion_detected`
- `headcount_in_band: ~60`
- `hiring_operations_role_signal`
- `enterprise_expansion_signal`
- `disqualifier_SEVERE: operating_partner_already_engaged (-45)`

## Suggested buyer path

Do not pursue. Reason codes above explain the disqualifier.

## Recommended outreach angle

> (no outreach — severe disqualifier present)

## Discovery-call questions

- (No outreach scheduled — see route.)

## Human review checkpoint

Before this brief is forwarded or used in outreach, the assigned analyst must complete the following:

- [ ] Verify the funding date and round size against an independent source (Crunchbase, PitchBook, or the announcement itself).
- [ ] Confirm the founder is still the operating owner of GTM (LinkedIn role descriptions, recent founder posts).
- [ ] Check whether any of the disqualifier signals were missed — fractional COO/CRO recently announced, VC platform team engaged, competitor advisory firm visible.
- [ ] Confirm there is no active fundraise underway (founder distraction). LinkedIn fundraising posts, recent press, calendar of investor demo days.
- [ ] If routing as warm_intro_candidate, confirm a real investor relationship path exists before forwarding.

---

*This brief is a routing recommendation, not a sales pitch. The system is designed to fail toward `watchlist` and `disqualified` before forwarding low-confidence accounts into senior attention.*