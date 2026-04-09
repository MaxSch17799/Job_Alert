from __future__ import annotations

from bs4 import BeautifulSoup

from .base import AdapterContext, normalize_href, posting


class OnlyfyAdapter:
    name = "onlyfy"

    def _ajax_url(self, base_url: str, page: int) -> str:
        return f"{base_url.rstrip('/')}/candidate/job/ajax_list?display_length=50&page={page}&sort=date&sort_dir=DESC&search="

    def scrape(self, context: AdapterContext):
        jobs = []
        page = 1
        while True:
            response = context.session.get(self._ajax_url(context.source_url, page), timeout=context.timeout_seconds)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")
            rows = soup.select("div.row.row-table")
            for row in rows:
                link = row.select_one("strong.job-title a")
                if not link:
                    continue
                title = link.get_text(" ", strip=True)
                href = link.get("href", "")
                cells = [cell.get_text(" ", strip=True) for cell in row.select("div.cell-table div.inner")]
                deadline = cells[1] if len(cells) > 1 else ""
                posted = cells[2] if len(cells) > 2 else ""
                job_id = href.rstrip("/").split("/")[-1]
                jobs.append(
                    posting(
                        site_id=context.site.id,
                        adapter_name=self.name,
                        source_url=context.source_url,
                        job_id=job_id,
                        title=title,
                        url=normalize_href(context.source_url, href),
                        posted_text=posted,
                        summary_text=f"Deadline: {deadline}" if deadline else "",
                    )
                )
            if not soup.select_one("a.infinite-next"):
                break
            page += 1
        return jobs
