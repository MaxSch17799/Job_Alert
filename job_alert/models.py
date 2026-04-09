from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class KeywordProfile:
    include_any: list[str] = field(default_factory=list)
    exclude_any: list[str] = field(default_factory=list)
    location_any: list[str] = field(default_factory=list)
    contract_type_any: list[str] = field(default_factory=list)
    language_any: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SchedulerConfig:
    mode: str = "daily"
    interval: int = 1
    time: str = "08:00"
    weekdays: list[str] = field(default_factory=lambda: ["MON"])


@dataclass(slots=True)
class DefaultSettings:
    broad_match: bool = True
    alert_on_first_failure: bool = True
    browser_fallback: bool = True
    request_timeout_seconds: int = 30
    detail_fetch_enabled: bool = False


@dataclass(slots=True)
class EmailSecrets:
    sender_email: str = ""
    sender_name: str = "Job Alert"
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_app_password: str = ""
    recipient_emails: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SiteFilters:
    location_any: list[str] = field(default_factory=list)
    contract_type_any: list[str] = field(default_factory=list)
    language_any: list[str] = field(default_factory=list)


@dataclass(slots=True)
class AlertSettings:
    immediate_new_jobs: bool = True
    weekly_summary: bool = False
    monthly_summary: bool = False
    alert_on_failure: bool = True


@dataclass(slots=True)
class SiteUIConfig:
    advanced_expanded: bool = True


@dataclass(slots=True)
class SiteConfig:
    id: str
    label: str
    source_url: str
    type: str = "auto"
    enabled: bool = True
    use_profile_defaults: bool = True
    include_any: list[str] = field(default_factory=list)
    exclude_any: list[str] = field(default_factory=list)
    filters: SiteFilters = field(default_factory=SiteFilters)
    alerts: AlertSettings = field(default_factory=AlertSettings)
    ui: SiteUIConfig = field(default_factory=SiteUIConfig)


@dataclass(slots=True)
class AppConfig:
    profile: KeywordProfile
    scheduler: SchedulerConfig
    defaults: DefaultSettings
    email: EmailSecrets
    sites: list[SiteConfig]


@dataclass(slots=True)
class JobPosting:
    site_id: str
    job_id: str
    title: str
    url: str
    location: str = ""
    posted_text: str = ""
    summary_text: str = ""
    raw_hash: str = ""
    adapter_name: str = ""
    source_url: str = ""
    matched_terms: list[str] = field(default_factory=list)

    @property
    def combined_text(self) -> str:
        return " ".join(part for part in [self.title, self.location, self.posted_text, self.summary_text] if part)


@dataclass(slots=True)
class ResolvedSite:
    adapter_name: str
    resolved_url: str
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SiteRunResult:
    site_id: str
    label: str
    success: bool
    adapter_name: str = ""
    resolved_url: str = ""
    jobs_found: int = 0
    matched_jobs: list[JobPosting] = field(default_factory=list)
    bootstrap: bool = False
    warning: str = ""
    notes: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RunSummary:
    started_at: str
    finished_at: str = ""
    site_results: list[SiteRunResult] = field(default_factory=list)
    emails_sent: list[str] = field(default_factory=list)

    def render_text(self) -> str:
        lines = [f"Run started: {self.started_at}"]
        if self.finished_at:
            lines.append(f"Run finished: {self.finished_at}")
        for result in self.site_results:
            status = "OK" if result.success else "FAIL"
            lines.append(
                f"[{status}] {result.label} | adapter={result.adapter_name or '-'} | "
                f"jobs={result.jobs_found} | matched={len(result.matched_jobs)}"
            )
            if result.warning:
                lines.append(f"  warning: {result.warning}")
        if self.emails_sent:
            lines.append("Emails sent:")
            for email_desc in self.emails_sent:
                lines.append(f"  - {email_desc}")
        return "\n".join(lines)


def dataclass_to_plain(obj: Any) -> Any:
    if hasattr(obj, "__dataclass_fields__"):
        return {
            name: dataclass_to_plain(getattr(obj, name))
            for name in obj.__dataclass_fields__.keys()
        }
    if isinstance(obj, list):
        return [dataclass_to_plain(item) for item in obj]
    return obj
