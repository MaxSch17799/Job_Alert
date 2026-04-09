# Job Alert

Local Windows job-alert scraper with:

- editable profile and site settings in a local browser UI
- SQLite state and plain text logs
- Gmail SMTP notifications
- a test-email button in the UI
- immediate alerts plus optional weekly or monthly summaries per site
- Windows Task Scheduler integration
- direct adapters for Workday, onlyfy, Lufthansa Group, and generic HTML pages
- explicit failure reporting for login-gated boards such as Pilatus SuccessFactors
- a browser fallback for dynamic pages that do not expose a cleaner endpoint

## Setup

1. Create a virtual environment:

```powershell
py -m venv .venv
```

2. Install dependencies:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

3. Install the Chromium browser used by the dynamic fallback:

```powershell
.venv\Scripts\python.exe -m playwright install chromium
```

4. Edit `secrets.yaml` with the Gmail sender account and recipient addresses, or fill them in through the UI later.

5. Launch the local UI:

```powershell
.venv\Scripts\python.exe launch_ui.py
```

6. Open the shown `http://127.0.0.1:5000` address in your browser.

## Run A Scrape Manually

```powershell
.venv\Scripts\python.exe run_job_alert.py
```

## Gmail Notes

The app does not send mail by itself. It connects to Gmail's SMTP service with the sender account you configure and asks Gmail to send the message to the recipient addresses you configure.

Recommended setup:

- create a dedicated Gmail account for alerts
- enable 2-Step Verification on that sender account
- create an App Password for that account
- paste the App Password into `secrets.yaml` or the UI
- use the `Send Test Email` button in the UI to verify the setup before scheduling runs

## Scheduler

You can edit schedule settings in the UI. The UI can also generate and apply a Windows Task Scheduler job for the scraper.

- `Every N days` means daily mode with a repeat interval such as `1` day or `3` days.
- `Every N weeks on weekdays` means weekly mode with a repeat interval such as `1` week or `2` weeks plus chosen weekdays.

## Current Site Coverage

- Workday boards are scraped directly through their JSON endpoint.
- onlyfy boards are scraped through their public AJAX list endpoint.
- Lufthansa Technik is scraped through the Lufthansa Group job API and filtered down to Lufthansa Technik organizations.
- CERN resolves to the public `careers.cern/jobs/` board.
- Pilatus currently resolves to a SuccessFactors sign-in page, so the app marks it as a failure with a clear message instead of silently returning zero jobs.
