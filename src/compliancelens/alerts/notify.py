"""Alerting: Slack webhook first, plain SMTP email as fallback.

Both transports use only the stdlib so the module is unit-testable; the
Databricks notebook passes the webhook/secret at runtime, never hardcoded.
"""
from __future__ import annotations

import json
import smtplib
import urllib.request
from email.message import EmailMessage


def send_slack(webhook_url: str, text: str, timeout: int = 10) -> bool:
    payload = json.dumps({"text": text}).encode("utf-8")
    req = urllib.request.Request(webhook_url, data=payload,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except Exception:
        return False


def send_email(smtp_host: str, port: int, sender: str, password: str,
               recipients: list[str], subject: str, body: str,
               timeout: int = 15) -> bool:
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = sender, ", ".join(recipients), subject
    msg.set_content(body)
    try:
        with smtplib.SMTP(smtp_host, port, timeout=timeout) as s:
            s.starttls()
            s.login(sender, password)
            s.send_message(msg)
        return True
    except Exception:
        return False


def build_alert(run_id: str, score: float | None, threshold: float,
                top_findings: list[dict], headline: str = "ComplianceLens alert") -> str:
    lines = [f":rotating_light: *{headline}*", f"run_id: `{run_id}`"]
    if score is not None:
        lines.append(f"compliance score: *{score}* (threshold {threshold})")
    for f in top_findings[:5]:
        lines.append(f"- [{f.get('severity', 'info')}] {f.get('finding')}: "
                     f"{f.get('table')}.{f.get('column', '-')}")
    return "\n".join(lines)
