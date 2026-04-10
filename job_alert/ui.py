from __future__ import annotations

from textwrap import dedent
from typing import Any

import yaml
from flask import Flask, flash, jsonify, redirect, render_template, request, url_for

from .config import (
    load_config,
    make_site_from_form,
    save_config,
    update_profile_from_form,
    update_setup_from_form,
)
from .db import Database
from .models import SiteConfig
from .notifier import EmailNotifier
from .runner import JobAlertRunner
from .scheduler import SchedulerService
from .utils import list_to_textarea, textarea_to_list


PROFILE_YAML_EXAMPLE = dedent(
    """\
    include_any:
      - systems engineer
      - electrical engineer
      - mission operations
    exclude_any:
      - software engineer
      - marketing
    location_any:
      - hamburg
      - darmstadt
    contract_type_any:
      - full-time
      - permanent
    language_any:
      - english
      - german
    """
)


SITE_YAML_EXAMPLE = dedent(
    """\
    label: Example Site
    source_url: https://example.com/jobs
    type: auto
    enabled: true
    use_profile_defaults: true
    include_any:
      - systems engineer
      - avionics
    exclude_any:
      - software engineer
    location_any:
      - hamburg
    contract_type_any:
      - full-time
    language_any:
      - english
    alerts:
      immediate_new_jobs: true
      weekly_summary: false
      monthly_summary: false
      alert_on_failure: true
    """
)


PROFILE_AI_PROMPT = dedent(
    """\
    I need YAML for a local Windows job-alert tool.

    Context:
    - The tool monitors job websites and uses simple text matching.
    - Matching checks job title, location text, posted text, and a short summary scraped from the page.
    - `include_any` should be broad enough to avoid missing relevant jobs.
    - `exclude_any` should stay conservative and only block obvious no-go roles.
    - If CVs, old applications, liked job ads, or notes are attached, read them carefully and infer the wording that should be matched.
    - Think hard about synonyms, acronyms, recruiter wording, adjacent role titles, and company-specific phrasing.

    Return ONLY YAML in exactly this format:

    include_any:
      - keyword
    exclude_any:
      - keyword
    location_any:
      - location
    contract_type_any:
      - contract type
    language_any:
      - language

    Rules:
    - use lowercase
    - no comments
    - no markdown fences
    - if a section has no useful entries, return it as an empty list
    """
)


SITE_AI_PROMPT_TEMPLATE = dedent(
    """\
    I need YAML for one specific site in a local Windows job-alert tool.

    Site context:
    - label: {label}
    - source_url: {source_url}

    Matching context:
    - The tool uses simple text matching across job title, location text, posted text, and a short summary scraped from the site.
    - This YAML is for a single site override, so think about the wording likely to appear on this specific company or portal.
    - If CVs, favourite job ads, or notes are attached, read them carefully and infer the strongest site-specific terms.
    - Keep `include_any` broad enough to catch good jobs on this site.
    - Keep `exclude_any` conservative.

    Return ONLY YAML in exactly this format:

    label: {label}
    source_url: {source_url}
    type: auto
    enabled: true
    use_profile_defaults: true
    include_any:
      - keyword
    exclude_any:
      - keyword
    location_any:
      - location
    contract_type_any:
      - contract type
    language_any:
      - language
    alerts:
      immediate_new_jobs: true
      weekly_summary: false
      monthly_summary: false
      alert_on_failure: true

    Rules:
    - use lowercase for keywords and locations
    - no comments
    - no markdown fences
    - if a list has no useful entries, return it as an empty list
    """
)


def _coerce_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    lowered = str(value).strip().casefold()
    if lowered in {"1", "true", "yes", "y", "on"}:
        return True
    if lowered in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _coerce_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return textarea_to_list("\n".join(str(item) for item in value))
    return textarea_to_list(str(value))


def _build_site_ai_prompt(site: SiteConfig | None) -> str:
    label = site.label if site else "Example Site"
    source_url = site.source_url if site else "https://example.com/jobs"
    return SITE_AI_PROMPT_TEMPLATE.format(label=label, source_url=source_url)


def _apply_site_yaml(site: SiteConfig, payload: dict[str, Any]) -> None:
    if "label" in payload:
        site.label = str(payload.get("label") or site.label).strip() or site.label
    if "source_url" in payload:
        site.source_url = str(payload.get("source_url") or site.source_url).strip() or site.source_url
    if "type" in payload:
        site.type = str(payload.get("type") or site.type).strip() or site.type
    if "enabled" in payload:
        site.enabled = _coerce_bool(payload.get("enabled"), site.enabled)
    if "use_profile_defaults" in payload:
        site.use_profile_defaults = _coerce_bool(payload.get("use_profile_defaults"), site.use_profile_defaults)
    if "include_any" in payload:
        site.include_any = _coerce_list(payload.get("include_any"))
    if "exclude_any" in payload:
        site.exclude_any = _coerce_list(payload.get("exclude_any"))

    filters = payload.get("filters", {}) or {}
    if "location_any" in payload or "location_any" in filters:
        site.filters.location_any = _coerce_list(payload.get("location_any", filters.get("location_any")))
    if "contract_type_any" in payload or "contract_type_any" in filters:
        site.filters.contract_type_any = _coerce_list(payload.get("contract_type_any", filters.get("contract_type_any")))
    if "language_any" in payload or "language_any" in filters:
        site.filters.language_any = _coerce_list(payload.get("language_any", filters.get("language_any")))

    alerts = payload.get("alerts", {}) or {}
    for field_name in ("immediate_new_jobs", "weekly_summary", "monthly_summary", "alert_on_failure"):
        if field_name in payload or field_name in alerts:
            current = getattr(site.alerts, field_name)
            setattr(site.alerts, field_name, _coerce_bool(payload.get(field_name, alerts.get(field_name)), current))


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["SECRET_KEY"] = "job-alert-local-ui"

    @app.after_request
    def no_cache_headers(response):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

    @app.get("/")
    def index():
        config = load_config()
        db = Database()
        scheduler = SchedulerService()
        notifier = EmailNotifier(
            smtp_host=config.email.smtp_host,
            smtp_port=config.email.smtp_port,
            smtp_username=config.email.smtp_username,
            smtp_app_password=config.email.smtp_app_password,
            sender_email=config.email.sender_email,
            sender_name=config.email.sender_name,
            recipient_emails=config.email.recipient_emails,
        )
        status_map = {site.id: db.get_site_status(site.id) for site in config.sites}
        runs = db.recent_runs(40)
        scheduler_command = " ".join(scheduler.build_task_command(config.scheduler))
        scheduler_status = scheduler.query_status()
        active_tab = request.args.get("tab", "").strip() or (
            "setup" if not notifier.is_configured() or not scheduler_status["exists"] else "job-alerts"
        )
        latest_run = runs[0] if runs else None
        return render_template(
            "index.html",
            config=config,
            status_map=status_map,
            runs=runs,
            list_to_textarea=list_to_textarea,
            scheduler_command=scheduler_command,
            scheduler_status=scheduler_status,
            email_ready=notifier.is_configured(),
            active_tab=active_tab,
            latest_run=latest_run,
            profile_yaml_example=PROFILE_YAML_EXAMPLE,
            profile_ai_prompt=PROFILE_AI_PROMPT,
        )

    @app.post("/profile/save")
    def save_profile():
        config = load_config()
        update_profile_from_form(config, request.form, textarea_to_list)
        save_config(config)
        flash("Default keyword profile saved.", "success")
        return redirect(url_for("index", tab="profile"))

    @app.post("/setup/save")
    def save_setup():
        config = load_config()
        update_setup_from_form(config, request.form, textarea_to_list)
        save_config(config)
        flash("Setup settings saved.", "success")
        return redirect(url_for("index", tab="setup"))

    @app.post("/email/test")
    def test_email():
        config = load_config()
        notifier = EmailNotifier(
            smtp_host=config.email.smtp_host,
            smtp_port=config.email.smtp_port,
            smtp_username=config.email.smtp_username,
            smtp_app_password=config.email.smtp_app_password,
            sender_email=config.email.sender_email,
            sender_name=config.email.sender_name,
            recipient_emails=config.email.recipient_emails,
        )
        if not notifier.is_configured():
            flash("Email settings are incomplete. Fill in sender, SMTP username, app password, and recipient fields first.", "warning")
            return redirect(url_for("index", tab="setup"))
        try:
            description = notifier.send_test_message()
            flash(f"Test email sent: {description}", "success")
        except Exception as exc:
            flash(f"Test email failed: {exc}", "danger")
        return redirect(url_for("index", tab="setup"))

    @app.post("/profile/import")
    def import_profile():
        raw_yaml = request.form.get("profile_yaml", "").strip()
        if not raw_yaml:
            flash("Paste YAML before importing.", "warning")
            return redirect(url_for("index", tab="profile"))
        try:
            payload = yaml.safe_load(raw_yaml) or {}
            config = load_config()
            config.profile.include_any = list(payload.get("include_any", []) or [])
            config.profile.exclude_any = list(payload.get("exclude_any", []) or [])
            config.profile.location_any = list(payload.get("location_any", []) or [])
            config.profile.contract_type_any = list(payload.get("contract_type_any", []) or [])
            config.profile.language_any = list(payload.get("language_any", []) or [])
            save_config(config)
            flash("Profile YAML imported.", "success")
        except Exception as exc:
            flash(f"YAML import failed: {exc}", "danger")
        return redirect(url_for("index", tab="profile"))

    @app.get("/sites/new")
    def new_site():
        return render_template(
            "site_form.html",
            site=None,
            inherited=load_config().profile,
            list_to_textarea=list_to_textarea,
            site_yaml_example=SITE_YAML_EXAMPLE,
            site_ai_prompt=_build_site_ai_prompt(None),
        )

    @app.get("/sites/<site_id>")
    def edit_site(site_id: str):
        config = load_config()
        site = next((item for item in config.sites if item.id == site_id), None)
        if not site:
            flash("Site not found.", "danger")
            return redirect(url_for("index", tab="job-alerts"))
        return render_template(
            "site_form.html",
            site=site,
            inherited=config.profile,
            list_to_textarea=list_to_textarea,
            site_yaml_example=SITE_YAML_EXAMPLE,
            site_ai_prompt=_build_site_ai_prompt(site),
        )

    @app.post("/sites/save")
    def save_site():
        config = load_config()
        site = make_site_from_form(request.form, textarea_to_list)
        existing_index = next((index for index, item in enumerate(config.sites) if item.id == site.id), None)
        if existing_index is None:
            config.sites.append(site)
        else:
            config.sites[existing_index] = site
        save_config(config)
        flash(f"Saved site: {site.label}", "success")
        return redirect(url_for("index", tab="job-alerts"))

    @app.post("/sites/<site_id>/import-yaml")
    def import_site_yaml(site_id: str):
        raw_yaml = request.form.get("site_yaml", "").strip()
        if not raw_yaml:
            flash("Paste site YAML before importing.", "warning")
            return redirect(url_for("edit_site", site_id=site_id))
        try:
            payload = yaml.safe_load(raw_yaml) or {}
            if not isinstance(payload, dict):
                raise ValueError("Expected a YAML mapping for site import.")
            config = load_config()
            site = next((item for item in config.sites if item.id == site_id), None)
            if not site:
                flash("Site not found.", "danger")
                return redirect(url_for("index", tab="job-alerts"))
            _apply_site_yaml(site, payload)
            save_config(config)
            flash(f"Imported YAML into {site.label}.", "success")
        except Exception as exc:
            flash(f"Site YAML import failed: {exc}", "danger")
        return redirect(url_for("edit_site", site_id=site_id))

    @app.post("/sites/<site_id>/delete")
    def delete_site(site_id: str):
        config = load_config()
        original_count = len(config.sites)
        config.sites = [site for site in config.sites if site.id != site_id]
        if len(config.sites) == original_count:
            flash("Site not found.", "warning")
        else:
            save_config(config)
            flash("Site removed.", "success")
        return redirect(url_for("index", tab="job-alerts"))

    @app.post("/sites/<site_id>/test")
    def test_site(site_id: str):
        runner = JobAlertRunner()
        result = runner.test_site(site_id)
        if result.success:
            flash(
                f"Test succeeded for {result.label}: adapter={result.adapter_name}, jobs={result.jobs_found}, matched={len(result.matched_jobs)}",
                "success",
            )
        else:
            flash(f"Test failed for {result.label}: {result.warning}", "danger")
        return redirect(url_for("index", tab="job-alerts"))

    @app.get("/sites/<site_id>/preview")
    def preview_site(site_id: str):
        config = load_config()
        site = next((item for item in config.sites if item.id == site_id), None)
        if not site:
            return jsonify({"ok": False, "error": "Site not found."}), 404

        runner = JobAlertRunner()
        result = runner.test_site(site_id)
        payload = {
            "ok": result.success,
            "site_id": site.id,
            "label": site.label,
            "source_url": site.source_url,
            "adapter_name": result.adapter_name,
            "resolved_url": result.resolved_url,
            "jobs_found": result.jobs_found,
            "matched_count": len(result.matched_jobs),
            "warning": result.warning,
            "notes": result.notes,
            "jobs": [
                {
                    "title": job.title,
                    "url": job.url,
                    "location": job.location,
                    "posted_text": job.posted_text,
                    "matched_terms": job.matched_terms,
                }
                for job in result.matched_jobs
            ],
        }
        return jsonify(payload)

    @app.post("/run-now")
    def run_now():
        summary = JobAlertRunner().run_all()
        flash(summary.render_text().replace("\n", " | "), "success")
        return redirect(url_for("index", tab="diagnostics"))

    @app.post("/scheduler/apply")
    def apply_scheduler():
        config = load_config()
        ok, message = SchedulerService().apply(config.scheduler)
        flash(message, "success" if ok else "danger")
        return redirect(url_for("index", tab="setup"))

    @app.post("/keywords/promote")
    def promote_keyword():
        config = load_config()
        term = request.form.get("term", "").strip()
        bucket = request.form.get("bucket", "").strip()
        if not term or bucket not in {"include_any", "exclude_any", "location_any", "contract_type_any", "language_any"}:
            flash("Invalid keyword promotion request.", "danger")
            return redirect(url_for("index", tab="profile"))
        values = getattr(config.profile, bucket)
        if term not in values:
            values.append(term)
            setattr(config.profile, bucket, values)
            save_config(config)
            flash(f"Added '{term}' to the default profile.", "success")
        else:
            flash(f"'{term}' is already in the default profile.", "warning")
        return redirect(request.referrer or url_for("index", tab="profile"))

    return app
