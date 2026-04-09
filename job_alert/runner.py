from __future__ import annotations

from .adapters import get_adapter, resolve_site
from .adapters.base import AdapterContext, create_session
from .config import load_config
from .db import Database
from .filters import effective_profile, match_job
from .logging_utils import get_logger
from .models import RunSummary, SiteConfig, SiteRunResult
from .notifier import EmailNotifier
from .utils import utc_now_iso


class JobAlertRunner:
    def __init__(self) -> None:
        self.logger = get_logger()
        self.db = Database()

    def _notifier(self, config):
        return EmailNotifier(
            smtp_host=config.email.smtp_host,
            smtp_port=config.email.smtp_port,
            smtp_username=config.email.smtp_username,
            smtp_app_password=config.email.smtp_app_password,
            sender_email=config.email.sender_email,
            sender_name=config.email.sender_name,
            recipient_emails=config.email.recipient_emails,
        )

    def test_site(self, site_id: str) -> SiteRunResult:
        config = load_config()
        site = next(site for site in config.sites if site.id == site_id)
        return self._run_site(site, config, preview=True)

    def run_all(self) -> RunSummary:
        config = load_config()
        notifier = self._notifier(config)
        summary = RunSummary(started_at=utc_now_iso())
        digest_jobs = []
        bootstrap_jobs = []

        for site in [site for site in config.sites if site.enabled]:
            result = self._run_site(site, config, preview=False)
            summary.site_results.append(result)
            if result.success:
                if site.alerts.immediate_new_jobs:
                    if result.bootstrap:
                        bootstrap_jobs.extend(result.matched_jobs)
                    else:
                        digest_jobs.extend(result.matched_jobs)
            elif site.alerts.alert_on_failure and notifier.is_configured():
                status_after = self.db.get_site_status(site.id)
                failure_count = int(status_after["consecutive_failures"]) if status_after else 1
                if failure_count <= 1 and not config.defaults.alert_on_first_failure:
                    continue
                payload = f"{site.id}|{result.warning}"
                if self.db.should_send_alert(f"failure::{site.id}", payload):
                    try:
                        summary.emails_sent.append(notifier.send_failure(site.label, result.warning))
                    except Exception as exc:
                        self.logger.exception("Failed to send failure email for %s", site.id)
                        self.db.log_run(site.id, "failure-email", str(exc))

        if notifier.is_configured() and bootstrap_jobs:
            try:
                summary.emails_sent.append(notifier.send_jobs_digest(bootstrap_jobs, bootstrap=True))
            except Exception as exc:
                self.logger.exception("Failed to send bootstrap digest")
                self.db.log_run(None, "email-failure", str(exc))

        if notifier.is_configured() and digest_jobs:
            try:
                summary.emails_sent.append(notifier.send_jobs_digest(digest_jobs, bootstrap=False))
            except Exception as exc:
                self.logger.exception("Failed to send digest")
                self.db.log_run(None, "email-failure", str(exc))

        summary.finished_at = utc_now_iso()
        return summary

    def _run_site(self, site: SiteConfig, config, *, preview: bool) -> SiteRunResult:
        session = create_session()
        resolved = resolve_site(site, config.defaults.request_timeout_seconds, self.logger)
        adapter = get_adapter(resolved.adapter_name)
        status_before = self.db.get_site_status(site.id)
        try:
            if resolved.adapter_name == "browser_links" and not config.defaults.browser_fallback:
                raise RuntimeError(f"Browser fallback is disabled, but {site.label} requires a browser-based adapter.")
            context = AdapterContext(
                site=site,
                source_url=resolved.resolved_url,
                timeout_seconds=config.defaults.request_timeout_seconds,
                logger=self.logger,
                session=session,
            )
            jobs = adapter.scrape(context)
            profile = effective_profile(site, config.profile)
            matched_jobs = []
            for job in jobs:
                matched, terms = match_job(job, profile, config.defaults.broad_match)
                if matched:
                    job.matched_terms = terms
                    matched_jobs.append(job)

            bootstrap = self.db.count_seen_jobs(site.id) == 0 and not preview
            new_matches = []
            if preview:
                new_matches = matched_jobs
            else:
                for job in jobs:
                    already_seen = self.db.has_seen_job(site.id, job.job_id)
                    self.db.upsert_job(job)
                    if matched_jobs and bootstrap and job in matched_jobs:
                        new_matches.append(job)
                    elif matched_jobs and not bootstrap and not already_seen and job in matched_jobs:
                        new_matches.append(job)

            self.db.update_site_status(
                site.id,
                site.label,
                adapter_name=adapter.name,
                resolved_url=resolved.resolved_url,
                success=True,
                error_message="",
            )
            if status_before and status_before["last_status"] == "failure":
                notifier = self._notifier(config)
                if notifier.is_configured():
                    payload = f"{site.id}|{adapter.name}|{resolved.resolved_url}"
                    if self.db.should_send_alert(f"recovery::{site.id}", payload):
                        try:
                            notifier.send_recovery(site.label, adapter.name)
                        except Exception:
                            self.logger.exception("Failed to send recovery email for %s", site.id)
            self.db.log_run(site.id, "success", f"{len(jobs)} jobs scraped via {adapter.name}", new_jobs_count=len(new_matches), bootstrap=bootstrap)
            return SiteRunResult(
                site_id=site.id,
                label=site.label,
                success=True,
                adapter_name=adapter.name,
                resolved_url=resolved.resolved_url,
                jobs_found=len(jobs),
                matched_jobs=new_matches,
                bootstrap=bootstrap,
                notes=resolved.notes,
            )
        except Exception as exc:
            message = str(exc)
            self.logger.exception("Site run failed: %s", site.id)
            self.db.update_site_status(
                site.id,
                site.label,
                adapter_name=resolved.adapter_name,
                resolved_url=resolved.resolved_url,
                success=False,
                error_message=message,
            )
            self.db.log_run(site.id, "failure", message)
            return SiteRunResult(
                site_id=site.id,
                label=site.label,
                success=False,
                adapter_name=resolved.adapter_name,
                resolved_url=resolved.resolved_url,
                warning=message,
                notes=resolved.notes,
            )
