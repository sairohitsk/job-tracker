#!/usr/bin/env python3
# main.py — Job tracker entry point
# Notifications: Gmail only (Telegram disabled)

import json
import logging
import sys
import time
from pathlib import Path

from scraper.companies import COMPANIES
from scraper.config import SEEN_JOBS_FILE
from scraper.ats_api import scrape_greenhouse, scrape_lever
from scraper.playwright_scraper import scrape_playwright
from scraper.health import (
    load_health,
    save_health,
    record_results,
    get_broken_scrapers,
    get_recovered_scrapers,
    mark_alerted,
)
from notifier.notifier import send_digest_email
from notifier.health_notifier import send_broken_email, send_recovered_email

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


# ─── Seen-jobs store ──────────────────────────────────────────────────────────

def load_seen_jobs() -> set:
    path = Path(SEEN_JOBS_FILE)
    if path.exists():
        try:
            return set(json.loads(path.read_text()))
        except Exception:
            return set()
    return set()


def save_seen_jobs(seen: set) -> None:
    path = Path(SEEN_JOBS_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(sorted(seen), indent=2))


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    logger.info("=" * 60)
    logger.info("Job tracker starting")
    logger.info("=" * 60)

    seen_jobs = load_seen_jobs()
    health    = load_health()
    logger.info(f"Loaded {len(seen_jobs)} previously seen job IDs")

    # ── Split companies by ATS type ───────────────────────────────────────────
    greenhouse_companies = [c for c in COMPANIES if c["ats"] == "greenhouse"]
    lever_companies      = [c for c in COMPANIES if c["ats"] == "lever"]
    playwright_companies = [c for c in COMPANIES if c["ats"] in ("playwright", "workday")]

    all_found = []

    # ── Greenhouse (official public API) ──────────────────────────────────────
    logger.info(f"\nScraping {len(greenhouse_companies)} Greenhouse companies...")
    for company in greenhouse_companies:
        jobs      = scrape_greenhouse(company)
        job_count = len(jobs) if jobs is not None else -1   # None = hard error
        health    = record_results(company["name"], job_count, health)
        if jobs:
            all_found.extend(jobs)
        time.sleep(0.5)

    # ── Lever (official public API) ───────────────────────────────────────────
    logger.info(f"\nScraping {len(lever_companies)} Lever companies...")
    for company in lever_companies:
        jobs      = scrape_lever(company)
        job_count = len(jobs) if jobs is not None else -1
        health    = record_results(company["name"], job_count, health)
        if jobs:
            all_found.extend(jobs)
        time.sleep(0.5)

    # ── Playwright / Workday (JS-rendered pages) ──────────────────────────────
    logger.info(f"\nScraping {len(playwright_companies)} JS-rendered career pages...")
    playwright_results = scrape_playwright(playwright_companies)
    for company_name, jobs in playwright_results:
        job_count = len(jobs) if isinstance(jobs, list) else -1
        health    = record_results(company_name, job_count, health)
        if isinstance(jobs, list):
            all_found.extend(jobs)

    logger.info(f"\nTotal jobs found this run: {len(all_found)}")

    # ── Deduplicate against already-seen jobs ─────────────────────────────────
    new_jobs = []
    for job in all_found:
        if job["id"] not in seen_jobs:
            new_jobs.append(job)
            seen_jobs.add(job["id"])

    logger.info(f"New jobs (not seen before): {len(new_jobs)}")

    # ── Notify: new jobs via email ────────────────────────────────────────────
    if new_jobs:
        logger.info("Sending job digest email...")
        send_digest_email(new_jobs)
    else:
        logger.info("No new jobs found this run.")

    # ── Health checks: broken and recovered scrapers ──────────────────────────
    broken    = get_broken_scrapers(health)
    recovered = get_recovered_scrapers(health)

    if broken:
        logger.warning("\n" + "=" * 60)
        logger.warning(f"BROKEN SCRAPERS ({len(broken)}):")
        for b in broken:
            logger.warning(
                f"  ❌ {b['company']} — {b['failures']} consecutive failures"
            )
        logger.warning("=" * 60)
        send_broken_email(broken)
        health = mark_alerted(health, [b["company"] for b in broken])

    if recovered:
        logger.info(f"\nRECOVERED SCRAPERS: {', '.join(recovered)}")
        send_recovered_email(recovered)

    # ── Save state for next run ───────────────────────────────────────────────
    save_seen_jobs(seen_jobs)
    save_health(health)
    logger.info(f"Saved {len(seen_jobs)} job IDs and health data.")
    logger.info("Run complete.")


if __name__ == "__main__":
    main()
