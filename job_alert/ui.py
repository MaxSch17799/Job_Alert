from __future__ import annotations

from flask import Flask, flash, redirect, render_template, request, url_for

from .config import load_config, make_site_from_form, save_config, update_profile_from_form
from .db import Database
from .notifier import EmailNotifier
from .runner import JobAlertRunner
from .scheduler import SchedulerService
from .utils import list_to_textarea, textarea_to_list


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["SECRET_KEY"] = "job-alert-local-ui"

    def _site_statuses():
        db = Database()
        return {site_id: db.get_site_status(site_id) for site_id in [site.id for site in load_config().sites]}

    @app.get("/")
    def index():
        config = load_config()
        db = Database()
        status_map = {site.id: db.get_site_status(site.id) for site in config.sites}
        runs = db.recent_runs(20)
        scheduler_command = " ".join(SchedulerService().build_task_command(config.scheduler))
        return render_template(
            "index.html",
            config=config,
            status_map=status_map,
            runs=runs,
            list_to_textarea=list_to_textarea,
            scheduler_command=scheduler_command,
        )

    @app.post("/profile/save")
    def save_profile():
        config = load_config()
        update_profile_from_form(config, request.form, textarea_to_list)
        save_config(config)
        flash("Profile, email, and scheduler settings saved.", "success")
        return redirect(url_for("index"))

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
            return redirect(url_for("index"))
        try:
            description = notifier.send_test_message()
            flash(f"Test email sent: {description}", "success")
        except Exception as exc:
            flash(f"Test email failed: {exc}", "danger")
        return redirect(url_for("index"))

    @app.post("/profile/import")
    def import_profile():
        raw_yaml = request.form.get("profile_yaml", "").strip()
        if not raw_yaml:
            flash("Paste YAML before importing.", "warning")
            return redirect(url_for("index"))
        try:
            import yaml

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
        return redirect(url_for("index"))

    @app.get("/sites/new")
    def new_site():
        return render_template("site_form.html", site=None, inherited=None, list_to_textarea=list_to_textarea)

    @app.get("/sites/<site_id>")
    def edit_site(site_id: str):
        config = load_config()
        site = next((item for item in config.sites if item.id == site_id), None)
        if not site:
            flash("Site not found.", "danger")
            return redirect(url_for("index"))
        return render_template(
            "site_form.html",
            site=site,
            inherited=config.profile,
            list_to_textarea=list_to_textarea,
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
        return redirect(url_for("index"))

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
        return redirect(url_for("index"))

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
        return redirect(url_for("index"))

    @app.post("/run-now")
    def run_now():
        summary = JobAlertRunner().run_all()
        flash(summary.render_text().replace("\n", " | "), "success")
        return redirect(url_for("index"))

    @app.post("/scheduler/apply")
    def apply_scheduler():
        config = load_config()
        ok, message = SchedulerService().apply(config.scheduler)
        flash(message, "success" if ok else "danger")
        return redirect(url_for("index"))

    @app.post("/keywords/promote")
    def promote_keyword():
        config = load_config()
        term = request.form.get("term", "").strip()
        bucket = request.form.get("bucket", "").strip()
        if not term or bucket not in {"include_any", "exclude_any", "location_any", "contract_type_any", "language_any"}:
            flash("Invalid keyword promotion request.", "danger")
            return redirect(url_for("index"))
        values = getattr(config.profile, bucket)
        if term not in values:
            values.append(term)
            setattr(config.profile, bucket, values)
            save_config(config)
            flash(f"Added '{term}' to the default profile.", "success")
        else:
            flash(f"'{term}' is already in the default profile.", "warning")
        return redirect(request.referrer or url_for("index"))

    return app
