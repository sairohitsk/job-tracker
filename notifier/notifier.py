# notifier.py — Gmail email notifications for new job matches
# Telegram is disabled. Only GMAIL_APP_PASSWORD secret is required.

import os
import re
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from scraper.config import RECIPIENT_EMAIL, SENDER_EMAIL

logger = logging.getLogger(__name__)


def _send_email(subject: str, html: str) -> bool:
    """Core email sender — used by all notification functions."""
    app_password = os.environ.get("GMAIL_APP_PASSWORD", "")
    if not app_password:
        logger.warning("GMAIL_APP_PASSWORD not set — skipping email")
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
        logger.error("[Email] Authentication failed — check GMAIL_APP_PASSWORD secret")
        return False
    except Exception as e:
        logger.error(f"[Email] Send failed: {e}")
        return False


def send_digest_email(new_jobs: list[dict]) -> bool:
    """
    Send a single HTML digest email listing all new jobs found this run.
    Called once per run — not once per job.
    """
    if not new_jobs:
        return True

    rows = ""
    for job in new_jobs:
        desc       = job.get("description", "")
        desc_clean = re.sub(r"<[^>]+>", " ", desc).strip()[:300] if desc else ""
        desc_cell  = (
            f'<div style="font-size:11px; color:#888; margin-top:4px;">'
            f'{desc_clean}…</div>'
            if desc_clean else ""
        )
        rows += f"""
        <tr>
            <td style="padding:12px 8px; border-bottom:1px solid #eee; vertical-align:top;">
                <strong>{job['company']}</strong>
            </td>
            <td style="padding:12px 8px; border-bottom:1px solid #eee; vertical-align:top;">
                {job['title']}{desc_cell}
            </td>
            <td style="padding:12px 8px; border-bottom:1px solid #eee; vertical-align:top; white-space:nowrap;">
                {job.get('location', 'India')}
            </td>
            <td style="padding:12px 8px; border-bottom:1px solid #eee; vertical-align:top;">
                <a href="{job['url']}" style="color:#0066cc; white-space:nowrap;">Apply →</a>
            </td>
        </tr>"""

    html = f"""
    <html><body style="font-family:Arial,sans-serif; max-width:750px; margin:auto; padding:20px;">
        <div style="background:#0066cc; padding:20px; border-radius:8px 8px 0 0;">
            <h2 style="color:white; margin:0;">🔔 Job Tracker — {len(new_jobs)} new match(es)</h2>
        </div>
        <div style="background:white; border:1px solid #ddd; border-top:none; padding:24px;
                    border-radius:0 0 8px 8px; overflow-x:auto;">
            <table style="width:100%; border-collapse:collapse; min-width:500px;">
                <thead>
                    <tr style="background:#f5f5f5;">
                        <th style="padding:10px 8px; text-align:left; color:#666; width:140px;">Company</th>
                        <th style="padding:10px 8px; text-align:left; color:#666;">Role</th>
                        <th style="padding:10px 8px; text-align:left; color:#666; width:130px;">Location</th>
                        <th style="padding:10px 8px; text-align:left; color:#666; width:70px;">Link</th>
                    </tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
        </div>
        <p style="text-align:center; color:#aaa; font-size:11px; margin-top:12px;">
            Job Tracker — running hourly on GitHub Actions
        </p>
    </body></html>
    """

    subject = f"[Job Tracker] {len(new_jobs)} new job(s) found"
    logger.info(f"[Email] Sending digest: {len(new_jobs)} jobs to {RECIPIENT_EMAIL}")
    ok = _send_email(subject, html)
    if ok:
        logger.info("[Email] Digest sent successfully")
    return ok
