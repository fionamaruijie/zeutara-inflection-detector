# Diagnostic Brief — Mavros Health

*Generated 2026-05-13 — Zeutara Inflection Detector — extraction mode: `rule_based`*

- **Inflection score:** 60 / 100
- **Confidence:** 66 / 100
- **Disqualifier penalty applied:** -15
- **Route:** `direct_outreach_candidate`
- **Primary structural constraint:** `gtm_leader_transition`
- **Source confidence:** medium
- **Company URL:** https://example-mavros.com
- **Funding announcement:** https://example-press.com/mavros-seed

## Why this company, now

Mavros Health appears to be hiring its first dedicated GTM leader. This is the moment Zeutara's product is most valuable — the operating architecture the new hire inherits in the first 90 days determines whether they succeed or churn. Stage is consistent with Zeutara's sweet spot (seed).

### Evidence

- **b2b_revenue_motion** (medium): "from analyst notes. Run with --live for real HTTP fetches.) B2B healthtech SaaS. Seed-stage with $4M raised from Andreessen"
  - Source: sample_inputs/sample_company_page.html
- **recent_funding** (medium): "or real HTTP fetches.) B2B healthtech SaaS. Seed-stage with $4M raised from Andreessen Horowitz (a16z) and Founders Fund. Hiring f"
  - Source: sample_inputs/sample_company_page.html
- **hiring_first_gtm_leader** (medium): "Andreessen Horowitz (a16z) and Founders Fund. Hiring first head of sales. Team of 18. Founder-led sales motion. Mavros Health fundi"
  - Source: sample_inputs/sample_company_page.html
- **founder_led_sales_signal** (medium): "and Founders Fund. Hiring first head of sales. Team of 18. Founder-led sales motion. Mavros Health funding announcement (offline-mode s"
  - Source: sample_inputs/sample_company_page.html
- **investor_has_platform_team** (high): "Company is backed by 'founders fund', which runs an in-house operating/platform team."
  - Source: sample_inputs/sample_company_page.html

### Reason codes (audit trail)

- `stage_fit: estimated stage = seed`
- `b2b_revenue_motion_detected`
- `headcount_in_band: ~18`
- `recent_funding_signal`
- `hiring_first_gtm_leader_signal (strong)`
- `founder_led_sales_signal`
- `disqualifier_soft: investor_has_platform_team (-15)`

## Suggested buyer path

Direct founder brief — to founder/CEO, with co-founder cc'd if visible.

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