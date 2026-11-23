"""Subscription Reviewer - Streamlit prototype.

Run:  streamlit run app.py
"""

import json
import os
import time
from pathlib import Path

import pandas as pd
import pypdfium2 as pdfium
import streamlit as st

from reviewer import cache
from reviewer.extract import FIELD_NAMES, ExtractionRefused
from reviewer.fund_terms import FUND_NAME, MINIMUM_COMMITMENT_USD
from reviewer.rules import CRITICAL, check

ROOT = Path(__file__).parent
PACKETS = ROOT / "data" / "packets"
UPLOADS = ROOT / "data" / "uploads"
TRUTH = json.loads((ROOT / "data" / "ground_truth.json").read_text())
EVAL_RESULTS = ROOT / "evals" / "results" / "latest.json"
DECISIONS = ROOT / "decisions.jsonl"

LABELS = {
    "investor_name": "Investor name",
    "investor_type": "Investor type",
    "commitment_amount_figures": "Commitment (figures)",
    "commitment_amount_words": "Commitment (words, as written)",
    "commitment_amount_words_value": "Commitment (words, as number)",
    "us_person": "U.S. person",
    "accreditation_basis": "Accreditation basis",
    "tax_form": "Tax form enclosed",
    "signed": "Signed",
    "signatory_name": "Signatory name",
    "signatory_title": "Signatory title",
    "signature_date": "Signature date",
}
BOOL_FIELDS = {"us_person", "signed"}
NUM_FIELDS = {"commitment_amount_figures", "commitment_amount_words_value"}

st.set_page_config(page_title="Subscription Reviewer", page_icon=":material/fact_check:", layout="wide")


# ---------- helpers ----------

def show(field: str, value) -> str:
    if value is None:
        return ""
    if field in BOOL_FIELDS:
        return "yes" if value else "no"
    if field in NUM_FIELDS:
        return f"{value:,.0f}"
    return str(value)


def parse(field: str, text: str):
    text = (text or "").strip()
    if not text:
        return False if field == "signed" else None
    if field in BOOL_FIELDS:
        return text.lower() in {"yes", "true", "y", "1"}
    if field in NUM_FIELDS:
        try:
            return float(text.replace("$", "").replace(",", "").replace("US", ""))
        except ValueError:
            return None
    return text


@st.cache_data(show_spinner=False)
def render_pages(pdf_bytes: bytes) -> list:
    doc = pdfium.PdfDocument(pdf_bytes)
    return [doc[i].render(scale=1.4).to_pil() for i in range(len(doc))]


def packet_label(pid: str) -> str:
    return f"{pid} - {TRUTH[pid]['fields']['investor_name']}"


def log_decision(packet: str, decision: str, flags, edits, note: str):
    entry = {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "packet": packet, "decision": decision,
             "flags": [f.code for f in flags], "reviewer_edits": edits, "note": note}
    with DECISIONS.open("a") as fh:
        fh.write(json.dumps(entry) + "\n")


# ---------- sidebar: choose a packet ----------

with st.sidebar:
    st.header("Subscription Reviewer")
    st.caption(f"{FUND_NAME}  \nMinimum commitment: ${MINIMUM_COMMITMENT_USD:,.0f}")
    source = st.segmented_control("Packet source", ["Sample packets", "Upload PDF"],
                                  default="Sample packets")
    pdf_path = None
    if source == "Upload PDF":
        up = st.file_uploader("Subscription booklet (PDF)", type="pdf")
        if up:
            UPLOADS.mkdir(parents=True, exist_ok=True)
            pdf_path = UPLOADS / up.name
            pdf_path.write_bytes(up.getvalue())
    else:
        pid = st.selectbox("Sample packet", sorted(TRUTH), format_func=packet_label)
        pdf_path = PACKETS / f"{pid}.pdf"
    refresh = st.toggle("Fresh model call (ignore cache)", value=False)
    run = st.button("Review packet", type="primary", use_container_width=True,
                    disabled=pdf_path is None)
    if os.environ.get("REVIEWER_BACKEND") != "claude-code" and not os.environ.get("ANTHROPIC_API_KEY"):
        st.caption(":material/info: No ANTHROPIC_API_KEY set: only cached results can be shown.")

tab_why, tab_review, tab_evals, tab_how = st.tabs(["Why this product", "Review", "Evals", "How it works"])

# ---------- review tab ----------

def review_tab():
    if pdf_path is None:
        st.info("Choose a sample packet or upload a PDF in the sidebar.")
        return

    key = str(pdf_path)
    if run:
        with st.spinner("Reading the packet..."):
            try:
                result, from_cache = cache.cached_extract(pdf_path, refresh=refresh)
                st.session_state[key] = (result, from_cache)
            except ExtractionRefused as e:
                st.error(f"The model declined this document; send it to manual review. ({e})")
            except Exception as e:
                st.error(f"Could not review the packet: {type(e).__name__}: {e}")

    if key not in st.session_state:
        digest = cache.file_hash(pdf_path.read_bytes())
        if hit := cache.load(digest):
            st.session_state[key] = (hit, True)

    pages = render_pages(pdf_path.read_bytes())
    left, right = st.columns([1, 1.5], gap="large")

    if key not in st.session_state:
        with left:
            st.image(pages[0], use_container_width=True)
        with right:
            st.info("Press **Review packet** to extract the fields and run the checks.")
        return

    result, from_cache = st.session_state[key]

    # Reviewer table: model output plus evidence; values are editable.
    ev_by_field = {}
    for ev in result.evidence:
        ev_by_field.setdefault(ev["field"], ev)
    rows = []
    for f in FIELD_NAMES:
        ev = ev_by_field.get(f, {})
        filled = result.fields.get(f) not in (None, False)
        if f in result.needs_review:
            status = "Check"
        elif filled and result.grounded.get(f):
            status = "Grounded"
        else:
            status = ""
        rows.append({"field": f, "Field": LABELS[f], "Value": show(f, result.fields.get(f)),
                     "Page": str(ev.get("page") or ""), "Evidence": ev.get("quote", ""),
                     "Status": status})
    df = pd.DataFrame(rows)

    with right:
        edited = st.data_editor(
            df, key=f"editor-{key}", hide_index=True, use_container_width=True,
            height=35 * (len(df) + 1) + 3,
            column_order=["Field", "Value", "Status", "Page", "Evidence"],
            disabled=["Field", "Page", "Evidence", "Status"],
            column_config={
                "Field": st.column_config.TextColumn(width="medium"),
                "Value": st.column_config.TextColumn(width="medium",
                                                     help="Edit to correct the model; checks re-run."),
                "Status": st.column_config.TextColumn(width="small",
                                                      help="Grounded: quote found on the cited page. "
                                                           "Check: no matching quote, or the model was unsure."),
                "Page": st.column_config.TextColumn(width="small"),
                "Evidence": st.column_config.TextColumn(width="large"),
            },
        )
        fields = {r["field"]: parse(r["field"], r["Value"]) for r in edited.to_dict("records")}
        edits = {f: {"model": result.fields.get(f), "reviewer": fields[f]}
                 for f in FIELD_NAMES if show(f, fields[f]) != show(f, result.fields.get(f))}
        flags = check(fields)
        critical = [f for f in flags if f.severity == CRITICAL]

    # Status banner and flags, shown above the table.
    with left:
        if critical:
            st.error(f"**Not in good order** - {len(critical)} critical issue(s). "
                     "Return to the investor or fix before acceptance.", icon=":material/block:")
        elif flags or result.needs_review:
            st.warning("**Needs a human check** before acceptance.", icon=":material/visibility:")
        else:
            st.success("**In good order** - all checks passed and every field is grounded.",
                       icon=":material/check_circle:")
        for f in flags:
            icon = ":material/error:" if f.severity == CRITICAL else ":material/warning:"
            st.markdown(f"{icon} **{f.code.replace('_', ' ').title()}** - {f.message}")
        if result.needs_review:
            st.markdown(":material/visibility: **Check these fields:** "
                        + ", ".join(LABELS[f] for f in result.needs_review))
        if edits:
            st.caption(f"Reviewer corrected {len(edits)} field(s); checks re-ran on the corrected values.")

        page_no = st.segmented_control("Page", list(range(1, len(pages) + 1)), default=1,
                                       format_func=lambda n: f"Page {n}", key=f"page-{key}")
        page_no = page_no or 1
        st.image(pages[page_no - 1], use_container_width=True)
        quotes = [e for e in result.evidence if e["page"] == page_no]
        if quotes:
            with st.expander(f"Evidence quoted from page {page_no} ({len(quotes)})"):
                for e in quotes:
                    st.markdown(f"- `{LABELS.get(e['field'], e['field'])}`: \"{e['quote']}\"")

    with right:
        note = st.text_input("Reviewer note (optional)", key=f"note-{key}")
        c1, c2 = st.columns(2)
        if c1.button("Approve", type="primary", use_container_width=True,
                     disabled=bool(critical), key=f"approve-{key}",
                     help="Disabled while critical issues remain."):
            log_decision(pdf_path.stem, "approved", flags, edits, note)
            st.toast("Approved and logged.", icon=":material/check:")
        if c2.button("Return to investor", use_container_width=True, key=f"return-{key}"):
            log_decision(pdf_path.stem, "returned", flags, edits, note)
            st.toast("Returned and logged.", icon=":material/undo:")
        st.caption(f"{result.model} | {result.input_tokens:,} in / {result.output_tokens:,} out tokens | "
                   f"${result.cost_usd:.4f} | {result.latency_s:.1f}s"
                   + (" | cached result" if from_cache else ""))

with tab_review:
    review_tab()

# ---------- evals tab ----------

with tab_evals:
    if not EVAL_RESULTS.exists():
        st.info("No eval run yet. Run `python -m evals.run_evals` (needs ANTHROPIC_API_KEY).")
    else:
        data = json.loads(EVAL_RESULTS.read_text())
        s, rows = data["summary"], data["rows"]
        st.subheader(f"{s['model']} - effort {s['effort']} - {s['packets']} packets")
        if s["ship"]:
            st.success("Ship gate: PASS (critical-flag recall 100%, field accuracy at least 95%)")
        else:
            st.error("Ship gate: FAIL (needs critical-flag recall 100% and field accuracy at least 95%)")
        m = st.columns(6)
        m[0].metric("Critical-flag recall", f"{s['critical_recall']:.0%}",
                    help=f"{s['critical_caught']} of {s['critical_planted']} planted defects caught")
        m[1].metric("Field accuracy", f"{s['field_accuracy']:.1%}")
        m[2].metric("Flag precision", f"{s['flag_precision']:.0%}")
        m[3].metric("Avg cost / packet", f"${s['avg_cost_usd']:.3f}")
        m[4].metric("Avg latency", f"{s['avg_latency_s']:.1f}s")
        if "clean_packets" in s:
            m[5].metric("Clean auto-cleared", f"{s['clean_auto_cleared']}/{s['clean_packets']}",
                        help="Clean booklets with no flag and no field sent to a human")
        st.caption("Synthetic, digitally generated booklets: an easy set. Real NIGO cases come next. "
                   "History: evals/results/v1-baseline.md, v2-na-fields.md.")
        table = [{
            "Packet": r["id"],
            "Expected flags": ", ".join(r.get("expected_flags", [])) or "-",
            "Raised flags": ", ".join(r.get("flags", [])) or "-",
            "Match": "error" if "error" in r else ("yes" if r["flags"] == r["expected_flags"] else "no"),
            "Wrong fields": ", ".join(r.get("wrong_fields", {})) or "-",
            "Sent to review": ", ".join(r.get("needs_review", [])) or "-",
            "Cost": r.get("cost_usd"), "Latency (s)": r.get("latency_s"),
        } for r in rows]
        st.dataframe(pd.DataFrame(table), hide_index=True, use_container_width=True,
                     column_config={"Cost": st.column_config.NumberColumn(format="$%.4f"),
                                    "Latency (s)": st.column_config.NumberColumn(format="%.1f")})

# ---------- why this product ----------

with tab_why:
    st.subheader("Know in minutes whether a subscription is in good order")
    st.markdown("An AI review layer for offline subscription booklets: it checks every field with "
                "evidence and leaves only the exceptions for a human. Full case and sources: `MEMO.md`.")
    c1, c2, c3 = st.columns(3)
    c1.metric("GPs saying KYC adds 6-30 days to a close", "74%", help="IQ-EQ fund managers survey, Apr 2026")
    c2.metric("GPs who lost investors over AML/KYC", "63%", help="CSC survey of 200 GPs and 200 LPs, Nov 2025")
    c3.metric("US evergreen fund assets", "~$500B", help="PitchBook US Evergreen Landscape, Q4 2025")
    st.markdown("""
**1. Why it should exist.** Private markets are adding individual investors fast. Each one is another
booklet to check, so review work grows with investor count. Anduin's online forms already validate input,
but offline PDFs are still re-keyed, and the final in-good-order check is still a person reading page by page.

**2. The pain.** Reviewers check signature, amounts, minimum, accreditation and tax form by hand. LPs hear
about problems late. GPs see closes slip and investors drop out. The worst case is a wrong acceptance.

**3. How big.** Surveys show weeks added to closings and investors lost (above). Vendors put NIGO at 20-60%,
but there is no independent benchmark: measuring it is step one of discovery.

**4. Worth doing.** It matches Anduin's 2026 direction (Review Agent, exception-based review), reuses
Instant Extraction and each fund's existing form rules, and competitors are already shipping AI extraction.
Risk is controlled by design: AI reads, code decides, a human approves.

**5. Business impact.** North star: first-time-right rate. Also tracked: days to acceptance, reviewer
minutes per booklet, critical misses (target 0), and attach rate to Fund Subscription and Data Extraction.
""")
    st.info("**Kill criterion, set before testing:** ship auto-clear only if critical-flag recall is 100% "
            "and field accuracy is at least 95% on the eval set. Otherwise it stays a pre-fill assistant.",
            icon=":material/rule:")

# ---------- how it works ----------

with tab_how:
    st.markdown("""
**Pipeline:** PDF -> Claude reads the booklet and returns typed fields, each with a page number and a
verbatim quote -> code checks every quote against the PDF text -> deterministic rules decide the flags ->
a reviewer corrects fields, sees the checks re-run, and approves or returns the packet.

**Where AI does the work:** reading messy documents - checkboxes, amounts written in words, whether a
signature line is actually signed.

**Where it does not:** pass/fail decisions. Minimums, tax-form rules and accreditation checks are plain
code, so every flag can be explained and audited.

**Human in the loop:** any field the model was unsure about, or whose quote cannot be found on the page,
is marked *Check*. Approve is disabled while a critical issue remains. Every decision and every
reviewer correction is logged to `decisions.jsonl`, which becomes the next eval set.
""")
