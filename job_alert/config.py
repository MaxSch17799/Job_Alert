from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .models import (
    AlertSettings,
    AppConfig,
    DefaultSettings,
    EmailSecrets,
    KeywordProfile,
    SchedulerConfig,
    SiteConfig,
    SiteFilters,
    SiteUIConfig,
    dataclass_to_plain,
)
from .utils import CONFIG_PATH, SECRETS_PATH, slugify


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {path}")
    return data


def _write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")


def _positive_int(raw_value: str | int | None, default: int) -> int:
    try:
        value = int(str(raw_value).strip() or default)
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


def ensure_config_files() -> None:
    if not CONFIG_PATH.exists():
        CONFIG_PATH.write_text(CONFIG_PATH.with_name("config.example.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    if not SECRETS_PATH.exists():
        SECRETS_PATH.write_text(SECRETS_PATH.with_name("secrets.example.yaml").read_text(encoding="utf-8"), encoding="utf-8")


def _site_from_plain(item: dict[str, Any]) -> SiteConfig:
    return SiteConfig(
        id=item.get("id") or slugify(item.get("label") or item.get("source_url") or "site"),
        label=item.get("label") or item.get("id") or "Site",
        source_url=item.get("source_url", "").strip(),
        type=item.get("type", "auto"),
        enabled=bool(item.get("enabled", True)),
        use_profile_defaults=bool(item.get("use_profile_defaults", True)),
        include_any=list(item.get("include_any", []) or []),
        exclude_any=list(item.get("exclude_any", []) or []),
        filters=SiteFilters(**(item.get("filters", {}) or {})),
        alerts=AlertSettings(**(item.get("alerts", {}) or {})),
        ui=SiteUIConfig(**(item.get("ui", {}) or {})),
    )


def load_config() -> AppConfig:
    ensure_config_files()
    base = _read_yaml(CONFIG_PATH)
    secrets = _read_yaml(SECRETS_PATH)
    global_block = base.get("global", {}) or {}
    sites_block = base.get("sites", []) or []
    return AppConfig(
        profile=KeywordProfile(**(global_block.get("profile", {}) or {})),
        scheduler=SchedulerConfig(**(global_block.get("scheduler", {}) or {})),
        defaults=DefaultSettings(**(global_block.get("defaults", {}) or {})),
        email=EmailSecrets(**((secrets.get("email", {}) or {}))),
        sites=[_site_from_plain(item) for item in sites_block],
    )


def save_config(config: AppConfig) -> None:
    base_data = {
        "global": {
            "profile": dataclass_to_plain(config.profile),
            "scheduler": dataclass_to_plain(config.scheduler),
            "defaults": dataclass_to_plain(config.defaults),
        },
        "sites": [dataclass_to_plain(site) for site in config.sites],
    }
    secrets_data = {
        "email": dataclass_to_plain(config.email),
    }
    _write_yaml(CONFIG_PATH, base_data)
    _write_yaml(SECRETS_PATH, secrets_data)


def update_profile_from_form(config: AppConfig, form: dict[str, str], list_parser) -> None:
    config.profile.include_any = list_parser(form.get("profile_include_any"))
    config.profile.exclude_any = list_parser(form.get("profile_exclude_any"))
    config.profile.location_any = list_parser(form.get("profile_location_any"))
    config.profile.contract_type_any = list_parser(form.get("profile_contract_type_any"))
    config.profile.language_any = list_parser(form.get("profile_language_any"))
    config.scheduler.mode = form.get("scheduler_mode", "daily").strip() or "daily"
    config.scheduler.interval = _positive_int(form.get("scheduler_interval"), 1)
    config.scheduler.time = form.get("scheduler_time", "08:00").strip() or "08:00"
    config.scheduler.weekdays = list_parser(form.get("scheduler_weekdays")) or ["MON"]
    config.defaults.broad_match = form.get("defaults_broad_match") == "on"
    config.defaults.alert_on_first_failure = form.get("defaults_alert_on_first_failure") == "on"
    config.defaults.browser_fallback = form.get("defaults_browser_fallback") == "on"
    timeout_value = form.get("defaults_request_timeout_seconds", "30").strip() or "30"
    config.defaults.request_timeout_seconds = _positive_int(timeout_value, 30)
    config.defaults.detail_fetch_enabled = form.get("defaults_detail_fetch_enabled") == "on"
    config.email.sender_email = form.get("email_sender_email", "").strip()
    config.email.sender_name = form.get("email_sender_name", "Job Alert").strip() or "Job Alert"
    config.email.smtp_host = form.get("email_smtp_host", "smtp.gmail.com").strip() or "smtp.gmail.com"
    config.email.smtp_port = _positive_int(form.get("email_smtp_port"), 587)
    config.email.smtp_username = form.get("email_smtp_username", "").strip()
    config.email.smtp_app_password = form.get("email_smtp_app_password", "").strip()
    config.email.recipient_emails = list_parser(form.get("email_recipient_emails"))


def make_site_from_form(form: dict[str, str], list_parser) -> SiteConfig:
    site_id = slugify(form.get("id", "").strip() or form.get("label", "").strip() or form.get("source_url", "").strip())
    return SiteConfig(
        id=site_id,
        label=form.get("label", "").strip() or site_id,
        source_url=form.get("source_url", "").strip(),
        type=form.get("type", "auto").strip() or "auto",
        enabled=form.get("enabled") == "on",
        use_profile_defaults=form.get("use_profile_defaults") == "on",
        include_any=list_parser(form.get("include_any")),
        exclude_any=list_parser(form.get("exclude_any")),
        filters=SiteFilters(
            location_any=list_parser(form.get("location_any")),
            contract_type_any=list_parser(form.get("contract_type_any")),
            language_any=list_parser(form.get("language_any")),
        ),
        alerts=AlertSettings(
            immediate_new_jobs=form.get("immediate_new_jobs") == "on",
            weekly_summary=form.get("weekly_summary") == "on",
            monthly_summary=form.get("monthly_summary") == "on",
            alert_on_failure=form.get("alert_on_failure") == "on",
        ),
        ui=SiteUIConfig(
            advanced_expanded=form.get("advanced_expanded") == "on",
        ),
    )
