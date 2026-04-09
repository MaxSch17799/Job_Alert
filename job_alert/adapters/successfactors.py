from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup

from .base import AdapterContext, normalize_href, posting

BLOCKLIST = (
    "privacy",
    "cookie",
    "mailto:",
    "forgotpassword",
    "createaccount",
)

LOGIN_MARKERS = (
    "career opportunities: sign in",
    "id=\"signintitlecontainer\"",
    "loginflowrequired",
)


class SuccessFactorsAdapter:
    name = "successfactors"

    def scrape(self, context: AdapterContext):
        response = context.session.get(context.source_url, timeout=context.timeout_seconds)
        response.raise_for_status()
        body = response.text.casefold()
        if any(marker in body for marker in LOGIN_MARKERS):
            raise RuntimeError("This SuccessFactors board requires sign-in and does not expose a public job list.")

        soup = BeautifulSoup(response.text, "html.parser")
        jobs = []
        seen_ids: set[str] = set()
        for link in soup.select("a[href]"):
            href = link.get("href", "").strip()
            title = link.get_text(" ", strip=True).replace("\ufeff", "").strip()
            if not href or not title:
                continue
            absolute = normalize_href(response.url, href)
            lowered = absolute.casefold()
            if any(blocked in lowered for blocked in BLOCKLIST):
                continue
            if "jobreqid" not in lowered and "jobdetail" not in lowered and "jobprofile" not in lowered and "careersection" not in lowered:
                continue

            parsed = urlparse(absolute)
            query = parse_qs(parsed.query)
            job_id = (
                (query.get("jobReqId") or [None])[0]
                or (query.get("jobreqid") or [None])[0]
                or parsed.path.rstrip("/").split("/")[-1]
                or title
            )
            if job_id in seen_ids:
                continue
            seen_ids.add(job_id)
            jobs.append(
                posting(
                    site_id=context.site.id,
                    adapter_name=self.name,
                    source_url=context.source_url,
                    job_id=str(job_id),
                    title=title,
                    url=absolute,
                )
            )

        if not jobs:
            raise RuntimeError("No public job postings were detected on the SuccessFactors board.")
        return jobs
