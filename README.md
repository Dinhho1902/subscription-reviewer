# Subscription Reviewer

An AI review layer for offline private-fund subscription booklets: Claude reads the PDF, code checks
the result against fund rules, and a reviewer handles only the exceptions. Why it is worth building:
see [MEMO.md](MEMO.md).

All funds, investors and documents in this repo are synthetic.


## What it does
1. **Extract:** Claude Opus 5.5 reads the booklet and returns typed fields (investor, type, commitment
   in figures and in words, US person, accreditation basis, tax form, signature), each with a page
   number and a verbatim quote.
2. **Ground:** every quote is matched against the PDF text. Unmatched or uncertain fields are marked
   *Check* for the reviewer.
3. **Check:** plain-code rules raise flags: missing signature, amount mismatch, below minimum,
   no accreditation, wrong tax form, missing signatory title.
4. **Review:** the reviewer corrects fields (checks re-run), then approves or returns the packet.
   Approve is disabled while a critical issue remains. Decisions and corrections go to `decisions.jsonl`.

Why it is built this way: see [MEMO.md](MEMO.md).

## Run it
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
export ANTHROPIC_API_KEY=...            # needed for live reviews and evals
.venv/bin/python -m data.generate       # rebuild the 20 synthetic booklets (already committed)
.venv/bin/python -m evals.run_evals     # score all 20 packets, writes evals/results/latest.md
.venv/bin/streamlit run app.py
```
The eval run also fills `cache/`, so the app can show every sample packet without new API calls.

## Evals
| Metric | Why it matters |
|---|---|
| Critical-flag recall | A missed defect means a bad subscription is accepted. Ship gate: 100%. |
| Field accuracy | Reviewers stop trusting pre-filled fields fast. Ship gate: 95%. |
| Flag precision | False alarms cost reviewer time. |
| Grounding rate | Share of fields backed by a quote found on the page. |
| Cost and latency per packet | Must stay well below the cost of a manual review. |

Settings: `REVIEWER_MODEL` (default `claude-opus-5-5`), `REVIEWER_EFFORT` (default `medium`),
`REVIEWER_BACKEND` (`api`, the default, or `claude-code` to run the same prompt and schema through the
Claude Code CLI on a Claude subscription, no API key needed).

Results so far: `evals/results/v1-baseline.md` and `evals/results/v2-na-fields.md`.
Requests use server-side refusal fallback (`fallbacks: "default"`); a refused packet goes to manual review.

## Layout
```
app.py                 Streamlit review screen
reviewer/extract.py    Claude call, structured output, grounding
reviewer/rules.py      deterministic checks
reviewer/fund_terms.py fund minimum and tax-form rules
reviewer/cache.py      result cache keyed by file hash
data/generate.py       synthetic booklets + ground truth
evals/run_evals.py     scoring and ship gate
```
