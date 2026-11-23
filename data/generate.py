"""Generate synthetic subscription packets (PDF) with ground truth.

Every investor, fund and number here is invented. Each packet has four pages:
subscription agreement, investor questionnaire, tax documentation, signature page.
Some packets carry deliberate defects (unsigned, below minimum, amount mismatch,
wrong tax form, no accreditation, missing signatory title).

Run:  python -m data.generate
Out:  data/packets/*.pdf and data/ground_truth.json
"""

import json
from pathlib import Path

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from reviewer.fund_terms import FUND_NAME
from reviewer.rules import check

ROOT = Path(__file__).parent
OUT_DIR = ROOT / "packets"

ACCREDITATION_OPTIONS = {
    "individual": [
        ("income", "Individual income above $200,000 (or $300,000 jointly) in each of the last two years."),
        ("net_worth", "Individual or joint net worth above $1,000,000, excluding primary residence."),
        ("license", "Holder in good standing of a Series 7, 65 or 82 license."),
    ],
    "entity": [
        ("entity_assets", "Entity with total assets above $5,000,000, not formed to make this investment."),
        ("all_owners_accredited", "Entity in which every equity owner is an accredited investor."),
    ],
}

INVESTOR_TYPE_LABELS = [
    ("individual", "Individual"), ("joint", "Joint tenants"), ("ira", "IRA"),
    ("trust", "Trust"), ("llc", "Limited liability company"),
    ("corporation", "Corporation"), ("partnership", "Partnership"),
]

# Each spec is one packet. Fields not listed default to clean values.
SPECS = [
    dict(id="SUB-001", name="Margaret L. Hollis", type="individual", amount=500_000, us=True,
         country="United States", basis="income", form="W-9", signer="Margaret L. Hollis"),
    dict(id="SUB-002", name="Cedar Ridge Holdings LLC", type="llc", amount=1_000_000, us=True,
         country="United States", basis="entity_assets", form="W-9", signer="Daniel Okafor",
         title="Managing Member"),
    dict(id="SUB-003", name="The Albright Family Trust", type="trust", amount=750_000, us=True,
         country="United States", basis="entity_assets", form="W-9", signer="Susan Albright",
         title="Trustee"),
    dict(id="SUB-004", name="Wei Ling Tan", type="individual", amount=300_000, us=False,
         country="Singapore", basis="net_worth", form="W-8BEN", signer="Wei Ling Tan"),
    dict(id="SUB-005", name="Harrowgate Capital Ltd", type="corporation", amount=2_500_000, us=False,
         country="United Kingdom", basis="entity_assets", form="W-8BEN-E", signer="James Whitcombe",
         title="Director"),
    dict(id="SUB-006", name="Robert and Elena Marsh", type="joint", amount=400_000, us=True,
         country="United States", basis="net_worth", form="W-9", signer="Robert Marsh"),
    dict(id="SUB-007", name="Equity Trust Co. FBO Priya Raman IRA", type="ira", amount=250_000, us=True,
         country="United States", basis="net_worth", form="W-9", signer="Priya Raman"),
    dict(id="SUB-008", name="Bluestem Ventures LP", type="partnership", amount=5_000_000, us=True,
         country="United States", basis="all_owners_accredited", form="W-9", signer="Carla Mendes",
         title="General Partner"),
    dict(id="SUB-009", name="Thomas J. Reyes", type="individual", amount=600_000, us=True,
         country="United States", basis="income", form="W-9", signer="Thomas J. Reyes", signed=False),
    dict(id="SUB-010", name="Angela Kowalski", type="individual", amount=200_000, us=True,
         country="United States", basis="net_worth", form="W-9", signer="Angela Kowalski"),
    dict(id="SUB-011", name="Northbank Family Office LLC", type="llc", amount=600_000, words_amount=650_000,
         us=True, country="United States", basis="entity_assets", form="W-9", signer="Helen Park",
         title="Chief Investment Officer"),
    dict(id="SUB-012", name="Lucas Ferreira", type="individual", amount=450_000, us=False,
         country="Brazil", basis="income", form="W-9", signer="Lucas Ferreira"),
    dict(id="SUB-013", name="Granite Peak Partners LLC", type="llc", amount=1_200_000, us=True,
         country="United States", basis="entity_assets", form="W-8BEN-E", signer="Mark Ellison",
         title="Manager"),
    dict(id="SUB-014", name="The Nakamura Revocable Trust", type="trust", amount=800_000, us=True,
         country="United States", basis=None, form="W-9", signer="Kenji Nakamura", title="Trustee"),
    dict(id="SUB-015", name="Solano Industrial Corp.", type="corporation", amount=3_000_000, us=True,
         country="United States", basis="entity_assets", form="W-9", signer="Diana Solano", title=None),
    dict(id="SUB-016", name="Gregory Avila", type="individual", amount=350_000, us=True,
         country="United States", basis="license", form="none", signer="Gregory Avila"),
    dict(id="SUB-017", name="Natalie Brooks", type="individual", amount=150_000, us=True,
         country="United States", basis="income", form="W-9", signer="Natalie Brooks", signed=False),
    dict(id="SUB-018", name="Westlake Endowment Partners LP", type="partnership", amount=1_500_000,
         words_amount=1_050_000, us=True, country="United States", basis="all_owners_accredited",
         form="W-9", signer="Owen Fitzgerald", title="General Partner"),
    dict(id="SUB-019", name="Kestrel Holdings Pte. Ltd.", type="corporation", amount=900_000, us=False,
         country="Singapore", basis=None, form="W-8BEN", signer="Arjun Mehta", title="Director"),
    dict(id="SUB-020", name="Nguyen Thi Minh Anh", type="individual", amount=350_000, us=False,
         country="Vietnam", basis="license", form="W-8BEN", signer="Nguyen Thi Minh Anh"),
]

ONES = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten",
        "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen",
        "Eighteen", "Nineteen"]
TENS = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]


def _under_thousand(n: int) -> str:
    parts = []
    if n >= 100:
        parts.append(f"{ONES[n // 100]} Hundred")
        n %= 100
    if n >= 20:
        parts.append(TENS[n // 10] + (f"-{ONES[n % 10]}" if n % 10 else ""))
    elif n:
        parts.append(ONES[n])
    return " ".join(parts)


def amount_in_words(n: int) -> str:
    parts = []
    for value, label in [(1_000_000, "Million"), (1_000, "Thousand")]:
        if n >= value:
            parts.append(f"{_under_thousand(n // value)} {label}")
            n %= value
    if n:
        parts.append(_under_thousand(n))
    return " ".join(parts)


def truth_fields(spec: dict) -> dict:
    is_entity = spec["type"] in {"trust", "llc", "corporation", "partnership"}
    signed = spec.get("signed", True)
    return {
        "investor_name": spec["name"],
        "investor_type": spec["type"],
        "commitment_amount_figures": float(spec["amount"]),
        "commitment_amount_words_value": float(spec.get("words_amount", spec["amount"])),
        "us_person": spec["us"],
        "accreditation_basis": spec["basis"],
        "tax_form": spec["form"],
        "signed": signed,
        "signatory_name": spec["signer"] if signed else None,
        "signatory_title": (spec.get("title") if is_entity else None) if signed else None,
        "signature_date": "2026-11-14" if signed else None,
    }


class Page:
    def __init__(self, c: canvas.Canvas):
        self.c = c
        self.y = 10.2 * inch

    def text(self, s: str, size=10, font="Helvetica", gap=16, x=0.9 * inch):
        self.c.setFont(font, size)
        self.c.drawString(x, self.y, s)
        self.y -= gap

    def wrap(self, s: str, size=10, width=95, gap=14):
        words, line = s.split(), ""
        for w in words:
            if len(line) + len(w) + 1 > width:
                self.text(line, size=size, gap=gap)
                line = w
            else:
                line = f"{line} {w}".strip()
        if line:
            self.text(line, size=size, gap=gap)

    def space(self, h=10):
        self.y -= h

    def header(self, title: str, spec: dict, page_no: int):
        self.c.setFont("Helvetica", 8)
        self.c.drawString(0.9 * inch, 10.6 * inch, f"{FUND_NAME} | Subscription Booklet | {spec['id']}")
        self.c.drawRightString(7.6 * inch, 0.6 * inch, f"Page {page_no} of 4")
        self.text(title, size=14, font="Helvetica-Bold", gap=24)


def box(checked: bool) -> str:
    return "[X]" if checked else "[  ]"


def build(spec: dict, path: Path):
    c = canvas.Canvas(str(path), pagesize=LETTER)
    words_amount = spec.get("words_amount", spec["amount"])
    is_entity = spec["type"] in {"trust", "llc", "corporation", "partnership"}

    # Page 1: subscription agreement
    p = Page(c)
    p.header("Subscription Agreement", spec, 1)
    p.wrap(f"{FUND_NAME} (the \"Fund\") is a Delaware limited partnership. This Subscription "
           "Agreement is entered into by the undersigned investor (the \"Investor\") in connection "
           "with the offering of limited partnership interests in the Fund.")
    p.space()
    p.text("1. Investor", font="Helvetica-Bold")
    p.text(f"Legal name of Investor:  {spec['name']}")
    p.text("Type of Investor (check one):")
    for code, label in INVESTOR_TYPE_LABELS:
        p.text(f"{box(code == spec['type'])}  {label}", x=1.2 * inch, gap=14)
    p.space()
    p.text("2. Capital Commitment", font="Helvetica-Bold")
    p.wrap("The Investor hereby irrevocably subscribes for a limited partnership interest with a "
           "capital commitment in the amount set out below. In case of conflict between the amount "
           "in words and the amount in figures, the Fund may request clarification before acceptance.")
    p.text(f"Amount in words:  {amount_in_words(words_amount)} U.S. Dollars")
    p.text(f"Amount in figures:  US$ {spec['amount']:,.2f}")
    p.space()
    p.text("3. Acceptance", font="Helvetica-Bold")
    p.wrap("This subscription is not binding on the Fund until accepted by the General Partner. "
           "The General Partner may reject any subscription in whole or in part in its sole discretion.")
    c.showPage()

    # Page 2: investor questionnaire
    p = Page(c)
    p.header("Investor Questionnaire", spec, 2)
    p.text("Part A. Tax status", font="Helvetica-Bold")
    p.text(f"Is the Investor a U.S. person for U.S. federal income tax purposes?   "
           f"{box(spec['us'])} Yes   {box(not spec['us'])} No")
    p.text(f"Country of tax residence:  {spec['country']}")
    p.space()
    p.text("Part B. Accredited investor status", font="Helvetica-Bold")
    p.wrap("The Investor represents that it is an \"accredited investor\" as defined in Rule 501(a) "
           "of Regulation D because it meets the following criterion (check the one that applies):")
    group = "entity" if is_entity else "individual"
    for code, label in ACCREDITATION_OPTIONS[group]:
        p.wrap(f"{box(code == spec['basis'])}  {label}")
    p.space()
    p.text("Part C. Anti-money laundering", font="Helvetica-Bold")
    p.wrap("The Investor confirms that the funds used for this investment are not derived from any "
           "unlawful activity and agrees to provide additional information on request.")
    c.showPage()

    # Page 3: tax documentation
    p = Page(c)
    p.header("Tax Documentation", spec, 3)
    p.wrap("Investors must enclose the applicable IRS form: Form W-9 for U.S. persons, Form W-8BEN "
           "for non-U.S. individuals, and Form W-8BEN-E for non-U.S. entities.")
    p.space()
    if spec["form"] == "none":
        p.text("Enclosed form:  (none enclosed)", font="Helvetica-Bold")
    else:
        p.text(f"Enclosed form:  Form {spec['form']}", font="Helvetica-Bold")
        p.text(f"Name as shown on form:  {spec['name']}")
        tin = "XX-XXX4821" if is_entity else "XXX-XX-3307"
        p.text(f"Taxpayer identification number:  {tin if spec['form'] == 'W-9' else 'Foreign TIN on file'}")
        p.text(f"Country of residence on form:  {spec['country']}")
    c.showPage()

    # Page 4: signature page
    p = Page(c)
    p.header("Signature Page", spec, 4)
    p.wrap("IN WITNESS WHEREOF, the Investor has executed this Subscription Agreement as of the date "
           "written below, and agrees to be bound by the Limited Partnership Agreement of the Fund.")
    p.space(20)
    p.text(f"INVESTOR:  {spec['name']}", font="Helvetica-Bold")
    p.space(10)
    signed = spec.get("signed", True)
    c.setFont("Helvetica", 10)
    c.drawString(0.9 * inch, p.y, "Signature:")
    c.line(1.8 * inch, p.y - 2, 4.6 * inch, p.y - 2)
    if signed:
        c.setFont("Times-Italic", 15)
        c.drawString(1.9 * inch, p.y + 1, f"/s/ {spec['signer']}")
    p.space(26)
    p.text(f"Print name:  {spec['signer'] if signed else ''}")
    if is_entity:
        title = spec.get("title") if signed else None
        p.text(f"Title:  {title or ''}")
    p.text(f"Date:  {'November 14, 2026' if signed else ''}")
    c.showPage()
    c.save()


def main():
    OUT_DIR.mkdir(exist_ok=True)
    truth = {}
    for spec in SPECS:
        build(spec, OUT_DIR / f"{spec['id']}.pdf")
        fields = truth_fields(spec)
        truth[spec["id"]] = {
            "fields": fields,
            "flags": sorted(f.code for f in check(fields)),
        }
    (ROOT / "ground_truth.json").write_text(json.dumps(truth, indent=2))
    defective = sum(1 for t in truth.values() if t["flags"])
    print(f"Wrote {len(SPECS)} packets ({defective} with defects) to {OUT_DIR}")


if __name__ == "__main__":
    main()
