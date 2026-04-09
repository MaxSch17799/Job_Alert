from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Protocol

import requests

from ..models import JobPosting, SiteConfig
from ..utils import DEFAULT_USER_AGENT, absolute_url


@dataclass(slots=True)
class AdapterContext:
    site: SiteConfig
    source_url: str
    timeout_seconds: int
    logger: object
    session: requests.Session


class JobAdapter(Protocol):
    name: str

    def scrape(self, context: AdapterContext) -> list[JobPosting]:
        ...


def create_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": DEFAULT_USER_AGENT})
    return session


def raw_hash(*parts: str) -> str:
    joined = "||".join(parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def posting(
    *,
    site_id: str,
    adapter_name: str,
    source_url: str,
    job_id: str,
    title: str,
    url: str,
    location: str = "",
    posted_text: str = "",
    summary_text: str = "",
) -> JobPosting:
    return JobPosting(
        site_id=site_id,
        job_id=job_id,
        title=title.strip(),
        url=url.strip(),
        location=location.strip(),
        posted_text=posted_text.strip(),
        summary_text=summary_text.strip(),
        raw_hash=raw_hash(job_id, title, url, location, posted_text, summary_text),
        adapter_name=adapter_name,
        source_url=source_url,
    )


def normalize_href(base_url: str, href: str) -> str:
    return absolute_url(base_url, href)

