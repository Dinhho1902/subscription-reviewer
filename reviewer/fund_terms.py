"""Terms of the (fictional) fund that every subscription packet is checked against.

All names and numbers here are invented for the prototype.
"""

FUND_NAME = "Northwind Growth Fund III, L.P."
MINIMUM_COMMITMENT_USD = 250_000

INDIVIDUAL_TYPES = {"individual", "joint", "ira"}
ENTITY_TYPES = {"trust", "llc", "corporation", "partnership"}
INVESTOR_TYPES = sorted(INDIVIDUAL_TYPES | ENTITY_TYPES)

TAX_FORMS = ["W-9", "W-8BEN", "W-8BEN-E", "none"]


def expected_tax_form(investor_type: str, us_person: bool) -> str:
    """US persons file a W-9; non-US individuals a W-8BEN; non-US entities a W-8BEN-E."""
    if us_person:
        return "W-9"
    return "W-8BEN" if investor_type in INDIVIDUAL_TYPES else "W-8BEN-E"
