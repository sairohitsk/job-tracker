# ats_api.py — Greenhouse & Lever public API scrapers (no auth needed)
# Returns None on hard errors so health tracking can distinguish crashes from empty results

import requests
import logging
from scraper.config import ROLE_KEYWORDS, INDIA_LOCATIONS

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def _role_matches(title: str) -> bool:
    title_lower = title.lower()
    return any(kw.lower() in title_lower for kw in ROLE_KEYWORDS)


def _location_matches(location: str) -> bool:
    """
    Return True if the location is India-based.
    If no location is provided, include the job — better to show too many
    than to silently drop roles that just don't list a location.
    """
    if not location:
        return True
    return any(loc in location.lower() for loc in INDIA_LOCATIONS)


# ─── Greenhouse ───────────────────────────────────────────────────────────────

def scrape_greenhouse(company: dict) -> list[dict] | None:
    """
    Fetch all jobs from Greenhouse public board API.
    Returns list of matched jobs, or None on hard failure.
    Empty list [] means the API worked fine — just no matching roles today.
    """
    board_id = company.get("greenhouse_id", "")
    if not board_id:
        logger.error(f"[Greenhouse] {company['name']}: missing greenhouse_id in config")
        return None

    url     = f"https://api.greenhouse.io/v1/boards/{board_id}/jobs?content=true"
    matched = []

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        jobs = data.get("jobs", [])

        for job in jobs:
            title    = job.get("title", "")
            location = job.get("location", {}).get("name", "")
            job_url  = job.get("absolute_url", "")
            job_id   = str(job.get("id", ""))
            content  = job.get("content", "")

            if _role_matches(title) and _location_matches(location):
                # Strip HTML tags from description
                import re
                clean = re.sub(r"<[^>]+>", " ", content or "").strip()
                matched.append({
                    "id":          f"gh_{board_id}_{job_id}",
                    "company":     company["name"],
                    "title":       title,
                    "location":    location or "India",
                    "url":         job_url,
                    "description": clean[:3000],
                    "source":      "greenhouse",
                })

        logger.info(
            f"[Greenhouse] {company['name']}: "
            f"{len(jobs)} total, {len(matched)} matched"
        )
        return matched

    except requests.exceptions.HTTPError as e:
        logger.error(f"[Greenhouse] {company['name']} HTTP {e.response.status_code}: {e}")
        return None
    except requests.exceptions.Timeout:
        logger.error(f"[Greenhouse] {company['name']}: request timed out")
        return None
    except Exception as e:
        logger.error(f"[Greenhouse] {company['name']} failed: {e}")
        return None


# ─── Lever ────────────────────────────────────────────────────────────────────

def scrape_lever(company: dict) -> list[dict] | None:
    """
    Fetch all jobs from Lever public postings API.
    Returns list of matched jobs, or None on hard failure.
    Empty list [] means the API worked — just no matching roles today.
    """
    lever_id = company.get("lever_id", "")
    if not lever_id:
        logger.error(f"[Lever] {company['name']}: missing lever_id in config")
        return None

    url     = f"https://api.lever.co/v0/postings/{lever_id}?mode=json"
    matched = []

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
        jobs = resp.json()

        if not isinstance(jobs, list):
            logger.error(f"[Lever] {company['name']}: unexpected response format")
            return None

        for job in jobs:
            title    = job.get("text", "")
            cats     = job.get("categories", {})
            location = cats.get("location", "") or ""
            job_url  = job.get("hostedUrl", "")
            job_id   = job.get("id", "")
            desc_raw = job.get("descriptionPlain", "") or ""
            description = desc_raw[:3000]

            if _role_matches(title) and _location_matches(location):
                matched.append({
                    "id":          f"lv_{lever_id}_{job_id}",
                    "company":     company["name"],
                    "title":       title,
                    "location":    location or "India",
                    "url":         job_url,
                    "description": description,
                    "source":      "lever",
                })

        logger.info(
            f"[Lever] {company['name']}: "
            f"{len(jobs)} total, {len(matched)} matched"
        )
        return matched

    except requests.exceptions.HTTPError as e:
        logger.error(f"[Lever] {company['name']} HTTP {e.response.status_code}: {e}")
        return None
    except requests.exceptions.Timeout:
        logger.error(f"[Lever] {company['name']}: request timed out")
        return None
    except Exception as e:
        logger.error(f"[Lever] {company['name']} failed: {e}")
        return None
