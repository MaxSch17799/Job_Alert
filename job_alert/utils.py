from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin

ROOT_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT_DIR / "config.yaml"
SECRETS_PATH = ROOT_DIR / "secrets.yaml"
DB_PATH = ROOT_DIR / "job_alert.db"
LOG_DIR = ROOT_DIR / "logs"
LOG_PATH = LOG_DIR / "job_alert.log"
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def slugify(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-")
    return value.lower() or "site"


def normalize_text(value: str | None) -> str:
    if not value:
        return ""
    lowered = value.casefold()
    cleaned = unicodedata.normalize("NFKD", lowered)
    cleaned = cleaned.encode("ascii", "ignore").decode("ascii")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def unique_preserve(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value is None:
            continue
        stripped = value.strip()
        if not stripped:
            continue
        marker = stripped.casefold()
        if marker in seen:
            continue
        seen.add(marker)
        result.append(stripped)
    return result


def textarea_to_list(value: str | None) -> list[str]:
    if not value:
        return []
    pieces = re.split(r"[\r\n,]+", value)
    return unique_preserve(piece for piece in pieces if piece and piece.strip())


def list_to_textarea(values: Iterable[str]) -> str:
    return "\n".join(unique_preserve(values))


def absolute_url(base_url: str, href: str) -> str:
    return urljoin(base_url, href)


def ensure_logs_dir() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)

