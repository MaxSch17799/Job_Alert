from __future__ import annotations

from urllib.parse import urlparse

from .base import AdapterContext, posting


class BrowserLinksAdapter:
    name = "browser_links"

    def scrape(self, context: AdapterContext):
        try:
            from playwright.sync_api import sync_playwright
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(
                "Playwright is not installed. Run: .venv\\Scripts\\python.exe -m pip install -r requirements.txt"
            ) from exc

        source_url = context.source_url
        jobs = []
        seen_ids: set[str] = set()
        base_host = urlparse(source_url).netloc
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(user_agent=context.session.headers.get("User-Agent", "Mozilla/5.0"))
            page.goto(source_url, wait_until="domcontentloaded", timeout=max(60000, context.timeout_seconds * 1000))
            page.wait_for_timeout(6000)
            anchors = page.evaluate(
                """
                () => Array.from(document.querySelectorAll('a[href]')).map(anchor => ({
                    href: anchor.href,
                    text: (anchor.innerText || anchor.textContent || '').trim(),
                    parentText: anchor.parentElement ? anchor.parentElement.innerText || '' : ''
                }))
                """
            )
            browser.close()

        for item in anchors:
            href = (item.get("href") or "").strip()
            title = (item.get("text") or "").strip()
            if not href or not title or len(title) < 4:
                continue
            lowered_href = href.casefold()
            if any(block in lowered_href for block in ("linkedin", "facebook", "youtube", "instagram", "privacy", "cookie", "mailto:", ".pdf")):
                continue
            if not any(token in lowered_href for token in ("/job/", "/jobs/", "job-opportunities", "careersite", "vacan", "position", "search")):
                continue
            parsed = urlparse(href)
            if parsed.netloc and parsed.netloc != base_host and "career" not in parsed.netloc and "jobs" not in parsed.netloc:
                continue
            job_id = href.rstrip("/").split("/")[-1] or title
            if job_id in seen_ids:
                continue
            seen_ids.add(job_id)
            jobs.append(
                posting(
                    site_id=context.site.id,
                    adapter_name=self.name,
                    source_url=source_url,
                    job_id=job_id,
                    title=title,
                    url=href,
                    summary_text=(item.get("parentText") or "")[:260],
                )
            )
        return jobs
