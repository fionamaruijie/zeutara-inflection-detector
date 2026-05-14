# Diagnostic Brief — Vellum

*Generated 2026-05-13 — Zeutara Inflection Detector — extraction mode: `rule_based`*

- **Inflection score:** 80 / 100
- **Confidence:** 66 / 100
- **Disqualifier penalty applied:** 0
- **Route:** `warm_intro_candidate`
- **Primary structural constraint:** `gtm_leader_transition`
- **Source confidence:** medium
- **Company URL:** https://example-vellum.com
- **Funding announcement:** https://example-press.com/vellum-series-a

## Why this company, now

Vellum appears to be hiring its first dedicated GTM leader. This is the moment Zeutara's product is most valuable — the operating architecture the new hire inherits in the first 90 days determines whether they succeed or churn. Stage is consistent with Zeutara's sweet spot (series a).

### Evidence

- **b2b_revenue_motion** (medium): "from analyst notes. Run with --live for real HTTP fetches.) B2B SaaS revenue operating platform. Closed Series A round of $"
  - Source: sample_inputs/sample_company_page.html
- **hiring_first_gtm_leader** (medium): ". Closed Series A round of $14M in March 2026. Hiring first Head of Sales and a Head of Revenue Operations. Team of 38 people. Founde"
  - Source: sample_inputs/sample_company_page.html
- **hiring_operations_role** (medium): "und of $14M in March 2026. Hiring first Head of Sales and a Head of Revenue Operations. Team of 38 people. Founder Maya Park still owns enterprise"
  - Source: sample_inputs/sample_company_page.html
- **enterprise_expansion_signal** (medium): "Operations. Team of 38 people. Founder Maya Park still owns enterprise sales. Moving up-market into mid-market and Fortune 1000 lo"
  - Source: sample_inputs/sample_company_page.html
- **recent_funding** (high): "Funding announcement provided as input."
  - Source: (funding announcement page)

### Reason codes (audit trail)

- `stage_fit: estimated stage = series_a`
- `b2b_revenue_motion_detected`
- `headcount_in_band: ~38`
- `recent_funding_signal`
- `hiring_first_gtm_leader_signal (strong)`
- `hiring_operations_role_signal`
- `enterprise_expansion_signal`

## Suggested buyer path

Forwardable investor brief — to lead investor partner, who introduces to founder/CEO.

## Recommended outreach angle

> The first head of sales fails 60%+ of the time. The deciding variable is the operating architecture they inherit on day one, not the hire.

## Discovery-call questions

- How are you measuring the first 90 days of the new GTM hire?
- What does the pipeline review cadence look like once the hire starts?
- What is the agreed split of accountability between you and them?

## Human review checkpoint

Before this brief is forwarded or used in outreach, the assigned analyst must complete the following:

- [ ] Verify the funding date and round size against an independent source (Crunchbase, PitchBook, or the announcement itself).
- [ ] Confirm the founder is still the operating owner of GTM (LinkedIn role descriptions, recent founder posts).
- [ ] Check whether any of the disqualifier signals were missed — fractional COO/CRO recently announced, VC platform team engaged, competitor advisory firm visible.
- [ ] Confirm there is no active fundraise underway (founder distraction). LinkedIn fundraising posts, recent press, calendar of investor demo days.
- [ ] If routing as warm_intro_candidate, confirm a real investor relationship path exists before forwarding.

---

*This brief is a routing recommendation, not a sales pitch. The system is designed to fail toward `watchlist` and `disqualified` before forwarding low-confidence accounts into senior attention.*