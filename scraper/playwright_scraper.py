# playwright_scraper.py — Handles JS-rendered pages using headless Chromium
# Returns list of (company_name, jobs_or_None) tuples for health tracking

import asyncio
import logging
import re
from playwright.async_api import async_playwright, TimeoutError as PWTimeout
from scraper.config import ROLE_KEYWORDS, INDIA_LOCATIONS, SCRAPE_DELAY

logger = logging.getLogger(__name__)

# Broad search keywords used when the URL has a {role} placeholder.
# Kept broad intentionally — filtering happens via ROLE_KEYWORDS after scraping.
SEARCH_KEYWORDS = [
    "Software Engineer",
    "Data Engineer",
    "ML Engineer",
    "Data Scientist",
    "DevOps",
    "Cloud Engineer",
]


def _role_matches(title: str) -> bool:
    title_lower = title.lower()
    return any(kw.lower() in title_lower for kw in ROLE_KEYWORDS)


def _location_matches(location: str) -> bool:
    if not location:
        return True   # no location listed → include; let user verify
    return any(loc in location.lower() for loc in INDIA_LOCATIONS)


def _build_url(template: str, role: str) -> str:
    return template.replace("{role}", role.replace(" ", "+"))


# ─── Per-ATS page parsers ──────────────────────────────────────────────────────

async def _parse_workday(page, company_name: str) -> list[dict]:
    """Extract jobs from a Workday job search page."""
    jobs = []
    try:
        await page.wait_for_selector("[data-automation-id='jobTitle']", timeout=15000)
        items = await page.query_selector_all("li[class*='css-']")
        for item in items:
            title_el = await item.query_selector("[data-automation-id='jobTitle']")
            loc_el   = await item.query_selector("[data-automation-id='jobPostingLocation']")
            link_el  = await item.query_selector("a")
            title    = await title_el.inner_text() if title_el else ""
            location = await loc_el.inner_text()   if loc_el   else ""
            href     = await link_el.get_attribute("href") if link_el else ""
            if _role_matches(title) and _location_matches(location):
                jobs.append({
                    "title":    title.strip(),
                    "location": location.strip(),
                    "url":      href if href.startswith("http") else f"https://{href.lstrip('/')}",
                })
    except PWTimeout:
        logger.warning(f"[Workday] {company_name}: timeout waiting for job list")
    except Exception as e:
        logger.error(f"[Workday] {company_name}: {e}")
    return jobs


async def _parse_generic(page, company_name: str) -> list[dict]:
    """
    Generic parser — tries common job listing selectors.
    Works on most Lever-hosted, Greenhouse-hosted, and custom career pages.
    """
    jobs = []
    try:
        await page.wait_for_load_state("networkidle", timeout=20000)
        await asyncio.sleep(2)   # allow JS-rendered content to settle

        # Try selectors in priority order — stop at first that returns results
        selectors = [
            "a[href*='/job/']",
            "a[href*='/jobs/']",
            "a[href*='/careers/']",
            "a[href*='/position']",
            "a[href*='/opening']",
            "a[href*='/role']",
            ".job-title a",
            ".posting-title",
            "[class*='job'] a",
            "[class*='position'] a",
            "[class*='role'] a",
        ]

        found_links = []
        for sel in selectors:
            els = await page.query_selector_all(sel)
            if els:
                found_links = els
                break

        seen_titles: set[str] = set()
        for el in found_links:
            text = (await el.inner_text()).strip()
            href = await el.get_attribute("href") or ""
            if not text or len(text) < 4 or text.lower() in seen_titles:
                continue
            seen_titles.add(text.lower())

            if _role_matches(text):
                # Look for location in the nearest list item / row / card parent
                location = ""
                parent = await el.evaluate_handle(
                    "el => el.closest('li, tr, div[class*=\"job\"], div[class*=\"posting\"], div[class*=\"card\"]')"
                )
                if parent:
                    parent_text = await parent.evaluate("el => el ? el.innerText : ''")
                    for loc in INDIA_LOCATIONS:
                        if loc in parent_text.lower():
                            location = loc.title()
                            break

                if _location_matches(location):
                    full_url = href
                    if href and not href.startswith("http"):
                        base     = page.url.rstrip("/")
                        full_url = base + "/" + href.lstrip("/")
                    jobs.append({
                        "title":    text,
                        "location": location or "India (verify)",
                        "url":      full_url,
                    })

    except PWTimeout:
        logger.warning(f"[Generic] {company_name}: page load timeout")
    except Exception as e:
        logger.error(f"[Generic] {company_name}: {e}")

    return jobs


# ─── Per-company Playwright runner ────────────────────────────────────────────

async def _scrape_company(browser, company: dict) -> list[dict]:
    """Scrape a single company's career page. Returns matched job list."""
    ats          = company["ats"]
    name         = company["name"]
    url_template = company["url"]
    matched      = []
    seen_titles: set[str] = set()

    # Build list of URLs to try (multiple if template has {role})
    if "{role}" in url_template:
        urls = list({_build_url(url_template, kw) for kw in SEARCH_KEYWORDS})
    else:
        urls = [url_template]

    for url in urls:
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            java_script_enabled=True,
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()

        try:
            await page.goto(url, timeout=30000, wait_until="domcontentloaded")

            raw_jobs = (
                await _parse_workday(page, name)
                if ats == "workday"
                else await _parse_generic(page, name)
            )

            for job in raw_jobs:
                key = job["title"].lower().strip()
                if key not in seen_titles:
                    seen_titles.add(key)
                    job_id = re.sub(r"\W+", "_", f"{name}_{job['title']}").lower()[:80]
                    matched.append({
                        "id":          f"pw_{job_id}",
                        "company":     name,
                        "title":       job["title"],
                        "location":    job.get("location", "India"),
                        "url":         job.get("url", url),
                        "description": "",
                        "source":      "playwright",
                    })

        except Exception as e:
            logger.error(f"[Playwright] {name} @ {url}: {e}")
        finally:
            await page.close()
            await context.close()

        await asyncio.sleep(SCRAPE_DELAY)

    logger.info(f"[Playwright] {name}: {len(matched)} matched")
    return matched


# ─── Concurrent runner ────────────────────────────────────────────────────────

async def _scrape_all(companies: list[dict]) -> list[tuple]:
    """
    Scrape all companies concurrently, max 3 browsers at once.
    Returns list of (company_name, jobs_or_None) tuples.
    None means a hard error — used by health tracking.
    """
    semaphore = asyncio.Semaphore(3)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
        )

        async def bounded(company):
            async with semaphore:
                try:
                    jobs = await _scrape_company(browser, company)
                    return (company["name"], jobs)
                except Exception as e:
                    logger.error(f"[Playwright] {company['name']} hard error: {e}")
                    return (company["name"], None)

        results = await asyncio.gather(*[bounded(c) for c in companies])
        await browser.close()

    return list(results)


def scrape_playwright(companies: list[dict]) -> list[tuple]:
    """Synchronous entry point for Playwright scraping."""
    return asyncio.run(_scrape_all(companies))
