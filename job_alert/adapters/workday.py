from __future__ import annotations

from urllib.parse import urlparse

from bs4 import BeautifulSoup

from .base import AdapterContext, posting


class WorkdayAdapter:
    name = "workday"

    def _endpoint_from_url(self, context: AdapterContext) -> str:
        source_url = context.source_url.rstrip("/")
        if "/wday/cxs/" in source_url:
            return source_url if source_url.endswith("/jobs") else f"{source_url}/jobs"

        parsed = urlparse(source_url)
        path_parts = [part for part in parsed.path.split("/") if part]
        if not path_parts:
            raise RuntimeError("Workday URL is missing the site path.")
        tenant = parsed.netloc.split(".")[0]
        site_id = path_parts[0]

        response = context.session.get(source_url, timeout=context.timeout_seconds)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        script_text = "\n".join(script.get_text(" ", strip=True) for script in soup.find_all("script"))
        if 'tenant: "' in script_text:
            tenant = script_text.split('tenant: "', 1)[1].split('"', 1)[0] or tenant
        if 'siteId: "' in script_text:
            site_id = script_text.split('siteId: "', 1)[1].split('"', 1)[0] or site_id
        return f"{parsed.scheme}://{parsed.netloc}/wday/cxs/{tenant}/{site_id}/jobs"

    def scrape(self, context: AdapterContext):
        endpoint = self._endpoint_from_url(context)
        jobs = []
        offset = 0
        limit = 20
        total = None
        while total is None or offset < total:
            payload = {
                "limit": limit,
                "offset": offset,
                "searchText": "",
                "appliedFacets": {},
                "userPreferredLanguage": "en-US",
            }
            response = context.session.post(endpoint, json=payload, timeout=context.timeout_seconds)
            response.raise_for_status()
            data = response.json()
            total = int(data.get("total", 0))
            postings = data.get("jobPostings", []) or []
            for item in postings:
                external_path = item.get("externalPath", "")
                bullet_fields = item.get("bulletFields", []) or []
                job_code = str(bullet_fields[0]) if bullet_fields else ""
                if not job_code:
                    job_code = external_path.rsplit("/", 1)[-1] or item.get("title", "workday-job")
                jobs.append(
                    posting(
                        site_id=context.site.id,
                        adapter_name=self.name,
                        source_url=context.source_url,
                        job_id=job_code,
                        title=item.get("title", "Untitled role"),
                        url=f"{urlparse(context.source_url).scheme}://{urlparse(context.source_url).netloc}{external_path}",
                        location=item.get("locationsText", ""),
                        posted_text=item.get("postedOn", ""),
                        summary_text=" | ".join(bullet_fields[1:]) if len(bullet_fields) > 1 else "",
                    )
                )
            offset += limit
            if not postings:
                break
        return jobs

