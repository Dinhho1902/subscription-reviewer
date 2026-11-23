"""Run the reviewer on every synthetic packet and score it against ground truth.

Metrics
- Field accuracy: share of fields extracted exactly right (names compared case-insensitively).
- Critical-flag recall: of the critical defects planted, how many the pipeline caught.
  This is the ship gate: a missed defect means a bad subscription gets accepted.
- Flag precision: of the flags raised, how many were real (false alarms cost reviewer time).
- Grounding rate: share of filled fields backed by a quote found on the cited page.
- Cost and latency per packet.

Run:  python -m evals.run_evals            (all 20 packets, real API calls, ~US$1-2)
      python -m evals.run_evals SUB-011    (one packet)
"""

import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import anthropic

from reviewer import cache
from reviewer.extract import BACKEND, EFFORT, FIELD_NAMES, MODEL, extract
from reviewer.rules import CRITICAL, check

ROOT = Path(__file__).resolve().parent.parent
PACKETS = ROOT / "data" / "packets"
TRUTH = json.loads((ROOT / "data" / "ground_truth.json").read_text())
RESULTS = ROOT / "evals" / "results"

# Ship gate, decided before looking at results.
GATE_CRITICAL_RECALL = 1.0
GATE_FIELD_ACCURACY = 0.95

SCORED_FIELDS = [f for f in FIELD_NAMES if f != "commitment_amount_words"]
CRITICAL_CODES = {"MISSING_SIGNATURE", "AMOUNT_MISMATCH", "BELOW_MINIMUM",
                  "NO_ACCREDITATION", "TAX_FORM_MISMATCH"}


def same(field: str, got, want) -> bool:
    if isinstance(want, str) and isinstance(got, str):
        return got.strip().lower() == want.strip().lower()
    if isinstance(want, float) and isinstance(got, (int, float)):
        return abs(got - want) < 0.5
    return got == want


def score_one(packet_id: str, client: anthropic.Anthropic) -> dict:
    truth = TRUTH[packet_id]
    pdf = PACKETS / f"{packet_id}.pdf"
    try:
        r = extract(pdf, client)  # always a fresh call: evals measure the live model
    except Exception as e:  # keep the run going; record the failure
        return {"id": packet_id, "error": f"{type(e).__name__}: {e}"}
    cache.save(cache.file_hash(pdf.read_bytes()), r)  # lets the demo app reuse this result
    flags = sorted(f.code for f in check(r.fields))
    field_hits = {f: same(f, r.fields.get(f), truth["fields"][f]) for f in SCORED_FIELDS}
    filled = [f for f in FIELD_NAMES if r.fields.get(f) not in (None, False)]
    return {
        "id": packet_id,
        "fields": r.fields,
        "field_hits": field_hits,
        "wrong_fields": {f: {"got": r.fields.get(f), "want": truth["fields"][f]}
                         for f, ok in field_hits.items() if not ok},
        "flags": flags,
        "expected_flags": truth["flags"],
        "needs_review": r.needs_review,
        "grounded": sum(1 for f in filled if r.grounded.get(f)),
        "filled": len(filled),
        "cost_usd": r.cost_usd,
        "latency_s": r.latency_s,
        "model": r.model,
    }


def summarize(rows: list[dict]) -> dict:
    ok = [r for r in rows if "error" not in r]
    hits = [h for r in ok for h in r["field_hits"].values()]
    planted = [(r["id"], c) for r in ok for c in r["expected_flags"] if c in CRITICAL_CODES]
    caught = [(i, c) for i, c in planted if c in next(r for r in ok if r["id"] == i)["flags"]]
    raised = [(r["id"], c) for r in ok for c in r["flags"]]
    true_raised = [(i, c) for i, c in raised
                   if c in next(r for r in ok if r["id"] == i)["expected_flags"]]
    s = {
        "model": MODEL, "backend": BACKEND, "effort": EFFORT, "packets": len(rows), "errors": len(rows) - len(ok),
        "field_accuracy": sum(hits) / len(hits) if hits else 0.0,
        "critical_recall": len(caught) / len(planted) if planted else 1.0,
        "critical_planted": len(planted), "critical_caught": len(caught),
        "flag_precision": len(true_raised) / len(raised) if raised else 1.0,
        "false_flags": [f"{i}:{c}" for i, c in raised if (i, c) not in true_raised],
        "missed_flags": [f"{i}:{c}" for i, c in planted if (i, c) not in caught],
        "grounding_rate": (sum(r["grounded"] for r in ok) / sum(r["filled"] for r in ok)) if ok else 0.0,
        "packets_sent_to_review": sum(1 for r in ok if r["needs_review"]),
        # Business metric: clean packets that pass with no flag and no field to check.
        "clean_packets": sum(1 for r in ok if not r["expected_flags"]),
        "clean_auto_cleared": sum(1 for r in ok if not r["expected_flags"]
                                  and not r["flags"] and not r["needs_review"]),
        "avg_cost_usd": sum(r["cost_usd"] for r in ok) / len(ok) if ok else 0.0,
        "avg_latency_s": sum(r["latency_s"] for r in ok) / len(ok) if ok else 0.0,
    }
    s["ship"] = (s["errors"] == 0 and s["critical_recall"] >= GATE_CRITICAL_RECALL
                 and s["field_accuracy"] >= GATE_FIELD_ACCURACY)
    return s


def report(s: dict, rows: list[dict]) -> str:
    lines = [
        f"# Eval results - {s['model']} (effort {s['effort']}, backend {s['backend']})", "",
        f"**Ship gate:** {'PASS' if s['ship'] else 'FAIL'} "
        f"(critical recall >= {GATE_CRITICAL_RECALL:.0%}, field accuracy >= {GATE_FIELD_ACCURACY:.0%})", "",
        "| Metric | Value |", "|---|---|",
        f"| Packets | {s['packets']} ({s['errors']} errors) |",
        f"| Field accuracy | {s['field_accuracy']:.1%} |",
        f"| Critical-flag recall | {s['critical_recall']:.0%} ({s['critical_caught']}/{s['critical_planted']}) |",
        f"| Flag precision | {s['flag_precision']:.0%} |",
        f"| Grounding rate | {s['grounding_rate']:.1%} |",
        f"| Packets sent to human review | {s['packets_sent_to_review']} |",
        f"| Clean packets auto-cleared | {s['clean_auto_cleared']}/{s['clean_packets']} |",
        f"| Avg cost per packet | ${s['avg_cost_usd']:.4f} |",
        f"| Avg latency per packet | {s['avg_latency_s']:.1f}s |", "",
    ]
    if s["missed_flags"]:
        lines += ["**Missed critical flags:** " + ", ".join(s["missed_flags"]), ""]
    if s["false_flags"]:
        lines += ["**False flags:** " + ", ".join(s["false_flags"]), ""]
    wrong = [(r["id"], f, v) for r in rows if "error" not in r for f, v in r["wrong_fields"].items()]
    if wrong:
        lines += ["**Field errors:**", ""] + [f"- {i} `{f}`: got {v['got']!r}, want {v['want']!r}"
                                              for i, f, v in wrong] + [""]
    errs = [r for r in rows if "error" in r]
    if errs:
        lines += ["**Errors:**", ""] + [f"- {r['id']}: {r['error']}" for r in errs]
    return "\n".join(lines)


def main():
    ids = sys.argv[1:] or sorted(TRUTH)
    client = anthropic.Anthropic() if BACKEND == "api" else None
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(lambda i: score_one(i, client), ids))
    s = summarize(rows)
    RESULTS.mkdir(exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    (RESULTS / f"{stamp}.json").write_text(json.dumps({"summary": s, "rows": rows}, indent=2))
    md = report(s, rows)
    (RESULTS / "latest.md").write_text(md)
    (RESULTS / "latest.json").write_text(json.dumps({"summary": s, "rows": rows}, indent=2))
    print(md)


if __name__ == "__main__":
    main()
