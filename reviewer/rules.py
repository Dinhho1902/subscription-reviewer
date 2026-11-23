"""Deterministic checks run on extracted fields.

Design choice: the model only reads the document. Every pass/fail decision is made
here, in plain code, so a reviewer (or a regulator) can see exactly why a packet
was flagged.
"""

from dataclasses import dataclass

from .fund_terms import ENTITY_TYPES, MINIMUM_COMMITMENT_USD, expected_tax_form

CRITICAL = "critical"
WARNING = "warning"


@dataclass
class Flag:
    code: str
    severity: str
    message: str
    fields: list[str]


def check(fields: dict) -> list[Flag]:
    flags: list[Flag] = []

    figures = fields.get("commitment_amount_figures")
    words = fields.get("commitment_amount_words_value")

    if not fields.get("signed"):
        flags.append(Flag("MISSING_SIGNATURE", CRITICAL,
                          "The signature page is not signed.", ["signed"]))

    if figures is not None and words is not None and abs(figures - words) > 0.5:
        flags.append(Flag("AMOUNT_MISMATCH", CRITICAL,
                          f"Commitment in figures (${figures:,.0f}) does not match the amount "
                          f"written in words (${words:,.0f}).",
                          ["commitment_amount_figures", "commitment_amount_words_value"]))

    amount = figures if figures is not None else words
    if amount is not None and amount < MINIMUM_COMMITMENT_USD:
        flags.append(Flag("BELOW_MINIMUM", CRITICAL,
                          f"Commitment ${amount:,.0f} is below the fund minimum of "
                          f"${MINIMUM_COMMITMENT_USD:,.0f}.", ["commitment_amount_figures"]))

    if not fields.get("accreditation_basis"):
        flags.append(Flag("NO_ACCREDITATION", CRITICAL,
                          "No accredited-investor basis is selected in the questionnaire.",
                          ["accreditation_basis"]))

    investor_type = fields.get("investor_type")
    us_person = fields.get("us_person")
    tax_form = fields.get("tax_form")
    if investor_type and us_person is not None:
        expected = expected_tax_form(investor_type, us_person)
        if tax_form != expected:
            flags.append(Flag("TAX_FORM_MISMATCH", CRITICAL,
                              f"Expected {expected} for this investor, found {tax_form or 'no form'}.",
                              ["tax_form", "investor_type", "us_person"]))

    if investor_type in ENTITY_TYPES and fields.get("signed") and not fields.get("signatory_title"):
        flags.append(Flag("MISSING_SIGNATORY_TITLE", WARNING,
                          "An entity investor signed without stating the signatory's title.",
                          ["signatory_title"]))

    return flags
