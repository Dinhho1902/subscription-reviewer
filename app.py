"""Subscription Reviewer - a guided product story plus a working review screen.

Run:  streamlit run app.py
"""

import json
import os
import time
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from reviewer import cache
from reviewer.extract import FIELD_NAMES, ExtractionRefused
from reviewer.fund_terms import FUND_NAME, MINIMUM_COMMITMENT_USD
from reviewer.highlight import render as render_page
from reviewer.rules import CRITICAL, check

ROOT = Path(__file__).parent
PACKETS = ROOT / "data" / "packets"
TRUTH = json.loads((ROOT / "data" / "ground_truth.json").read_text())
RESULTS = ROOT / "evals" / "results"
DECISIONS = ROOT / "decisions.jsonl"
MEMO_URL = "https://github.com/Dinhho1902/subscription-reviewer/blob/main/MEMO.md"
CODE_URL = "https://github.com/Dinhho1902/subscription-reviewer"

DEMO_MODE = os.environ.get("REVIEWER_BACKEND") != "claude-code" and not os.environ.get("ANTHROPIC_API_KEY")

STEPS = [
    ("problem", "The problem"),
    ("queue", "Today's queue"),
    ("review", "Review one booklet"),
    ("trust", "Can we trust it?"),
    ("impact", "What is it worth?"),
    ("next", "Why Anduin, what's next"),
]
STEP_KEYS = [k for k, _ in STEPS]

LABELS = {
    "investor_name": "Investor name", "investor_type": "Investor type",
    "commitment_amount_figures": "Commitment (figures)",
    "commitment_amount_words": "Commitment (words, as written)",
    "commitment_amount_words_value": "Commitment (words, as number)",
    "us_person": "U.S. person", "accreditation_basis": "Accreditation basis",
    "tax_form": "Tax form enclosed", "signed": "Signed", "signatory_name": "Signatory name",
    "signatory_title": "Signatory title", "signature_date": "Signature date",
}
FLAG_TITLES = {
    "MISSING_SIGNATURE": "Signature missing", "AMOUNT_MISMATCH": "Amounts disagree",
    "BELOW_MINIMUM": "Below fund minimum", "NO_ACCREDITATION": "No accreditation basis",
    "TAX_FORM_MISMATCH": "Wrong tax form", "MISSING_SIGNATORY_TITLE": "Signatory title missing",
}
BOOL_FIELDS = {"us_person", "signed"}
NUM_FIELDS = {"commitment_amount_figures", "commitment_amount_words_value"}

st.set_page_config(page_title="Subscription Reviewer", page_icon=":material/fact_check:",
                   layout="wide", initial_sidebar_state="auto")

# ---------- design tokens (Swiss / accessible document-workflow palette) ----------
st.html("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
:root{--navy:#1E3A5F;--blue:#1D4ED8;--fg:#0F172A;--muted:#475569;--border:#CBD5E1;--card:#FFFFFF;
--soft:#EEF2F7;--ok:#15803D;--ok-bg:#DCFCE7;--warn:#92400E;--warn-bg:#FEF3C7;--crit:#B91C1C;--crit-bg:#FEE2E2;}
html, body, [data-testid="stAppViewContainer"] *:not([data-testid="stIconMaterial"]),
[data-testid="stSidebar"] *:not([data-testid="stIconMaterial"]){font-family:'Inter',system-ui,sans-serif;}
[data-testid="stAppViewContainer"] .block-container{max-width:1180px;padding-top:2rem;}
.eyebrow{font-size:13px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--blue);margin:0 0 6px}
.hero{font-size:34px;line-height:1.2;font-weight:700;color:var(--fg);margin:0 0 10px;letter-spacing:-.01em}
.lead{font-size:17px;line-height:1.6;color:var(--muted);max-width:760px;margin:0 0 20px}
.h3{font-size:19px;font-weight:600;color:var(--fg);margin:8px 0 10px}
.card{background:var(--card);border:1px solid var(--border);border-radius:12px;padding:16px 20px;height:100%}
.card p{margin:4px 0;line-height:1.55;color:var(--fg);font-size:15px}
.card .muted{color:var(--muted);font-size:14px}
.kpi .num{font-size:34px;font-weight:700;color:var(--navy);line-height:1.1}
.kpi .lbl{font-size:15px;color:var(--fg);margin-top:6px;line-height:1.45}
.kpi .src{font-size:12.5px;color:var(--muted);margin-top:8px}
.note{border-left:4px solid var(--navy);background:var(--soft);padding:12px 16px;border-radius:0 10px 10px 0;
margin:12px 0 18px;color:var(--fg);font-size:15px;line-height:1.6}
.note .lbl{font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--navy);margin-bottom:2px}
.badge{display:inline-flex;align-items:center;gap:6px;padding:3px 10px;border-radius:999px;font-size:13px;
font-weight:600;white-space:nowrap;line-height:1.4}
.badge::before{content:"";width:8px;height:8px;border-radius:50%;background:currentColor;flex:none}
.badge.ok{background:var(--ok-bg);color:var(--ok)} .badge.warn{background:var(--warn-bg);color:var(--warn)}
.badge.crit{background:var(--crit-bg);color:var(--crit)} .badge.neutral{background:#E2E8F0;color:#334155}
.stepper{display:flex;gap:6px;flex-wrap:wrap;margin:0 0 22px!important;padding:0!important;list-style:none}
.stepper li{display:flex;align-items:center;gap:8px;font-size:13.5px;color:var(--muted);padding:6px 12px 6px 6px;
border-radius:999px;background:#fff;border:1px solid var(--border)}
.stepper li .n{width:22px;height:22px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;
font-size:12px;font-weight:700;background:#E2E8F0;color:#334155}
.stepper li.done .n{background:var(--ok-bg);color:var(--ok)}
.stepper li.cur{border-color:var(--navy);color:var(--fg);font-weight:600}
.stepper li.cur .n{background:var(--navy);color:#fff}
.flow{display:flex;gap:8px;flex-wrap:wrap;margin:4px 0 14px}
.flow span{background:#fff;border:1px solid var(--border);border-radius:8px;padding:6px 12px;font-size:14px;color:var(--fg)}
.flow b{color:var(--navy)}
.qrow{display:flex;align-items:center;gap:12px;min-height:44px}
.qid{font-variant-numeric:tabular-nums;color:var(--muted);font-size:14px;width:72px;flex:none}
.qname{font-weight:600;color:var(--fg);font-size:15px}
.qwhy{color:var(--muted);font-size:14px}
.finding{border:1px solid var(--border);border-radius:10px;padding:12px 14px;background:#fff;margin-bottom:10px}
.finding.crit{border-left:4px solid var(--crit)} .finding.warn{border-left:4px solid #D97706}
.finding .t{font-weight:600;color:var(--fg);font-size:15px;margin:6px 0 2px}
.finding .m{color:var(--fg);font-size:14.5px;line-height:1.5}
.quote{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:13px;background:var(--soft);
border-radius:6px;padding:4px 8px;margin-top:6px;color:#1E293B;display:inline-block}
.big-ok{border:1px solid #86EFAC;background:#F0FDF4;border-radius:12px;padding:14px 16px;color:var(--fg)}
.trail li{font-size:14px;color:var(--fg);margin:4px 0;line-height:1.5}
.foot{color:var(--muted);font-size:13px;margin-top:28px}
div.stButton > button{min-height:44px;border-radius:10px;font-weight:600}
@media (max-width: 640px){.hero{font-size:27px}.lead{font-size:16px}.stepper li:not(.cur){display:none}
.qrow{flex-wrap:wrap;gap:6px 10px}.qid{width:auto}}
@media (prefers-reduced-motion: reduce){*{transition:none!important;animation:none!important}}
</style>
""")


# ---------- state & navigation ----------

def init_state():
    qp = st.query_params
    if "step" not in st.session_state:
        st.session_state.step = qp.get("step") if qp.get("step") in STEP_KEYS else "problem"
    if "pid" not in st.session_state:
        st.session_state.pid = qp.get("booklet") if qp.get("booklet") in TRUTH else "SUB-018"
    st.session_state.setdefault("ai_view", "With AI pre-check")
    st.session_state.setdefault("trail", {})


def go(step: str, pid: str | None = None):
    st.session_state.step = step
    st.query_params["step"] = step
    if pid:
        st.session_state.pid = pid
        st.session_state.pop(f"page-{pid}", None)
        st.query_params["booklet"] = pid


def nav(back: str | None, nxt: str | None, next_label: str | None = None):
    st.write("")
    c1, _, c2 = st.columns([1, 2, 1])
    if back:
        c1.button(f"Back: {dict(STEPS)[back]}", icon=":material/arrow_back:", on_click=go, args=(back,),
                  use_container_width=True, key=f"back-{st.session_state.step}")
    if nxt:
        c2.button(next_label or f"Next: {dict(STEPS)[nxt]}", icon=":material/arrow_forward:",
                  type="primary", on_click=go, args=(nxt,), use_container_width=True,
                  key=f"next-{st.session_state.step}")


def stepper():
    cur = STEP_KEYS.index(st.session_state.step)
    items = []
    for i, (_, label) in enumerate(STEPS):
        cls = "cur" if i == cur else ("done" if i < cur else "")
        mark = "&#10003;" if i < cur else str(i + 1)
        items.append(f'<li class="{cls}"><span class="n">{mark}</span>{label}</li>')
    st.html(f'<ol class="stepper" aria-label="Story progress">{"".join(items)}</ol>')


def note(text: str, label: str = "PM note"):
    st.html(f'<div class="note" role="note"><div class="lbl">{label}</div>{text}</div>')


def header(eyebrow: str, title: str, lead: str = ""):
    st.html(f'<p class="eyebrow">{eyebrow}</p><h1 class="hero">{title}</h1>'
            + (f'<p class="lead">{lead}</p>' if lead else ""))


def badge(kind: str, text: str) -> str:
    return f'<span class="badge {kind}">{text}</span>'


# ---------- data ----------

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
def pdf_bytes(pid: str) -> bytes:
    return (PACKETS / f"{pid}.pdf").read_bytes()


def result_for(pid: str):
    key = f"result-{pid}"
    if key not in st.session_state:
        st.session_state[key] = cache.load(cache.file_hash(pdf_bytes(pid)))
    return st.session_state[key]


def status(pid: str) -> tuple[str, list, list]:
    """('cleared' | 'critical' | 'check' | 'missing', flags, needs_review)"""
    r = result_for(pid)
    if r is None:
        return "missing", [], []
    flags = check(r.fields)
    if any(f.severity == CRITICAL for f in flags):
        return "critical", flags, r.needs_review
    if flags or r.needs_review:
        return "check", flags, r.needs_review
    return "cleared", flags, r.needs_review


@st.cache_data(show_spinner=False)
def load_eval(name: str):
    path = RESULTS / name
    return json.loads(path.read_text()) if path.exists() else None


@st.cache_data(show_spinner=False)
def page_image(pid: str, page_index: int, marks: tuple):
    return render_page(pdf_bytes(pid), page_index, list(marks))


# ---------- step 1: the problem ----------

def step_problem():
    header("Closing week at a fund administrator",
           "Twenty subscription booklets arrived overnight. Which ones are safe to accept?",
           "Every offline booklet is read page by page: signature, amounts, minimum, accreditation, "
           "tax form. Problems surface late, closes slip, and the worst case is accepting a booklet that "
           "should have been sent back.")
    k = st.columns(3)
    kpis = [
        ("74%", "of GPs say KYC adds 6 to 30 days to a fund close", "IQ-EQ fund managers survey, Apr 2026"),
        ("63%", "of GPs lost investors over AML/KYC; documentation gaps were the main cause",
         "CSC survey of 200 GPs and 200 LPs, Nov 2025"),
        ("~$500B", "in US evergreen funds: more individual investors, more booklets per dollar raised",
         "PitchBook US Evergreen Landscape, Q4 2025"),
    ]
    for col, (num, lbl, src) in zip(k, kpis):
        col.html(f'<div class="card kpi"><div class="num">{num}</div><div class="lbl">{lbl}</div>'
                 f'<div class="src">Source: {src}</div></div>')
    st.write("")
    left, right = st.columns([1.1, 1])
    with left:
        st.html('<div class="h3">Who feels it</div>'
                '<div class="card"><p><b>Reviewer at a fund administrator or GP ops team</b></p>'
                '<p class="muted">"When a subscription arrives, I want to know quickly whether it is in good '
                'order and exactly what is missing, so we close on time without ever accepting a defective '
                'subscription."</p>'
                '<p style="margin-top:10px">Also affected: the LP, who hears about problems late; the GP, whose '
                'close slips; compliance, who owns the risk of a wrong acceptance.</p></div>')
    with right:
        st.html('<div class="h3">Where the gap is</div>'
                '<div class="card"><p>Anduin\'s online forms already validate input as LPs type.</p>'
                '<p>Offline PDFs are still re-keyed. Instant Extraction gets the data out, but its page '
                'promises "80%+ accuracy out of the box" and leaves low-confidence fields to a human.</p>'
                '<p>The final "is this in good order?" check is still a person reading pages.</p></div>')
    note("The bet: if a model reads the booklet and code applies the fund's rules, reviewers only touch "
         "the booklets that need them. Anduin lists a <b>Review Agent</b> on its 2026 timeline, and GP Con "
         "2026 panels asked for exception-based review. This prototype is one way to build it.")
    st.button("Open today's queue", icon=":material/inbox:", type="primary", on_click=go, args=("queue",))


# ---------- step 2: the queue ----------

def step_queue():
    header("The product", "Only the exceptions should reach a human",
           "Same twenty booklets, two ways of working. Switch the view to see what changes for the reviewer.")
    view = st.segmented_control("Way of working", ["Without AI", "With AI pre-check"],
                                key="ai_view", label_visibility="collapsed")
    rows = [(pid, *status(pid)) for pid in sorted(TRUTH)]
    cleared = [r for r in rows if r[1] == "cleared"]
    attention = [r for r in rows if r[1] in ("critical", "check")]

    if view == "Without AI":
        c = st.columns(3)
        c[0].html('<div class="card kpi"><div class="num">20</div><div class="lbl">booklets to read page by page</div></div>')
        c[1].html('<div class="card kpi"><div class="num">4</div><div class="lbl">pages per booklet, every field checked by hand</div></div>')
        c[2].html('<div class="card kpi"><div class="num">?</div><div class="lbl">defects found only when someone reaches that page</div></div>')
        note("Without a pre-check every booklet costs the same review time, whether it is clean or not. "
             "Switch to <b>With AI pre-check</b> to see the queue the reviewer would get instead.")
        for pid, *_ in rows:
            queue_row(pid, "neutral", "To review", "Not yet opened", button=False)
        st.write("")
        st.button("See the same queue with the AI pre-check", icon=":material/auto_awesome:", type="primary",
                  on_click=lambda: st.session_state.update(ai_view="With AI pre-check"))
        nav("problem", None)
        return

    c = st.columns(3)
    c[0].html(f'<div class="card kpi"><div class="num" style="color:var(--ok)">{len(cleared)}</div>'
              '<div class="lbl">cleared: no rule fired and every field is backed by a quote on the page</div></div>')
    c[1].html(f'<div class="card kpi"><div class="num" style="color:var(--crit)">{len(attention)}</div>'
              '<div class="lbl">need attention, each with the reason and the page it comes from</div></div>')
    c[2].html('<div class="card kpi"><div class="num">~12s</div>'
              '<div class="lbl">per booklet for the pre-check (Claude Opus 5.5, measured in the eval run)</div></div>')
    note("Cleared is strict: no rule fired, every extracted field has a verbatim quote found on the cited page, "
         "and the model did not mark anything as unsure. Anything else goes to a human, with the reason.")

    b1, b2, _ = st.columns([1.3, 1.3, 1])
    b1.button("Open the hardest catch: SUB-018", icon=":material/search:", type="primary",
              on_click=go, args=("review", "SUB-018"), use_container_width=True)
    b2.button("Open a clean booklet: SUB-001", icon=":material/task_alt:",
              on_click=go, args=("review", "SUB-001"), use_container_width=True)

    st.html('<div class="h3">Needs attention</div>')
    for pid, kind, flags, needs in attention:
        why = ", ".join(FLAG_TITLES.get(f.code, f.code) for f in flags) or \
              "Check: " + ", ".join(LABELS.get(n, n) for n in needs)
        queue_row(pid, "crit" if kind == "critical" else "warn",
                  "Return or fix" if kind == "critical" else "Check", why)
    st.html('<div class="h3">Cleared</div>')
    for pid, *_ in cleared:
        queue_row(pid, "ok", "In good order", "All checks passed")
    nav("problem", "review")


def queue_row(pid: str, kind: str, label: str, why: str, button: bool = True):
    name = TRUTH[pid]["fields"]["investor_name"]
    c1, c2 = st.columns([5, 1], vertical_alignment="center")
    c1.html(f'<div class="qrow"><span class="qid">{pid}</span><span class="qname">{name}</span>'
            f'{badge(kind, label)}<span class="qwhy">{why}</span></div>')
    if button:
        c2.button("Open", key=f"open-{pid}", on_click=go, args=("review", pid), use_container_width=True)


# ---------- step 3: review one booklet ----------

def step_review():
    pid = st.session_state.pid
    result = result_for(pid)
    top = st.columns([1, 3])
    top[0].button("Back to queue", icon=":material/arrow_back:", on_click=go, args=("queue",))
    if result is None:
        st.warning("No recorded result for this booklet yet. Run the eval to create one.")
        return

    # Apply reviewer edits (kept by the editor widget) before running the rules.
    ekey = f"editor-{pid}"
    fields = dict(result.fields)
    edits = {}
    for idx, change in st.session_state.get(ekey, {}).get("edited_rows", {}).items():
        f = FIELD_NAMES[int(idx)]
        if "Value" in change:
            fields[f] = parse(f, change["Value"])
            if show(f, fields[f]) != show(f, result.fields.get(f)):
                edits[f] = {"model": result.fields.get(f), "reviewer": fields[f]}
    flags = check(fields)
    critical = [f for f in flags if f.severity == CRITICAL]
    if critical:
        state_badge = badge("crit", f"Not in good order: {len(critical)} critical")
    elif flags or result.needs_review:
        state_badge = badge("warn", "Needs a human check")
    else:
        state_badge = badge("ok", "In good order")

    header(f"Booklet {pid}", f'{TRUTH[pid]["fields"]["investor_name"]}', "")
    st.html(f'<div style="margin:-6px 0 12px">{state_badge}</div>'
            f'<div class="flow" aria-label="How the review works">'
            f'<span><b>1</b> Claude reads the booklet ({result.latency_s:.0f}s)</span>'
            f'<span><b>2</b> Code checks every quote and the fund rules</span>'
            f'<span><b>3</b> You decide</span></div>')

    ev = {}
    for e in result.evidence:
        ev.setdefault(e["field"], []).append(e)
    flag_pages = [e["page"] for fl in flags for fd in fl.fields for e in ev.get(fd, [])]
    page_key = f"page-{pid}"
    if page_key not in st.session_state:
        st.session_state[page_key] = flag_pages[0] if flag_pages else 1

    left, right = st.columns([1.05, 1], gap="large")
    with right:
        st.html('<div class="h3">Findings</div>')
        if not flags:
            st.html('<div class="big-ok"><b>In good order.</b> No rule fired, and every field is backed by '
                    'a quote found on the page. This booklet would skip the reviewer\'s queue.</div>')
        for fl in flags:
            kind = "crit" if fl.severity == CRITICAL else "warn"
            quotes = [e for fd in fl.fields for e in ev.get(fd, [])][:2]
            qhtml = "".join(f'<div class="quote">p.{e["page"]}: "{e["quote"]}"</div><br>' for e in quotes)
            st.html(f'<div class="finding {kind}">{badge(kind, "Critical" if kind == "crit" else "Warning")}'
                    f'<div class="t">{FLAG_TITLES.get(fl.code, fl.code)}</div>'
                    f'<div class="m">{fl.message}</div>{qhtml}</div>')
            if quotes:
                st.button(f"Show on page {quotes[0]['page']}", key=f"show-{pid}-{fl.code}",
                          icon=":material/visibility:",
                          on_click=lambda p=quotes[0]["page"]: st.session_state.update({page_key: p}))
        if result.needs_review:
            st.html('<div class="finding warn">' + badge("warn", "Check") +
                    '<div class="t">The model was unsure about</div><div class="m">'
                    + ", ".join(LABELS.get(n, n) for n in result.needs_review) + '</div></div>')
        if pid == "SUB-018" and flags:
            note("The hardest planted defect: US$1,500,000 in figures against \"One Million Fifty Thousand\" "
                 "in words. The model reads both independently and code compares them. A reviewer skimming "
                 "the page sees two plausible numbers.")
        else:
            note("AI reads, code decides, a human approves. The model never says pass or fail: every flag "
                 "comes from a plain rule, so it can be explained to the investor or an auditor.")

        st.html('<div class="h3">Your decision</div>')
        d1, d2 = st.columns(2)
        approved = d1.button("Approve", type="primary", icon=":material/check:", key=f"approve-{pid}",
                             disabled=bool(critical), use_container_width=True,
                             help="Disabled while a critical issue remains.")
        returned = d2.button("Return to investor", icon=":material/undo:", key=f"return-{pid}",
                             use_container_width=True)
        trail = st.session_state.trail.setdefault(pid, [])
        if approved:
            log_decision(pid, "approved", flags, edits)
            trail.append(f"{time.strftime('%H:%M')} Reviewer approved" + (f" after {len(edits)} correction(s)" if edits else ""))
            st.toast("Approved and logged.", icon=":material/check:")
        if returned:
            log_decision(pid, "returned", flags, edits)
            trail.append(f"{time.strftime('%H:%M')} Reviewer returned the booklet to the investor")
        if returned or st.session_state.get(f"draft-{pid}"):
            st.session_state[f"draft-{pid}"] = True
            items = "\n".join(f"- {FLAG_TITLES.get(f.code, f.code)}: {f.message}" for f in flags) or \
                    "- Please confirm the fields marked for review."
            st.text_area("Draft note to the investor (edit before sending)", height=150, key=f"note-{pid}",
                         value=f"Thank you for your subscription. Before we can accept it into {FUND_NAME}, "
                               f"please correct the following:\n{items}")

        with st.expander("All extracted fields (edit to correct the model)"):
            rows = [{"Field": LABELS[f], "Value": show(f, result.fields.get(f)),
                     "Page": str(ev[f][0]["page"]) if f in ev else "",
                     "Evidence": ev[f][0]["quote"] if f in ev else ""} for f in FIELD_NAMES]
            st.data_editor(rows, key=ekey, hide_index=True, use_container_width=True,
                           disabled=["Field", "Page", "Evidence"],
                           column_config={"Value": st.column_config.TextColumn(
                               help="Edit a value; the checks re-run immediately.")})
            if edits:
                st.caption(f"{len(edits)} correction(s). Corrections are logged and become new eval cases.")

        with st.expander("Audit trail"):
            grounded = sum(1 for f in FIELD_NAMES if result.grounded.get(f))
            base = [f"Claude read the booklet: {result.model}, {result.latency_s:.1f}s, "
                    f"{result.input_tokens:,} input / {result.output_tokens:,} output tokens, ${result.cost_usd:.3f}",
                    f"Grounding: {grounded} field quotes found on the cited page",
                    f"Rules: {len(critical)} critical, {len(flags) - len(critical)} warning"]
            st.html('<ul class="trail">' + "".join(f"<li>{t}</li>" for t in base + trail) + "</ul>")
        if not DEMO_MODE:
            if st.button("Re-run with Claude now", icon=":material/refresh:", key=f"rerun-{pid}"):
                try:
                    st.session_state[f"result-{pid}"], _ = cache.cached_extract(PACKETS / f"{pid}.pdf", refresh=True)
                    st.rerun()
                except (ExtractionRefused, Exception) as e:
                    st.error(f"Could not run the model: {e}")

    with left:
        page_no = st.segmented_control("Page", [1, 2, 3, 4], key=page_key,
                                       format_func=lambda n: f"Page {n}") or 1
        marks = []
        for fl in flags:
            for fd in fl.fields:
                for e in ev.get(fd, []):
                    if e["page"] == page_no:
                        marks.append((e["quote"], "critical" if fl.severity == CRITICAL else "warning"))
        if not flags:
            marks = [(e["quote"], "ok") for es in ev.values() for e in es if e["page"] == page_no]
        img, found = page_image(pid, page_no - 1, tuple(marks))
        st.image(img, use_container_width=True)
        if marks:
            st.caption(f"Highlighted on this page: {found} quote(s) the findings rely on."
                       if flags else f"Highlighted: {found} quote(s) the model used as evidence.")

    nav("queue", "trust")


def log_decision(pid, decision, flags, edits):
    entry = {"time": time.strftime("%Y-%m-%d %H:%M:%S"), "packet": pid, "decision": decision,
             "flags": [f.code for f in flags], "reviewer_edits": edits}
    try:
        with DECISIONS.open("a") as fh:
            fh.write(json.dumps(entry) + "\n")
    except OSError:
        pass


# ---------- step 4: trust ----------

def step_trust():
    header("Evidence before shipping", "Can we trust it? The bar was set before testing.",
           "Twenty booklets with known answers, eleven of them with planted defects. "
           "The pre-check only ships as auto-clear if it passes the gate.")
    v1, v2 = load_eval("v1-baseline.json"), load_eval("v2-na-fields.json")
    s = (v2 or load_eval("latest.json") or {}).get("summary")
    if not s:
        st.info("No eval run yet. Run `python -m evals.run_evals`.")
        return
    gate = badge("ok", "PASS") if s["ship"] else badge("crit", "FAIL")
    st.html(f'<div class="card"><p><b>Ship gate</b> {gate}</p>'
            '<p class="muted">Catch 100% of critical defects (a missed one means a bad subscription is accepted) '
            'and get at least 95% of fields right. Otherwise it stays a pre-fill assistant.</p></div>')
    st.write("")
    c = st.columns(4)
    for col, (num, lbl) in zip(c, [
        (f"{s['critical_caught']}/{s['critical_planted']}", "critical defects caught"),
        (f"{s['field_accuracy']:.0%}", "of fields extracted correctly"),
        (f"{s['clean_auto_cleared']}/{s['clean_packets']}", "clean booklets cleared with no human touch"),
        (f"${s['avg_cost_usd']:.2f} / {s['avg_latency_s']:.0f}s", "per booklet, list-price estimate"),
    ]):
        col.html(f'<div class="card kpi"><div class="num">{num}</div><div class="lbl">{lbl}</div></div>')

    st.html('<div class="h3" style="margin-top:22px">One iteration, measured</div>')
    if v1 and v2:
        a, b = v1["summary"], v2["summary"]
        st.html(f'<div class="card"><p><b>v1</b>: {a["clean_auto_cleared"]}/{a["clean_packets"]} clean booklets cleared. '
                'The model marked fields that do not apply (a signatory title for an individual) as "unsure", '
                'so clean booklets went to a human.</p>'
                f'<p><b>v2</b>: one sentence added to the prompt. {b["clean_auto_cleared"]}/{b["clean_packets"]} cleared, '
                f'still {b["critical_caught"]}/{b["critical_planted"]} defects caught.</p></div>')
    st.write("")
    c = st.columns(3)
    c[0].html('<div class="card"><p><b>The model\'s doubt is a signal</b></p><p class="muted">In v2, every booklet '
              'it marked as unsure really had a defect.</p></div>')
    c[1].html('<div class="card"><p><b>It found a rule I had missed</b></p><p class="muted">In v1 it doubted a joint '
              'account signed by one holder. That becomes a rule, not something left to the model.</p></div>')
    c[2].html('<div class="card"><p><b>Why 100% is not the headline</b></p><p class="muted">Twenty clean, digital '
              'booklets are an easy test. Scans, handwriting and side letters come next, from real NIGO cases.</p></div>')
    note("The point of this step is the habit, not the score: decide the kill criterion first, measure, "
         "change one thing, measure again, and say plainly what the test does not cover.")
    nav("review", "impact")


# ---------- step 5: impact ----------

def step_impact():
    header("Business case", "What is it worth?",
           "North star: the share of subscriptions in good order at first review. "
           "The calculator below shows how review time moves; every input is an assumption to replace in discovery.")
    left, right = st.columns([1, 1.2], gap="large")
    with left:
        st.html('<div class="h3">Your assumptions</div>')
        n = st.number_input("Booklets in a close", 50, 20000, 1000, step=50,
                            help="A large close can mean over 1,000 subscription agreements (Cadwalader, 2024).")
        manual = st.slider("Minutes to review one booklet by hand", 5, 90, 30)
        share = st.slider("Share that still needs a human", 5, 100, 35, format="%d%%",
                          help="Vendors estimate 20-60% of documents arrive not in good order; no independent benchmark exists.")
        exc = st.slider("Minutes per exception with findings and evidence ready", 1, 60, 10)
    before = n * manual / 60
    after = n * share / 100 * exc / 60
    saved = before - after
    ai_cost = n * 0.09
    with right:
        st.html('<div class="h3">Review time for this close</div>')
        c = st.columns(2)
        c[0].html(f'<div class="card kpi"><div class="num">{before:,.0f} h</div><div class="lbl">reading every booklet by hand</div></div>')
        c[1].html(f'<div class="card kpi"><div class="num" style="color:var(--ok)">{after:,.0f} h</div><div class="lbl">reviewing only the exceptions</div></div>')
        st.write("")
        c = st.columns(2)
        c[0].html(f'<div class="card kpi"><div class="num">{saved:,.0f} h</div><div class="lbl">saved ({(saved / before if before else 0):.0%})</div></div>')
        c[1].html(f'<div class="card kpi"><div class="num">${ai_cost:,.0f}</div><div class="lbl">model cost at the measured ~$0.09 per booklet</div></div>')
    note("Illustrative only. The inputs are assumptions; the measured parts are speed (~12s) and cost (~$0.09) "
         "per booklet. In discovery I would replace each slider with numbers from three fund admins during a close.")
    st.html('<div class="h3">What I would track</div>')
    c = st.columns(4)
    for col, (t, d) in zip(c, [
        ("Customer outcome", "Days from first submission to acceptance; LP drop-off"),
        ("Ops efficiency", "Reviewer minutes per booklet; share auto-cleared"),
        ("Safety", "Critical defects missed in production spot audits (target 0)"),
        ("Anduin", "Attach to Fund Subscription and Data Extraction; win rate; offline LPs moved online"),
    ]):
        col.html(f'<div class="card"><p><b>{t}</b></p><p class="muted">{d}</p></div>')
    nav("trust", "next")


# ---------- step 6: why Anduin, what's next ----------

def step_next():
    header("Fit and plan", "Why Anduin, and what I would do next")
    c = st.columns(3)
    for col, (t, d) in zip(c, [
        ("On the roadmap", "Review Agent is on Anduin's 2026 timeline; GP Con 2026 panels asked for exception-based review."),
        ("Reuses what exists", "Instant Extraction's confidence flags and the rules already encoded in each fund's adaptive form: one rule set for online and offline."),
        ("Ahead of parity", "Juniper Square, Carta and Allvue ship AI extraction. Deciding \"in good order, with evidence\" is the step after."),
    ]):
        col.html(f'<div class="card"><p><b>{t}</b></p><p class="muted">{d}</p></div>')
    st.html('<div class="h3" style="margin-top:22px">Plan</div>')
    c = st.columns(3)
    for col, (t, d) in zip(c, [
        ("Weeks 1-2: discovery", "Sit with three fund admins during a close. Measure minutes per booklet, NIGO rate and the top five defect types."),
        ("Weeks 3-8: pilot", "Offline booklets after Instant Extraction, assist mode only. Track critical misses, reviewer minutes and overrides."),
        ("Then: move upstream", "Run the same checks when the LP submits, so issues are fixed before they reach the admin."),
    ]):
        col.html(f'<div class="card"><p><b>{t}</b></p><p class="muted">{d}</p></div>')
    note("Cut for now: scanned and handwritten pages, side letters, e-signature validation, a UI for fund terms. "
         "Next rule to add: every holder of a joint account must sign.")
    b = st.columns([1, 1, 1])
    b[0].link_button("Read the full case (MEMO.md)", MEMO_URL, icon=":material/description:", use_container_width=True)
    b[1].link_button("See the code", CODE_URL, icon=":material/code:", use_container_width=True)
    b[2].button("Start the story again", icon=":material/replay:", on_click=go, args=("problem",), use_container_width=True)
    st.html('<p class="foot">Prototype by Dinh H.N. Thong. All funds, investors and booklets are synthetic.</p>')


# ---------- layout ----------

init_state()
with st.sidebar:
    st.markdown("### Subscription Reviewer")
    st.caption(f"AI pre-check for offline subscription booklets  \n{FUND_NAME} (synthetic), "
               f"minimum ${MINIMUM_COMMITMENT_USD:,.0f}")
    for i, (key, label) in enumerate(STEPS, 1):
        st.button(f"{i}. {label}", key=f"nav-{key}", on_click=go, args=(key,), use_container_width=True,
                  type="primary" if key == st.session_state.step else "secondary")
    if DEMO_MODE:
        st.caption("Public demo: shows Claude's recorded results from the eval run. Live model calls are off.")
    st.markdown(f"[Product case]({MEMO_URL}) · [Code]({CODE_URL})")

if st.session_state.get("last_step") != st.session_state.step:
    # New step: start at the top of the page, not where the previous step was scrolled to.
    st.session_state.last_step = st.session_state.step
    components.html(f"""<script>/* {st.session_state.step} */
      const d = window.parent.document;
      const m = d.querySelector('[data-testid="stMain"]') || d.querySelector('section.main');
      if (m) m.scrollTo({{top: 0}}); window.parent.scrollTo(0, 0);</script>""", height=0)

stepper()
{"problem": step_problem, "queue": step_queue, "review": step_review,
 "trust": step_trust, "impact": step_impact, "next": step_next}[st.session_state.step]()
