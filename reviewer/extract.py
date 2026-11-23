"""Read a subscription packet with Claude and return structured fields with evidence.

The model reads the PDF and reports what is written, with a short verbatim quote and
page number for each field. Code then checks every quote against the PDF text
("grounding"); a field without a grounded quote is sent to the human reviewer.
"""

import base64
import json
import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal, Optional

import anthropic
from pydantic import BaseModel, Field
from pypdf import PdfReader

MODEL = os.environ.get("REVIEWER_MODEL", "claude-opus-5-5")
EFFORT = os.environ.get("REVIEWER_EFFORT", "medium")
# Claude Opus 5.5 list price, USD per million tokens (input, output).
PRICE_PER_MTOK = {"claude-opus-5-5": (4.0, 20.0), "claude-sonnet-5-5": (2.0, 10.0),
                  "claude-haiku-5-5": (0.10, 0.50)}

SYSTEM_PROMPT = """You review subscription booklets for a private fund on behalf of a fund administrator.
Report what the document actually says. Do not infer or fill gaps: if something is blank,
missing or ambiguous, return null and list the field in uncertain_fields.

How to read the booklet:
- A checkbox marked [X] is selected; [  ] is not selected.
- The commitment appears twice. Read the amount in figures and, separately, convert the amount
  written in words into a number yourself. Never copy one into the other; they may disagree.
- "signed" is true only if a signature mark appears on the signature line. A printed name or
  a blank line is not a signature.
- tax_form is the form actually enclosed on the tax documentation page, or "none".
- signature_date uses YYYY-MM-DD.
- A field that does not apply to this investor (for example a signatory title for an individual)
  is null, not uncertain. Use uncertain_fields only when the document is unclear or contradicts itself.

For every field you fill, add one evidence item: the field name, the 1-indexed page number, and a
short quote copied character for character from that page (under 15 words)."""


class Evidence(BaseModel):
    field: str
    page: int
    quote: str


class Extraction(BaseModel):
    investor_name: str
    investor_type: Literal["individual", "joint", "ira", "trust", "llc", "corporation", "partnership"]
    commitment_amount_figures: Optional[float]
    commitment_amount_words: Optional[str]
    commitment_amount_words_value: Optional[float]
    us_person: Optional[bool]
    accreditation_basis: Optional[
        Literal["income", "net_worth", "license", "entity_assets", "all_owners_accredited"]]
    tax_form: Literal["W-9", "W-8BEN", "W-8BEN-E", "none"]
    signed: bool
    signatory_name: Optional[str]
    signatory_title: Optional[str]
    signature_date: Optional[str]
    evidence: list[Evidence] = Field(default_factory=list)
    uncertain_fields: list[str] = Field(default_factory=list)


FIELD_NAMES = [n for n in Extraction.model_fields if n not in ("evidence", "uncertain_fields")]


class ExtractionRefused(Exception):
    pass


@dataclass
class Result:
    fields: dict
    evidence: list[dict]
    grounded: dict[str, bool]
    needs_review: list[str]
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_s: float
    model: str
    raw: dict = field(default_factory=dict)


def page_texts(pdf_path: Path) -> list[str]:
    return [p.extract_text() or "" for p in PdfReader(str(pdf_path)).pages]


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip().lower()


def ground(evidence: list[Evidence], pages: list[str]) -> dict[str, bool]:
    """A field is grounded when at least one of its quotes appears on the cited page."""
    grounded: dict[str, bool] = {}
    for ev in evidence:
        ok = 1 <= ev.page <= len(pages) and _norm(ev.quote) in _norm(pages[ev.page - 1])
        grounded[ev.field] = grounded.get(ev.field, False) or ok
    return grounded


BACKEND = os.environ.get("REVIEWER_BACKEND", "api")  # "api" or "claude-code"


def _via_claude_code(pdf_path: Path) -> tuple[Extraction, int, int, float, str, float]:
    """Run the same prompt and schema through the Claude Code CLI (uses a Claude subscription,
    no API key). MCP servers, skills and user settings are switched off so the context stays
    close to a plain API call; the reported cost is Claude Code's list-price estimate."""
    pdf_path = Path(pdf_path).resolve()
    cmd = [
        "claude", "-p",
        f"Read the PDF file {pdf_path} (all pages) and extract the fields from this subscription booklet.",
        "--output-format", "json",
        "--json-schema", json.dumps(Extraction.model_json_schema()),
        "--system-prompt", SYSTEM_PROMPT,
        "--model", MODEL, "--effort", EFFORT,
        "--tools", "Read", "--allowedTools", "Read",
        "--no-session-persistence", "--strict-mcp-config", "--disable-slash-commands",
        "--setting-sources", "",
    ]
    start = time.perf_counter()
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=pdf_path.parent, timeout=600)
    latency = time.perf_counter() - start
    try:
        out = json.loads(proc.stdout)
    except json.JSONDecodeError:
        raise RuntimeError(f"claude CLI failed: {proc.stderr.strip() or proc.stdout[:300]}")
    if out.get("is_error") or not out.get("structured_output"):
        raise RuntimeError(f"claude CLI returned no structured output: {str(out.get('result'))[:300]}")
    usage = out.get("usage", {})
    tokens_in = (usage.get("input_tokens", 0) + usage.get("cache_creation_input_tokens", 0)
                 + usage.get("cache_read_input_tokens", 0))
    model = next(iter(out.get("modelUsage", {})), MODEL) + " (via Claude Code)"
    return (Extraction.model_validate(out["structured_output"]), tokens_in,
            usage.get("output_tokens", 0), float(out.get("total_cost_usd", 0.0)), model, latency)


def _via_api(pdf_path: Path, client) -> tuple[Extraction, int, int, float, str, float]:
    client = client or anthropic.Anthropic()
    pdf_b64 = base64.standard_b64encode(Path(pdf_path).read_bytes()).decode()

    start = time.perf_counter()
    response = client.beta.messages.parse(
        model=MODEL,
        max_tokens=16000,
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_config={"effort": EFFORT},
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": [
                {"type": "document",
                 "source": {"type": "base64", "media_type": "application/pdf", "data": pdf_b64}},
                {"type": "text", "text": "Extract the fields from this subscription booklet."},
            ],
        }],
        output_format=Extraction,
    )
    latency = time.perf_counter() - start

    if response.stop_reason == "refusal":
        raise ExtractionRefused(str(response.stop_details))
    usage = response.usage
    in_price, out_price = PRICE_PER_MTOK.get(response.model, PRICE_PER_MTOK["claude-opus-5-5"])
    cost = (usage.input_tokens * in_price + usage.output_tokens * out_price) / 1_000_000
    return (response.parsed_output, usage.input_tokens, usage.output_tokens, cost,
            response.model, latency)


def extract(pdf_path: Path, client: anthropic.Anthropic | None = None) -> Result:
    if BACKEND == "claude-code":
        parsed, tokens_in, tokens_out, cost, model, latency = _via_claude_code(pdf_path)
    else:
        parsed, tokens_in, tokens_out, cost, model, latency = _via_api(pdf_path, client)

    pages = page_texts(pdf_path)
    grounded = ground(parsed.evidence, pages)
    fields = parsed.model_dump(exclude={"evidence", "uncertain_fields"})
    # A filled field needs a grounded quote; null fields are judged by the rules instead.
    needs_review = sorted(
        {f for f in FIELD_NAMES if fields.get(f) not in (None, False) and not grounded.get(f)}
        | set(parsed.uncertain_fields) & set(FIELD_NAMES)
    )

    return Result(
        fields=fields,
        evidence=[e.model_dump() for e in parsed.evidence],
        grounded=grounded,
        needs_review=needs_review,
        input_tokens=tokens_in,
        output_tokens=tokens_out,
        cost_usd=cost,
        latency_s=latency,
        model=model,
        raw=parsed.model_dump(),
    )
