from __future__ import annotations

import smtplib
from collections import defaultdict
from email.message import EmailMessage

from .models import JobPosting


class EmailNotifier:
    def __init__(
        self,
        *,
        smtp_host: str,
        smtp_port: int,
        smtp_username: str,
        smtp_app_password: str,
        sender_email: str,
        sender_name: str,
        recipient_emails: list[str],
    ) -> None:
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_username = smtp_username or sender_email
        self.smtp_app_password = smtp_app_password
        self.sender_email = sender_email
        self.sender_name = sender_name or "Job Alert"
        self.recipient_emails = [item for item in recipient_emails if item]

    def is_configured(self) -> bool:
        return bool(
            self.smtp_host
            and self.smtp_port
            and self.sender_email
            and self.smtp_username
            and self.smtp_app_password
            and self.recipient_emails
        )

    def send_message(self, subject: str, body: str) -> str:
        if not self.is_configured():
            raise RuntimeError("Email settings are incomplete. Fill in sender, password, and recipient fields.")
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = f"{self.sender_name} <{self.sender_email}>"
        message["To"] = ", ".join(self.recipient_emails)
        message.set_content(body)
        with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30) as client:
            client.starttls()
            client.login(self.smtp_username, self.smtp_app_password)
            client.send_message(message)
        return f"{subject} -> {', '.join(self.recipient_emails)}"

    def send_jobs_digest(self, jobs: list[JobPosting], *, bootstrap: bool = False) -> str:
        grouped: dict[str, list[JobPosting]] = defaultdict(list)
        for job in jobs:
            grouped[job.site_id].append(job)

        subject_prefix = "Bootstrap jobs" if bootstrap else "New jobs"
        subject = f"{subject_prefix}: {len(jobs)} matching role(s)"
        lines = [f"{subject_prefix} found: {len(jobs)}", ""]
        for site_id, site_jobs in grouped.items():
            lines.append(f"{site_id} ({len(site_jobs)})")
            lines.append("-" * max(8, len(site_id) + 4))
            for job in site_jobs:
                lines.append(job.title)
                if job.location:
                    lines.append(f"Location: {job.location}")
                if job.posted_text:
                    lines.append(f"Posted: {job.posted_text}")
                if job.matched_terms:
                    lines.append(f"Matched: {', '.join(job.matched_terms)}")
                lines.append(job.url)
                lines.append("")
        return self.send_message(subject, "\n".join(lines).strip() + "\n")

    def send_failure(self, site_label: str, message_text: str) -> str:
        return self.send_message(f"Job Alert failure: {site_label}", f"Site: {site_label}\n\n{message_text}\n")

    def send_recovery(self, site_label: str, adapter_name: str) -> str:
        return self.send_message(f"Job Alert recovered: {site_label}", f"Site: {site_label}\nRecovered adapter: {adapter_name}\n")

    def send_test_message(self) -> str:
        return self.send_message(
            "Job Alert test email",
            "This is a test email from your local Job Alert setup.\n\nIf you received this, the sender account and app password are working.\n",
        )

    def send_periodic_summary(self, site_label: str, jobs: list[JobPosting], *, period: str) -> str:
        subject = f"{period.title()} summary: {site_label} ({len(jobs)} matching role(s))"
        lines = [f"{period.title()} summary for {site_label}", ""]
        for job in jobs:
            lines.append(job.title)
            if job.location:
                lines.append(f"Location: {job.location}")
            if job.posted_text:
                lines.append(f"Posted: {job.posted_text}")
            if job.matched_terms:
                lines.append(f"Matched: {', '.join(job.matched_terms)}")
            lines.append(job.url)
            lines.append("")
        return self.send_message(subject, "\n".join(lines).strip() + "\n")
