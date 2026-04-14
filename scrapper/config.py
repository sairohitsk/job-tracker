# config.py — Role keywords, location filters, and notification settings

# Job title keywords to match (case-insensitive substring match)
ROLE_KEYWORDS = [
    "SDE",
    "SDE1",
    "SDE-1",
    "SWE",
    "SWE1",
    "SWE-1",
    "SW Engineer",
    "Software Engineer",
    "Software Developer",
    "Software Development Engineer",
    "Software Analyst",
    "Software Associate",
    "AI Engineer",
    "AI Scientist",
    "ML Engineer",
    "Machine Learning Engineer",
    "Data Engineer",
    "Data Analyst",
    "Data Scientist",
    "DevOps Engineer",
    "DevOps",
    "Cloud Engineer",
    "AWS Engineer",
    "Azure Engineer",
    "Support Engineer",
    "Backend Engineer",
    "Site Reliability",
    "Platform Engineer",
]

# India location keywords — job must match at least one (case-insensitive)
# If a job has NO location listed, it is included anyway (see ats_api.py)
INDIA_LOCATIONS = [
    "india",
    "bengaluru",
    "bangalore",
    "hyderabad",
    "mumbai",
    "pune",
    "gurugram",
    "gurgaon",
    "noida",
    "chennai",
    "kolkata",
    "delhi",
    "ncr",
    "remote",
]

# ─── Email settings ───────────────────────────────────────────────────────────
# Emails are sent FROM sender TO recipient.
# Change these to your own addresses if needed.
SENDER_EMAIL    = "n8nworkflow2026@gmail.com"
RECIPIENT_EMAIL = "shaiksairohit@gmail.com"

# Secrets are loaded from GitHub Actions environment variables:
#   GMAIL_APP_PASSWORD  → Gmail app password for SENDER_EMAIL
#   TELEGRAM_BOT_TOKEN  → Token from @BotFather
#   TELEGRAM_CHAT_ID    → Your personal Telegram chat ID

# ─── Scraper settings ─────────────────────────────────────────────────────────
SCRAPE_DELAY   = 2     # seconds between Playwright page loads (rate limiting)
SEEN_JOBS_FILE = "data/seen_jobs.json"
