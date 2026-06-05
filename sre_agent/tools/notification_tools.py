"""Notification tools for the SRE Agent.

Sends incident status notifications via console logging (default)
and optionally via Slack webhooks.
"""

import json
import logging
from typing import Optional

import httpx

from sre_agent.config import get_settings

logger = logging.getLogger(__name__)


def send_notification(
    title: str,
    message: str,
    severity: str = "info",
    pr_url: Optional[str] = None,
    scaling_details: Optional[str] = None,
) -> dict:
    """Send a notification about incident mitigation actions taken.

    Use this tool after completing all mitigation actions (infrastructure scaling,
    code fix PR creation) to notify the operations team about what happened.

    Currently supports console logging (always) and Slack webhooks (if configured).

    Args:
        title: Notification title (e.g., 'Incident Mitigated').
        message: Detailed message about all actions taken by the agent.
        severity: Severity level — one of 'info', 'warning', or 'critical'.
        pr_url: URL of the created Pull Request, if any.
        scaling_details: Details of infrastructure scaling actions, if any.

    Returns:
        A dictionary containing:
        - success (bool): Whether the notification was sent successfully
        - channels (list): Which channels received the notification
        - message (str): Status message
    """
    settings = get_settings()
    channels_notified = []

    # Build the notification content
    severity_emoji = {"info": "ℹ️", "warning": "⚠️", "critical": "🚨"}.get(
        severity, "ℹ️"
    )

    notification_text = f"""
{'=' * 60}
{severity_emoji}  {title}
{'=' * 60}

{message}
"""

    if scaling_details:
        notification_text += f"\n☁️  Infrastructure Actions:\n{scaling_details}\n"

    if pr_url:
        notification_text += f"\n🐙 Code Fix PR: {pr_url}\n"

    notification_text += f"\n{'=' * 60}"

    # Always log to console
    log_func = {
        "info": logger.info,
        "warning": logger.warning,
        "critical": logger.critical,
    }.get(severity, logger.info)

    log_func(notification_text)
    channels_notified.append("console")

    # Send to Slack if configured
    if settings.slack_webhook_url:
        try:
            slack_payload = _build_slack_payload(
                title=title,
                message=message,
                severity=severity,
                pr_url=pr_url,
                scaling_details=scaling_details,
            )
            with httpx.Client(timeout=10) as client:
                response = client.post(
                    settings.slack_webhook_url,
                    json=slack_payload,
                )
                response.raise_for_status()
            channels_notified.append("slack")
            logger.info("📨 Slack notification sent successfully")
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")

    return {
        "success": True,
        "channels": channels_notified,
        "message": f"Notification sent to: {', '.join(channels_notified)}",
    }


def _build_slack_payload(
    title: str,
    message: str,
    severity: str,
    pr_url: Optional[str] = None,
    scaling_details: Optional[str] = None,
) -> dict:
    """Build a Slack Block Kit message payload."""
    severity_color = {
        "info": "#36a64f",
        "warning": "#ff9900",
        "critical": "#ff0000",
    }.get(severity, "#36a64f")

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"🤖 SRE Agent: {title}"},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": message},
        },
    ]

    if scaling_details:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*☁️ Infrastructure Actions:*\n{scaling_details}",
                },
            }
        )

    if pr_url:
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*🐙 Code Fix:* <{pr_url}|View Pull Request>",
                },
            }
        )

    blocks.append({"type": "divider"})
    blocks.append(
        {
            "type": "context",
            "elements": [
                {
                    "type": "mrkdwn",
                    "text": "_Powered by Autonomous SRE Agent | Google ADK + Gemini + Dynatrace MCP_",
                }
            ],
        }
    )

    return {
        "attachments": [{"color": severity_color, "blocks": blocks}],
    }
