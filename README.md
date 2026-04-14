# Job Tracker — Auto-apply alert system

Monitors 123 company career pages every 30 minutes. Sends instant **Telegram push notifications** and **Gmail digest emails** when new matching jobs appear in India.

## What it does

- Checks Greenhouse, Lever APIs (100% reliable — no scraping)
- Uses Playwright headless browser for Workday, custom JS career pages
- Matches against 21 role keywords + India location filter
- Deduplicates — you never see the same job twice
- Notifies via Telegram (instant, per job) + Gmail (digest per run)
- Runs free on GitHub Actions every 30 minutes, 24/7

---

## Setup — step by step

### Step 1 — Fork / create the repo

1. Go to [github.com](https://github.com) and create a **new private repository** (e.g. `job-tracker`)
2. Upload all files from this folder into it (drag and drop works)

Or via terminal:
```bash
cd job-tracker
git init
git remote add origin https://github.com/YOUR_USERNAME/job-tracker.git
git add .
git commit -m "initial commit"
git push -u origin main
```

---

### Step 2 — Add GitHub Secrets

Go to your repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Add these 3 secrets:

| Secret name | Value |
|---|---|
| `GMAIL_APP_PASSWORD` | `lugs yqjj lzqg ldvl` (your Gmail app password, spaces are fine) |
| `TELEGRAM_BOT_TOKEN` | Your bot token from `@BotFather` (add this when ready) |
| `TELEGRAM_CHAT_ID` | Your chat ID from `@userinfobot` (add this when ready) |

> The Gmail secret is already configured. You can add Telegram later — the system works with just Gmail until then.

---

### Step 3 — Enable GitHub Actions

1. Go to your repo → **Actions** tab
2. Click **"I understand my workflows, go ahead and enable them"**
3. Click on **"Job Tracker"** in the left panel
4. Click **"Run workflow"** → **"Run workflow"** to test it manually right now

---

### Step 4 — Set up Telegram (optional but recommended)

1. Open Telegram → search `@BotFather` → send `/newbot`
2. Give it a name (e.g. "My Job Tracker") and a username (e.g. `myjobtracker_bot`)
3. Copy the **API token** it gives you → add as `TELEGRAM_BOT_TOKEN` secret
4. Search `@userinfobot` → send `/start` → copy your **id** number → add as `TELEGRAM_CHAT_ID` secret
5. **Important:** Send any message to your new bot first (search it by username and press Start), otherwise it can't message you

---

### Step 5 — Watch it run

After the first manual run:
- Check your Gmail (`shaiksairohit@gmail.com`) for a digest email
- If Telegram is set up, you'll get individual push notifications per job
- The `data/seen_jobs.json` file in your repo will grow as jobs are tracked

The workflow then runs automatically every 30 minutes forever.

---

## Notification examples

**Telegram (per new job):**
```
🆕 New Job Match!

🏢 Company: Databricks
💼 Role: Data Engineer
📍 Location: Bengaluru, India
🔗 Apply Now → https://...
```

**Gmail (digest per run):**
- Subject: `[Job Digest] 3 new job(s) found`
- Table with company, role, location, Apply link
- Full job description included (for Greenhouse/Lever companies)

---

## Files explained

```
job-tracker/
├── main.py                        # Entry point — runs everything
├── requirements.txt               # Python dependencies
├── data/
│   └── seen_jobs.json             # Tracks seen job IDs (auto-updated)
├── scraper/
│   ├── companies.py               # All 123 companies with ATS type + URLs
│   ├── config.py                  # Role keywords, India locations, settings
│   ├── ats_api.py                 # Greenhouse + Lever API scrapers
│   └── playwright_scraper.py      # Headless browser for JS sites
├── notifier/
│   └── notifier.py                # Telegram + Gmail notification logic
└── .github/
    └── workflows/
        └── job_tracker.yml        # GitHub Actions cron schedule
```

---

## Adjusting role keywords or companies

**Add a role keyword:** Edit `scraper/config.py` → add to `ROLE_KEYWORDS` list

**Add a new company:**
Edit `scraper/companies.py` and add an entry:
```python
# For Greenhouse companies (check: careers.yourcompany.com → look for greenhouse.io in URL)
{"name": "New Company", "ats": "greenhouse", "greenhouse_id": "newcompany", "url": "https://api.greenhouse.io/v1/boards/newcompany/jobs"},

# For Lever companies
{"name": "New Company", "ats": "lever", "lever_id": "newcompany", "url": "https://api.lever.co/v0/postings/newcompany?mode=json"},

# For everything else
{"name": "New Company", "ats": "playwright", "url": "https://careers.newcompany.com/jobs?q={role}&location=India"},
```

**How to find a company's ATS:**
- Visit their careers page
- Look at the URL — `greenhouse.io` → Greenhouse, `lever.co` → Lever, `myworkday` → Workday
- Everything else → use `playwright`

---

## Troubleshooting

| Problem | Fix |
|---|---|
| No email received | Check spam folder; verify app password in secrets (no spaces) |
| Workflow not running | Check Actions tab → enable workflows → run manually first |
| `seen_jobs.json` not updating | Check Actions has `contents: write` permission (already set) |
| Playwright timeout errors | Normal for some sites — they'll be retried next run |
| Telegram not working | Make sure you sent `/start` to your bot first |
