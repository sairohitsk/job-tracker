# health_notifier.py — Gmail email alerts for broken and recovered scrapers
# Telegram is disabled. Only GMAIL_APP_PASSWORD secret is required.

import os
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from scraper.config import RECIPIENT_EMAIL, SENDER_EMAIL

logger = logging.getLogger(__name__)


def _send_email(subject: str, html: str) -> bool:
    """Core email sender."""
    app_password = os.environ.get("GMAIL_APP_PASSWORD", "")
    if not app_password:
        logger.warning("GMAIL_APP_PASSWORD not set — skipping health email")
        return False
    msg            = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = SENDER_EMAIL
    msg["To"]      = RECIPIENT_EMAIL
    msg.attach(MIMEText(html, "html"))
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SENDER_EMAIL, app_password)
            server.sendmail(SENDER_EMAIL, RECIPIENT_EMAIL, msg.as_string())
        return True
    except smtplib.SMTPAuthenticationError:
        logger.error("[HealthEmail] Authentication failed — check GMAIL_APP_PASSWORD secret")
        return False
    except Exception as e:
        logger.error(f"[HealthEmail] Send failed: {e}")
        return False


def send_broken_email(broken: list[dict]) -> bool:
    """
    Send an alert email when scrapers have failed 3+ consecutive hourly runs.
    Includes a fix guide so you know exactly what to check.
    """
    if not broken:
        return True

    rows = ""
    for b in broken:
        rows += f"""
        <tr>
            <td style="padding:10px 8px; border-bottom:1px solid #eee;">
                ❌ <strong>{b['company']}</strong>
            </td>
            <td style="padding:10px 8px; border-bottom:1px solid #eee;
                       color:#cc0000; font-weight:bold;">
                {b['failures']} consecutive runs
            </td>
            <td style="padding:10px 8px; border-bottom:1px solid #eee; color:#888;">
                {b['last_error']}
            </td>
        </tr>"""

    html = f"""
    <html><body style="font-family:Arial,sans-serif; max-width:700px; margin:auto; padding:20px;">
        <div style="background:#cc0000; padding:20px; border-radius:8px 8px 0 0;">
            <h2 style="color:white; margin:0;">⚠️ Scraper Alert — {len(broken)} broken scraper(s)</h2>
        </div>
        <div style="background:white; border:1px solid #ddd; border-top:none;
                    padding:24px; border-radius:0 0 8px 8px;">
            <p style="color:#555; margin-top:0;">
                The following scrapers have failed
                <strong>{broken[0]['failures']}+ consecutive hourly runs</strong>.
                This usually means the career page URL changed, the ATS was updated,
                or the site is temporarily blocking requests.
            </p>
            <table style="width:100%; border-collapse:collapse;">
                <thead>
                    <tr style="background:#f5f5f5;">
                        <th style="padding:10px 8px; text-align:left; color:#666;">Company</th>
                        <th style="padding:10px 8px; text-align:left; color:#666;">Failures</th>
                        <th style="padding:10px 8px; text-align:left; color:#666;">Reason</th>
                    </tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
            <div style="margin-top:24px; padding:16px; background:#fff8e1;
                        border-left:4px solid #f9a825; border-radius:4px;">
                <strong>How to fix:</strong>
                <ol style="margin:8px 0 0 0; padding-left:20px; color:#555; line-height:1.9;">
                    <li>Open <code>scraper/companies.py</code> in your GitHub repo</li>
                    <li>Find the company entry and open its URL in a browser to check it still works</li>
                    <li>For <strong>Greenhouse</strong>: confirm the <code>greenhouse_id</code> slug is correct</li>
                    <li>For <strong>Lever</strong>: confirm the <code>lever_id</code> slug is correct</li>
                    <li>For <strong>Playwright/Workday</strong>: the page layout may have changed — update the URL</li>
                    <li>Commit the fix and trigger a manual run from the Actions tab to verify</li>
                </ol>
            </div>
        </div>
        <p style="text-align:center; color:#aaa; font-size:11px; margin-top:12px;">
            Job Tracker Health Monitor — running hourly on GitHub Actions
        </p>
    </body></html>
    """

    subject = f"[Job Tracker] ⚠️ {len(broken)} broken scraper(s) detected"
    ok = _send_email(subject, html)
    if ok:
        logger.info(f"[HealthEmail] Broken alert sent: {len(broken)} companies")
    return ok


def send_recovered_email(recovered: list[str]) -> bool:
    """Send a confirmation email when previously broken scrapers start working again."""
    if not recovered:
        return True

    items = "".join(
        f'<li style="padding:6px 0; color:#2e7d32;">✅ {name}</li>'
        for name in recovered
    )
    html = f"""
    <html><body style="font-family:Arial,sans-serif; max-width:600px; margin:auto; padding:20px;">
        <div style="background:#2e7d32; padding:20px; border-radius:8px 8px 0 0;">
            <h2 style="color:white; margin:0;">✅ {len(recovered)} Scraper(s) Recovered</h2>
        </div>
        <div style="background:white; border:1px solid #ddd; border-top:none;
                    padding:24px; border-radius:0 0 8px 8px;">
            <p style="color:#555; margin-top:0;">
                The following scrapers were previously failing but are now working again:
            </p>
            <ul style="padding-left:20px; line-height:1.9;">{items}</ul>
        </div>
        <p style="text-align:center; color:#aaa; font-size:11px; margin-top:12px;">
            Job Tracker Health Monitor — running hourly on GitHub Actions
        </p>
    </body></html>
    """

    subject = f"[Job Tracker] ✅ {len(recovered)} scraper(s) recovered"
    ok = _send_email(subject, html)
    if ok:
        logger.info(f"[HealthEmail] Recovery alert sent: {', '.join(recovered)}")
    return ok
