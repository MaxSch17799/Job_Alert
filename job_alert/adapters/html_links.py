from __future__ import annotations

import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .base import AdapterContext, normalize_href, posting

BLOCKLIST = (
    "linkedin",
    "facebook",
    "instagram",
    "youtube",
    "twitter",
    "x.com",
    "privacy",
    "imprint",
    "cookie",
    "kontakt",
    "contact",
    "mailto:",
    "jobabo",
    ".pdf",
    "/feed",
)

TITLE_BLOCKLIST = (
    "skip to content",
    "all jobs",
    "find your path",
    "jobs overview",
)

TITLE_HINTS = (
    "engineer",
    "systems",
    "specialist",
    "analyst",
    "manager",
    "scientist",
    "operations",
    "electrical",
    "avionics",
    "mission",
    "ground",
    "test",
    "integration",
    "quality",
    "propulsion",
    "technician",
)


class HtmlLinksAdapter:
    name = "html_links"

    def _score(self, text: str, href: str) -> int:
        lowered_href = href.casefold()
        lowered_text = text.casefold()
        if not text or len(text) < 4:
            return -10
        if any(blocked == lowered_text or blocked in lowered_text for blocked in TITLE_BLOCKLIST):
            return -10
        if any(item in lowered_href for item in BLOCKLIST):
            return -10
        score = 0
        if any(piece in lowered_href for piece in ("/job/", "/jobs/", "job-opportunities", "careersite", "position", "vacan", "stellen")):
            score += 4
        if any(hint in lowered_text for hint in TITLE_HINTS):
            score += 2
        if len(text) > 180:
            score -= 2
        if re.search(r"\b(job|position|vacancy|opening|engineer|manager|specialist)\b", lowered_text):
            score += 2
        return score

    def scrape(self, context: AdapterContext):
        response = context.session.get(context.source_url, timeout=context.timeout_seconds)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        base_host = urlparse(context.source_url).netloc
        source_root = context.source_url.rstrip("/")
        jobs = []
        seen_ids: set[str] = set()
        for link in soup.select("a[href]"):
            href = link.get("href", "").strip()
            title = link.get_text(" ", strip=True).replace("\ufeff", "").strip()
            if not href or not title:
                continue
            absolute = normalize_href(context.source_url, href)
            if not absolute:
                continue
            if "#" in absolute and absolute.split("#", 1)[0].rstrip("/") == source_root:
                continue
            parsed = urlparse(absolute)
            if parsed.netloc and parsed.netloc != base_host and "career" not in parsed.netloc and "jobs" not in parsed.netloc:
                continue
            if absolute.rstrip("/") == source_root and title.casefold() in TITLE_BLOCKLIST:
                continue
            score = self._score(title, absolute)
            if score < 4:
                continue
            job_id = absolute.rstrip("/").split("/")[-1] or title
            if job_id in seen_ids:
                continue
            seen_ids.add(job_id)
            parent_text = link.parent.get_text(" ", strip=True) if link.parent else ""
            jobs.append(
                posting(
                    site_id=context.site.id,
                    adapter_name=self.name,
                    source_url=context.source_url,
                    job_id=job_id,
                    title=title,
                    url=absolute,
                    summary_text=parent_text[:260],
                )
            )
        return jobs
