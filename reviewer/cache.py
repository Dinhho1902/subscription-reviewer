"""Cache extraction results by file hash so a demo never pays twice for the same PDF."""

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from .extract import Result, extract

CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"


def file_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def load(digest: str) -> Result | None:
    path = CACHE_DIR / f"{digest}.json"
    if not path.exists():
        return None
    return Result(**json.loads(path.read_text()))


def save(digest: str, result: Result) -> None:
    CACHE_DIR.mkdir(exist_ok=True)
    (CACHE_DIR / f"{digest}.json").write_text(json.dumps(asdict(result), indent=2))


def cached_extract(pdf_path: Path, client=None, refresh: bool = False) -> tuple[Result, bool]:
    """Return (result, from_cache)."""
    digest = file_hash(Path(pdf_path).read_bytes())
    if not refresh and (hit := load(digest)):
        return hit, True
    result = extract(pdf_path, client)
    save(digest, result)
    return result, False
