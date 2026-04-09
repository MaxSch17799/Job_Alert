# Job Alert Plan

## Objective

Build a lightweight Windows-based job alert scraper that:

- checks a fixed list of job sites on a schedule
- detects newly posted jobs
- filters jobs by keywords and optional exclusions
- sends a simple notification when matching new jobs appear
- sends an error notification when a site breaks or a scrape fails
- runs via Windows Task Scheduler instead of as a permanent background process
- exposes a simple local configuration UI to add sites, edit keywords, and change alert behavior without editing code
- stays shareable so another person can install the tool and create their own profile and site list without changing code

This should be a normal coded scraper, not an AI-driven parser.

## Recommended Approach

Use a small Python application with:

- `requests` for HTTP fetching
- `sqlite3` for local persistence
- `PyYAML` or `tomllib` for site configuration
- a small local web UI for configuration
- `Windows Task Scheduler` for scheduling
- a simple notification backend:
  - primary: email through Gmail SMTP
  - optional later: Telegram, Discord webhook, or others through the same notifier interface

Avoid Cloudflare Workers for the first version. A local Windows setup is simpler to debug, easier to maintain, and sufficient for about 10 job sites if the PC is on regularly.

## Why This Architecture

- lightweight: no server, no Docker, no browser unless strictly needed
- resilient: state is stored locally in SQLite
- maintainable: each site type gets a small adapter
- cheap: zero hosting cost if run locally
- easy recovery: Task Scheduler can rerun after missed schedules
- user-friendly: most changes should be possible through a simple local UI
- AI-friendly: config remains in plain files and SQLite so it can be inspected and repaired directly if needed
- portable: the tool should be profile-driven and configurable rather than hardcoded to one user's interests

## Core Design

### 1. Site Adapters

Each website is assigned a scraper adapter:

- `workday`
  - use the direct JSON API behind Workday career sites
  - example pattern:
    - `https://<tenant>.wd3.myworkdayjobs.com/wday/cxs/<tenant>/<site>/jobs`
- `onlyfy`
  - use the job list AJAX endpoint or parse the returned HTML fragments
- `generic_html`
  - fallback adapter for simple sites where job cards are in normal HTML
- `generic_json`
  - fallback adapter for sites with exposed JSON feeds

For your examples, at least these are already viable without AI:

- `eumetsat.onlyfy.jobs`
- `leonardocompany.wd3.myworkdayjobs.com`
- `ag.wd3.myworkdayjobs.com`

### 2. Canonical Job Model

Normalize every scraped job into one common shape:

- `site_id`
- `job_id`
- `title`
- `url`
- `location`
- `posted_text`
- `summary_text`
- `raw_hash`
- `scraped_at`

`job_id` should come from the site if possible. If not available, derive it from a stable URL or hash.

### 3. Local State

Use SQLite with tables like:

- `sites`
  - site metadata and last run status
- `jobs_seen`
  - known jobs already stored
- `runs`
  - execution history for debugging
- `alerts_sent`
  - optional dedupe for notifications

This allows:

- detection of newly seen jobs
- detection of repeat site failures
- recovery after reboots
- a simple audit trail

### 4. Configuration UI

The project should include a very lightweight local configuration UI.

Recommended approach:

- run a local web app on `localhost`
- open it in the browser as the "config window"
- store actual settings in plain config files plus SQLite state

This is preferable to a native desktop GUI because:

- easier to build and maintain
- easier to inspect and fix
- easier to extend later
- easier to version in GitHub once a repo is provided

The UI should let you:

- complete a first-run setup flow
- create or edit the installation's default user profile
- paste or import keyword/profile YAML
- add a new website to monitor
- select the scraper type if known
- edit site URL or endpoint
- add per-site include and exclude keywords
- enable broad matching by default
- choose notification behavior per site
- choose whether a site sends:
  - immediate new-job alerts
  - daily summary
  - weekly summary
  - monthly summary
- enable optional filters such as:
  - location
  - contract type
  - language
  - remote or hybrid hints if detectable
- enable or disable a site
- test a site scrape manually
- view last success or failure message
- view recent jobs found for that site
- export or copy profile/site settings for reuse on another machine

The UI should keep defaults broad and forgiving so a user does not accidentally over-filter and miss relevant jobs.

Advanced options behavior:

- advanced settings should be hideable
- advanced settings should be shown by default at first
- the user should still be able to collapse them for a cleaner view

Adapter selection behavior:

- the system should try to auto-detect common site types such as `workday` and `onlyfy`
- the user must be able to override the detected adapter manually

History and diagnostics behavior:

- scrape error history should be tracked
- it can be hidden in the UI by default or tucked into a diagnostic section
- it should remain easy to inspect when something breaks

Site keyword UX behavior:

- site-specific keywords should be visually marked as site-only
- the UI should make clear which terms come from the default profile and which are site-specific overrides
- a context menu or equivalent action should allow promoting a site-specific term into the default profile
- inherited terms and site-specific terms should be easy to inspect separately

### 5. Filtering

Each site can define filters in config:

- `include_any`
- `exclude_any`
- optional `include_regex`
- optional location filters
- optional contract-type filters
- optional language filters
- optional summary frequency preferences

Filtering should be applied to:

- title
- location
- short summary or description text if available

Design principle:

- default behavior should be broad
- advanced filters should be optional
- per-site settings should override any global defaults

The system should also support a user-level default profile:

- default include keywords
- default exclude keywords
- default location preferences
- default contract-type preferences
- default language preferences

New sites should inherit the user profile by default, while still allowing site-specific overrides.

Inheritance behavior:

- site-specific terms should stay local to that site by default
- inherited profile terms should still apply unless explicitly disabled
- the UI should allow promoting a site-specific term into the default profile later

For Workday sites, use server-side `searchText` when useful, but still keep local filtering as the final rule.

### 6. Notification Strategy

V1 should send email alerts first.

Architecture should still be notifier-based so other channels can be added later without redesign.

Initial notification targets:

- email
- future optional channels:
  - Telegram
  - Discord webhook
  - other simple webhooks

Send notifications for:

- newly found matching jobs
- site failures
- site recovery after a failure
- configuration errors
- optional summary emails depending on per-site settings

Default alert behavior for new sites:

- immediate alerts only
- no weekly summary by default
- no monthly summary by default

Digest behavior:

- each check should group all newly matching jobs into one email digest for that run
- first-run bootstrap results should also be grouped into a single digest email

### 7. Email Delivery Model

Recommended V1 delivery model:

- the app logs into a Gmail SMTP account
- that Gmail account sends alert emails
- the app sends them to your chosen recipient address or addresses

Practical options:

- simplest setup:
  - send from your personal Gmail account to your personal Gmail account
  - requires a Gmail app password if 2-step verification is enabled
- cleaner long-term setup:
  - create a separate sender account such as a dedicated job-alert Gmail account
  - use that account only for sending alerts to your normal inbox

Recommendation:

- use a dedicated sender account from the start if you want a cleaner inbox setup
- send from that dedicated account to your normal inbox
- if you want the least setup work possible, use your personal Gmail first and switch later

Who sends what:

- sender account:
  - the Gmail account whose SMTP credentials are stored in the app
- recipient account:
  - the email address that receives the alerts
- the app itself:
  - generates the email body and asks Gmail SMTP to deliver it

This should be configurable in the UI and also remain editable in plain config if needed.

Setup note:

- if Gmail is used, the sender account will usually need:
  - a normal Gmail account
  - 2-step verification enabled
  - an app password for the local app

This is still one of the simpler low-cost options, but it is not completely zero-setup.

## Failure Handling

A single failed run should trigger an alert, because the user wants early failure visibility and details for fixing the issue quickly.

Use this rule:

- first failed run: send warning notification with details
- repeated failed runs: keep logging them, but avoid spamming duplicate emails unless the message changes or a cooldown expires
- recovery after failures: send recovery notification

Track:

- HTTP status failures
- timeout failures
- parse failures
- empty-result anomalies where a site suddenly returns zero jobs unexpectedly

Optional safeguard:

- if a site previously returned many jobs and now returns zero, mark as suspicious instead of deleting known state

## Runtime Flow

Each scheduled run should do this:

1. Load config
2. For each enabled site:
3. Fetch listings
4. Parse into canonical jobs
5. Apply filters
6. Compare against `jobs_seen`
7. Notify on new matching jobs
8. Record success or failure
9. Send summary only if something important happened

Default behavior should be quiet when nothing changed.

First-run bootstrap behavior:

- on the very first successful scrape of a site, send relevant currently-open jobs once
- mark those jobs as already seen after that initial run
- do not re-send them on later daily runs unless new jobs appear
- group the first-run results into one digest email for that site or run

## Scheduling on Windows

Use Windows Task Scheduler, not a persistent process.

Recommended schedule:

- start with `daily`
- run at a fixed time when the PC is usually on
- expose schedule settings in the UI so the user can later change frequency
- support at least:
  - daily
  - specific weekdays
  - weekly
  - custom cron-like advanced mode later if needed
- enable:
  - `Run whether user is logged on or not` if convenient
  - `Run task as soon as possible after a scheduled start is missed`
  - `If the task fails, restart every ...`

Optional second trigger:

- `At startup` or `At log on`

This avoids manual relaunch after shutdowns.

## Proposed Project Structure

```text
Job_Alert/
  PLAN.md
  README.md
  requirements.txt
  config.example.yaml
  run_job_alert.py
  launch_ui.py
  job_alert/
    __init__.py
    config.py
    models.py
    db.py
    filters.py
    notifier.py
    runner.py
    scheduler.py
    ui.py
    profile.py
    adapters/
      __init__.py
      workday.py
      onlyfy.py
      generic_html.py
      generic_json.py
```

## Implementation Phases

### Phase 1: Minimal Working Version

- create config-driven Python project
- implement SQLite state
- implement `workday` adapter
- implement `onlyfy` adapter
- add Gmail SMTP email notification
- define notifier abstraction for future channels
- add keyword include/exclude filtering
- add user profile defaults that new sites inherit
- add a minimal local configuration UI
- add profile import or paste support for keyword YAML
- support per-site settings in the UI
- support first-run bootstrap alerts
- support adapter auto-detection with manual override
- support promoting site-specific keywords into the default profile
- add Windows Task Scheduler setup instructions

### Phase 2: Reliability

- add consecutive failure tracking
- add recovery notifications
- add run logs
- add retry and timeout handling
- add suspicious empty-result detection
- add duplicate-failure cooldown behavior

### Phase 3: Convenience

- add summary mode
- add dry-run mode
- add CLI flags such as:
  - `--once`
  - `--site airbus`
  - `--verbose`
- add simple export/report of current tracked jobs
- add more notification channels
- add richer UI editing and validation

## Config Model Direction

The system should have both:

- a human-editable config file
- a UI that edits the same underlying settings safely

This keeps the setup accessible both to you and to future maintenance done directly in the repo.

The configuration should remain generic and reusable:

- no user-specific terms hardcoded in source code
- default profile data can be created through onboarding or imported through the UI
- another user should be able to install the project and create a different profile without editing code

Likely config shape:

```yaml
global:
  profile:
    include_any: []
    exclude_any: []
    location_any: []
    contract_type_any: []
    language_any: []
  notification_channels:
    email:
      enabled: true
      provider: gmail
      smtp_host: smtp.gmail.com
      smtp_port: 587
      sender_email: placeholder@gmail.com
      recipient_emails:
        - placeholder@gmail.com
  scheduler:
    mode: daily
    time: "08:00"
  defaults:
    broad_match: true
    alert_on_first_failure: true

sites:
  - id: airbus
    enabled: true
    type: workday
    endpoint: https://ag.wd3.myworkdayjobs.com/wday/cxs/ag/Airbus/jobs
    use_profile_defaults: true
    include_any: []
    exclude_any: []
    filters:
      location_any: []
      contract_type_any: []
      language_any: []
    alerts:
      immediate_new_jobs: true
      daily_summary: false
      weekly_summary: false
      monthly_summary: false
      alert_on_failure: true
    ui:
      advanced_expanded: true
```

## Keyword Intake Format

The keyword intake should be easy to paste into config later.

Preferred shape:

```yaml
include_any:
  - keyword 1
  - keyword 2
exclude_any:
  - keyword 3
location_any:
  - germany
  - darmstadt
contract_type_any:
  - permanent
  - internship
language_any:
  - english
  - german
```

## Non-Goals for V1

- no browser automation unless a site truly requires JavaScript rendering
- no AI interpretation
- no cloud deployment by default
- no large multi-user dashboard

## Technical Assumptions

- Windows machine is used regularly
- Python can be installed locally
- the number of target sites is small, about 10
- most sites are either Workday-like or simple HTML
- personal-use scraping is acceptable under each target site's terms

## Main Risks

- some sites may change HTML structure
- some sites may introduce anti-bot controls
- some sites may not expose stable job IDs
- email delivery setup can vary depending on provider and security rules
- a local-only runner will miss checks while the PC is fully off
- the configuration UI can become bloated if too many advanced options are pushed into V1

## Recommendation Summary

The strongest first version is:

- Python
- SQLite
- adapter-based scraping
- Gmail SMTP email-first notifications with an extensible notifier layer
- Windows Task Scheduler
- a minimal local configuration UI
- a user profile with default keywords inherited by each new site

That gives the best balance of simplicity, zero hosting cost, and reliability for a personal job monitor.

## Git Workflow Note

Planned remote repository:

- `https://github.com/MaxSch17799/Job_Alert.git`

Expected push flow later when implementation exists:

```bash
git remote add origin https://github.com/MaxSch17799/Job_Alert.git
git branch -M main
git push -u origin main
```

## Locked V1 Inputs

### Exact V1 URLs

- `https://eumetsat.onlyfy.jobs/`
- `https://leonardocompany.wd3.myworkdayjobs.com/LeonardoCareerSite`
- `https://ag.wd3.myworkdayjobs.com/Airbus`
- `https://jobs.esa.int/`
- `https://www.eumetsat.int/work-us/vacancies`
- `https://www.saab.com/career`
- `https://www.beyondgravity.com/en/careers`
- `https://www.pilatus-aircraft.com/en/jobs`
- `https://www.ohb.de/en/career`
- `https://career-ohb.csod.com/ux/ats/careersite/4/home?c=career-ohb&lang=de-DE`
- `https://www.lufthansa-technik.com/en/career`
- `https://careers.smartrecruiters.com/cern/tech`

### Confirmed Product Decisions

- use the pasted keyword/profile block as the initial default profile seed for this install
- main UI direction:
  - dashboard table for overview
  - dedicated site edit page or panel for detailed editing
- one profile per install for V1
- keep both SQLite history and plain text logs
- each run sends one grouped digest email for all new matching jobs found in that run
- site-specific terms remain site-specific by default
- the UI should support promoting a site-specific term into the default profile later
- do not hardcode user-specific data in the application logic
- keep the tool reusable so another user can install it and create their own profile through the UI

### Implementation Readiness Note

The planning scope is now sufficient to begin implementation.

## Questions To Finalize Before Build

1. For contract type filters, should V1 support free-text entry plus optional suggested presets?
2. When implementation starts, should everything stay local until you explicitly ask for a Git push?
