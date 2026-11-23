"""Deterministic checks run on extracted fields.

Design choice: the model only reads the document. Every pass/fail decision is made
here, in plain code, so a reviewer (or a regulator) can see exactly why a packet
was flagged.
"""

from dataclasses import dataclass

from .fund_terms import ENTITY_TYPES, INDIVIDUAL_TYPES, MINIMUM_COMMITMENT_USD, expected_tax_form

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
                          "The signature page has not been signed.", ["signed"]))

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
                          "None of the accredited-investor boxes in the questionnaire is ticked.",
                          ["accreditation_basis"]))

    investor_type = fields.get("investor_type")
    us_person = fields.get("us_person")
    tax_form = fields.get("tax_form")
    if investor_type and us_person is not None:
        expected = expected_tax_form(investor_type, us_person)
        if tax_form != expected:
            who = ("a U.S. investor" if us_person else
                   "a non-U.S. individual" if investor_type in INDIVIDUAL_TYPES else "a non-U.S. entity")
            found = f"Form {tax_form}" if tax_form and tax_form != "none" else "no tax form"
            flags.append(Flag("TAX_FORM_MISMATCH", CRITICAL,
                              f"{who[0].upper() + who[1:]} must send Form {expected}; this booklet has {found}.",
                              ["tax_form", "investor_type", "us_person"]))

    if investor_type in ENTITY_TYPES and fields.get("signed") and not fields.get("signatory_title"):
        flags.append(Flag("MISSING_SIGNATORY_TITLE", WARNING,
                          "The investor is a company, trust or partnership, but the signer's title "
                          "(for example Director or Trustee) is missing.",
                          ["signatory_title"]))

    return flags
