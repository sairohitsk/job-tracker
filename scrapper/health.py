# health.py — Tracks scraper failures per company across runs
# Persists state in data/scraper_health.json
# Only counts hard errors (HTTP failures, exceptions) as broken — not "no matches today"

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

HEALTH_FILE       = "data/scraper_health.json"
FAILURE_THRESHOLD = 3   # alert after this many consecutive hard-error runs


def load_health() -> dict:
    path = Path(HEALTH_FILE)
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            return {}
    return {}


def save_health(health: dict) -> None:
    path = Path(HEALTH_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(health, indent=2, sort_keys=True))


def record_results(company_name: str, job_count: int, health: dict) -> dict:
    """
    Update health record for a company after a scrape run.

    job_count meanings:
      -1  → hard error: HTTP failure, timeout, exception — scraper is broken
       0  → ran fine but no India-matching roles found today — this is NORMAL, not a failure
      >0  → healthy, found matching jobs

    We only flag a scraper as broken when job_count == -1 (hard error).
    A company that genuinely has no open India roles will return 0 every run
    and that's perfectly fine — we don't want false alerts for that.
    """
    entry = health.get(company_name, {
        "consecutive_errors": 0,
        "alerted":            False,
        "last_error":         None,
        "recovered":          False,
    })

    if job_count >= 0:
        # Successful scrape (0 matches is fine — could just be no open India roles)
        was_broken = entry.get("consecutive_errors", 0) > 0 or entry.get("alerted", False)
        if was_broken:
            logger.info(f"[Health] ✅ {company_name} recovered (scraper working again)")
            entry["recovered"] = True
        else:
            entry["recovered"] = False
        entry["consecutive_errors"] = 0
        entry["alerted"]            = False
        entry["last_error"]         = None
    else:
        # Hard error: -1
        entry["recovered"]          = False
        entry["consecutive_errors"] = entry.get("consecutive_errors", 0) + 1
        entry["last_error"]         = "HTTP error / timeout / exception"
        logger.warning(
            f"[Health] ❌ {company_name} hard error "
            f"(streak: {entry['consecutive_errors']})"
        )

    health[company_name] = entry
    return health


def get_broken_scrapers(health: dict) -> list[dict]:
    """
    Returns companies that have hit the failure threshold
    and haven't been alerted yet this streak.
    """
    broken = []
    for company, entry in health.items():
        if (
            entry.get("consecutive_errors", 0) >= FAILURE_THRESHOLD
            and not entry.get("alerted", False)
        ):
            broken.append({
                "company":    company,
                "failures":   entry["consecutive_errors"],
                "last_error": entry.get("last_error", "unknown"),
            })
    return broken


def get_recovered_scrapers(health: dict) -> list[str]:
    """Returns companies that just recovered from a broken streak."""
    return [c for c, e in health.items() if e.get("recovered", False)]


def mark_alerted(health: dict, company_names: list[str]) -> dict:
    """Mark companies as alerted so we don't spam every hour during an ongoing outage."""
    for name in company_names:
        if name in health:
            health[name]["alerted"] = True
    return health
