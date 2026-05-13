# Zeutara Inflection Detector

**The load-bearing component of Zeutara's BD architecture: an agentic signal
pipeline that turns messy public information about a company into a routed
BD decision — `warm_intro_candidate`, `direct_outreach_candidate`,
`watchlist`, or `disqualified` — plus a forwardable diagnostic brief.**

This is the prototype for the analyst screening assignment. The full
architecture and defending paper sit alongside it; this repo implements only
the load-bearing layer.

---

## Why this is the load-bearing component

Zeutara sells **execution architecture**, not lead generation. The BD
constraint is therefore not outbound volume — it is **the cost of producing
a forwardable, partner-quality diagnostic brief at scale without burning
investor and founder trust**.

The Inflection Detector is the layer that earns its keep:

- **Extraction is the AI-leverage point.** Turning a homepage, careers page
  and funding announcement into a structured signal set is where Claude adds
  ten-times leverage over a human analyst.
- **Routing is the trust-preservation point.** A static ICP scorer pushes
  every "high score" account to the partner. This system fails *toward*
  `watchlist` and `disqualified` when confidence is low, so partner attention
  is only spent on accounts a partner would actually be glad to see.
- **Scoring is just an output.** It's deterministic on purpose — every score
  is auditable from the reason codes in the brief.

Email generation, CRM enrichment and sequencing are downstream of this layer.
They are not in this repo because they are not where the architecture is
load-bearing.

---

## Run it (15 minutes, no API key required)

```bash
# 1. clone, cd in, install deps (defaults are minimal)
pip install -r requirements.txt

# 2. run the default offline demo on six sample companies
python src/main.py --input sample_inputs/companies.csv --output outputs/

# 3. inspect outputs
cat outputs/scored_companies.csv
ls outputs/briefs/
cat outputs/briefs/vellum_brief.md   # the showcase warm-intro brief
```

Expected output:

```
[1/6] Vellum ...           score=80  conf=66  route=warm_intro_candidate
[2/6] Northbeam Cloud ...  score=78  conf=48  route=watchlist
[3/6] LocalBites Cafe ...  score=0   conf=30  route=disqualified
[4/6] QuietPaths AI ...    score=0   conf=24  route=disqualified
[5/6] Helio Logistics ...  score=5   conf=42  route=disqualified
[6/6] Mavros Health ...    score=60  conf=66  route=direct_outreach_candidate
```

All four route buckets are represented with real (synthetic) cases. The
Northbeam case is intentional: a high-scoring account with only one source
of evidence routes to `watchlist`, not `direct_outreach`. That is the
"fail-toward-caution" behavior described in the architecture.

### Live mode (optional, with a Claude API key)

```bash
cp .env.example .env
# add ANTHROPIC_API_KEY=sk-ant-... to .env, then:
pip install anthropic                                  # optional dep
export ANTHROPIC_API_KEY=$(grep ANTHROPIC_API_KEY .env | cut -d= -f2)
python src/main.py --input sample_inputs/companies.csv --output outputs/ --live
```

In live mode:
- the fetcher hits real URLs (homepage, careers page discovered via link
  patterns, funding announcement)
- the extractor sends the cleaned text to Claude with a strict JSON schema
  and parses the structured response into the same `Signals` object the
  rule-based path produces
- scoring and routing are unchanged — that's a deliberate design choice
  (auditable scoring, AI-augmented extraction)

If `ANTHROPIC_API_KEY` is not set, `--live` still does live HTTP fetches
but degrades extraction to the rule-based path. The reviewer always gets
output.

### Single-URL mode

For testing against a single funding announcement:

```bash
python src/main.py \
    --url "https://example.com/funding-announcement" \
    --company-name "Example Co" \
    --output outputs/ \
    --live
```

---

## What's inside

```
zeutara-inflection-detector/
├─ README.md                       this file
├─ requirements.txt                minimal deps (requests, bs4)
├─ .env.example                    optional ANTHROPIC_API_KEY
├─ src/
│   ├─ main.py                     CLI orchestrator (the pipeline)
│   ├─ fetcher.py                  URL fetch + offline-sample fallback
│   ├─ extractor.py                rule-based + Claude-live extraction
│   ├─ schema.py                   Signals / Evidence / CompanyRecord
│   ├─ scorer.py                   deterministic 0-100 inflection score
│   ├─ router.py                   the four-bucket decision
│   ├─ brief_generator.py          Markdown diagnostic brief
│   ├─ exporter.py                 CSV + JSON output
│   └─ config.py                   weights, thresholds, disqualifier lists
├─ sample_inputs/
│   ├─ companies.csv               six demo prospects spanning all routes
│   ├─ sample_company_page.html    bundled offline homepage
│   └─ sample_funding_announcement.html
├─ outputs/
│   ├─ scored_companies.csv        flat one-row-per-company
│   ├─ scored_companies.json       nested objects
│   └─ briefs/                     one Markdown brief per company
└─ tests/
    ├─ test_scorer.py              scoring math invariants
    └─ test_router.py              route bucket logic
```

Run the tests with:

```bash
python tests/test_scorer.py && python tests/test_router.py
```

---

## How the pipeline works, in one paragraph

For each company in the input CSV: **(1)** the fetcher pulls the homepage,
discovers and follows links to the careers and about pages, and pulls the
funding announcement if one was supplied; **(2)** the extractor reads the
cleaned text and populates a strict `Signals` object — in `rule_based` mode
via regex patterns, in `claude_live` mode via a JSON-schema prompt to Claude;
**(3)** the scorer applies the weights in `config.py` to produce a 0-100
inflection score, a 0-100 confidence score, and a list of reason codes;
**(4)** the router maps `(score, confidence, disqualifiers)` to one of four
buckets, choosing the *primary structural constraint* that will lead the
brief; **(5)** the brief generator writes a Markdown file with the routing
decision, evidence trail, reason codes, recommended outreach angle and
discovery-call questions, plus a human-review checkpoint that any analyst
must complete before the brief is forwarded.

The full pipeline runs in seconds on a laptop. Every stage is one function
in one small file. That's the point — this prototype is meant to be cloned,
read in fifteen minutes, and stress-tested by a partner who wants to ask
"why did this account score 80?"

---

## Key design decisions

**Extraction is AI-leveraged, scoring is deterministic.** Even in `--live`
mode, Claude produces structured `Signals`, not scores. The score is
recomputed in `scorer.py` from weights in `config.py` so a partner can
look at any brief and reconstruct the math from the reason codes. AI is
allowed to read messy text; AI is *not* allowed to decide who Zeutara
spends partner-hours on.

**The system fails toward `watchlist`, not toward `partner forward`.** A
high-scoring account with only one source of evidence drops to `watchlist`
by design. This is the protection against the 5x-volume failure mode: under
load, the most expensive failure is sending a low-confidence
"high-scoring" account to a partner and damaging investor or founder trust.
The thresholds in `config.py` make this explicit.

**Disqualifier logic is partner-grade, not template-grade.** Severe
disqualifiers — `mature_revops_in_place`, `operating_partner_already_engaged`,
`local_smb_only`, `no_b2b_revenue_motion`, `competitor_advisory_engaged` —
short-circuit even a 95-score account to `disqualified`. The list of VCs
with strong internal platform teams (a16z, Sequoia, Founders Fund, USV, etc.)
applies a softer −15 penalty that pulls accounts out of `warm_intro` but
leaves them eligible for `direct_outreach` if the rest of the signal set
is strong.

**Briefs are forwardable, not pitchy.** The diagnostic brief is written in
the tone an investor partner would actually forward to a founder. It opens
with the structural constraint and the evidence trail, includes a human
review checkpoint, and never recommends an outreach angle when the route
is `watchlist` or `disqualified`.

---

## What this prototype is NOT

To stay honest about what the reviewer is looking at:

- **Not an email sender.** No SMTP, no template engine, no sequencing.
  Email is downstream of routing and is intentionally out of scope.
- **Not a CRM.** The exporter writes CSV and JSON; how those flow into
  HubSpot or Attio is a wiring concern for the full architecture, not
  the load-bearing layer.
- **Not a substitute for the analyst's judgment.** Every brief includes
  a human-review checkpoint with five required verifications before it
  can be forwarded or used for outreach.
- **Not a finished product.** Rule-based extraction handles the
  high-signal cases; live mode handles the long tail. Neither replaces
  the structured analyst review the brief is designed to support.

---

## If I had two more days

Honest priorities, in order:

1. **Plug in a real funding-data source** (Crunchbase API or a free
   alternative like the SEC Form D feed for US-domiciled C-corps) and
   replace the synthesized offline sample with weekly real input. The
   prototype currently treats the input CSV as the universe; production
   needs ingestion that produces that CSV every Monday.

2. **Add LinkedIn-derived founder and investor signals.** Founder-led
   sales, technical-only founder, and recent C-suite hires are best read
   from LinkedIn role descriptions, not company homepages. A second
   extractor module reading sanitized LinkedIn export data would
   meaningfully tighten the founder-level disqualifier branch.

3. **Calibrate weights on closed-won / closed-lost data.** Right now the
   weights in `config.py` reflect a thesis. A 90-day calibration cycle
   (the feedback loop described in the architecture) should regress
   actual closed-won outcomes against feature contributions and adjust.
   Until then the system is a defensible prior, not a learned one.

4. **Build the investor-relationship graph.** The current `warm_intro_candidate`
   route assumes a human knows whether a partner relationship exists with
   the lead investor on the deal. A small graph (lead investor → known
   relationship at Zeutara → strength) would let the router actually
   *verify* a warm-intro path instead of just recommending one.

5. **Tighten the `claude_live` extractor with explicit tool use.** Today it
   sends the cleaned page text and asks for JSON. A stronger version would
   give Claude a `fetch_url(url)` tool and let it decide whether to pull a
   second source (e.g. the founder's LinkedIn or a recent press piece)
   before committing to a signal value. This is the path to a more fully
   "agentic" version.

6. **Add inflection-window decay.** Right now any recent funding counts as
   "recent." In reality the inflection window opens at the round and starts
   closing around 6–9 months later, faster if the company has hired a head
   of sales in the meantime. The `signals.funding_age_months` field is in
   the schema but isn't yet wired into scoring.

---

## License & contact

Built as a screening artifact for Zeutara. Prepared by Ruijie Ma.
