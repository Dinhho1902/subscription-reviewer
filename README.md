# Subscription Reviewer

An AI pre-check that tells a fund administrator, in seconds, whether a subscription booklet sent as a PDF
is in good order, shows the evidence behind every problem, and sends only the booklets with a problem to
a reviewer.

**Live demo:** https://subscription-reviewer.streamlit.app (start with "Try the product", or follow the
six-step story). The public demo shows the AI's saved results from the test run; live AI calls and uploads
are switched off.

**Why it is worth building:** [MEMO.md](MEMO.md) (the product case, with sources).

All funds, investors and booklets in this repo are invented.

## The demo
Six steps, each with a PM note and a button to the next one. Every step has its own link
(`?step=problem|queue|review|trust|impact|next`, plus `&booklet=SUB-018` for step 3).

1. **The problem:** the closing-week scenario, three sourced figures, who has the problem.
2. **The review queue:** the same 20 booklets with and without the AI pre-check; a diagram shows them
   sorted into 9 in good order and 11 sent to the reviewer.
3. **Inside one booklet** (the working product): a replayable timeline of the check, the PDF page with the
   evidence highlighted, a zoomed image and a side-by-side card for each problem, Approve (blocked while a
   serious error remains), Return to investor with a draft message, an audit trail, editable values, and
   "Simulate the investor's correction".
4. **How accurate is it?** The go-live test and the results below.
5. **What does it save?** A reviewer-time calculator. Only the AI's speed and cost are measured; the other
   inputs are assumptions.
6. **Fit and next steps.**

Visual direction follows the ui-ux-pro-max guidance for document-workflow products: Swiss minimal,
accessible, trust navy with status colors that always carry a text label, Inter, Material icons, 44px
controls, responsive down to phone width.

## How it works
1. **The AI reads:** Claude Opus 5.5 reads the PDF and returns 12 typed values (investor, investor type,
   commitment in figures and in words, U.S. person, accredited-investor basis, tax form, signature,
   signer, title, date), each with the page number and a verbatim quote.
2. **Evidence check:** code looks for every quote on the page it cites. A value without a matching quote,
   or one the AI marked as unsure, is sent to the reviewer.
3. **Fixed rules decide:** plain-code rules flag serious errors (not signed, amount in words and figures
   differ, below the minimum commitment, no accredited-investor box ticked, wrong tax form) and minor ones
   (signer's title missing). The AI never decides pass or fail.
4. **A person approves:** the reviewer can correct values (the rules run again), then approve or return
   the booklet. Decisions and corrections are logged to `decisions.jsonl` and become new test cases.

## Run it
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run app.py          # demo mode: uses the saved results in cache/
```

To run the AI yourself, either set an API key or use the Claude Code CLI on a Claude subscription
(this is how the committed results were produced):
```bash
export ANTHROPIC_API_KEY=...                                    # option 1: Anthropic API
export REVIEWER_BACKEND=claude-code                             # option 2: Claude Code CLI, no API key
.venv/bin/python -m evals.run_evals                             # test all 20 booklets
.venv/bin/python -m evals.run_evals SUB-018                     # test one booklet
.venv/bin/python -m data.generate                               # rebuild the 20 booklets (already committed)
```
A test run also refreshes `cache/`, so the demo shows the new results without further AI calls. With
either option set, the demo turns off demo mode and step 3 gets a "Run the AI again now" button.

Settings: `REVIEWER_MODEL` (default `claude-opus-5-5`), `REVIEWER_EFFORT` (default `medium`),
`REVIEWER_BACKEND` (`api`, the default, or `claude-code`). API requests use server-side refusal fallback
(`fallbacks: "default"`); a booklet the model declines goes to manual review.

## Tests and results
The go-live test was set before testing: the pre-check may clear booklets without a reviewer only if it
finds every serious error and reads at least 95% of values correctly. In the code and the result files
this is the "ship gate", serious errors are "critical flags", and the evidence check is "grounding".

| Measure (name in the result files) | Version 1 | Version 2 |
|---|---|---|
| Serious errors found (critical-flag recall) | 12 of 12 | 12 of 12 |
| Values read correctly (field accuracy) | 100% | 100% |
| Problems flagged that were real (flag precision) | 100% | 100% |
| Values backed by a quote found on the page (grounding rate) | 100% | 100% |
| Good booklets cleared without a reviewer (clean auto-cleared) | 7 of 9 | 9 of 9 |
| AI reading time per booklet | 11.3 s | 11.5 s |
| AI cost per booklet (list-price estimate) | $0.09 | $0.09 |

Version 2 added one sentence to the AI's instructions so that fields that do not apply are no longer
marked "unsure". Full results: `evals/results/v1-baseline.md` and `evals/results/v2-na-fields.md`.
Twenty clean, typed booklets are an easy test; see MEMO.md section 6 for what it does not cover.

## Layout
```
app.py                  six-step demo around the working review screen
.streamlit/config.toml  light theme and colors
reviewer/extract.py     the AI call (API or Claude Code), structured output, evidence check
reviewer/rules.py       fixed rules that decide serious and minor errors
reviewer/fund_terms.py  fund minimum and tax-form rules
reviewer/highlight.py   highlights evidence on the PDF page and crops the zoomed images
reviewer/cache.py       saved results, keyed by file hash
data/generate.py        the 20 invented booklets and their known answers
data/packets/           the booklets (PDF)
evals/run_evals.py      the test harness and go-live test
evals/results/          test results (v1, v2, latest)
cache/                  saved AI results used by the public demo
MEMO.md                 the product case
```
