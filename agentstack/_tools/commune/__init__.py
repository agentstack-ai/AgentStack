import os
import re
from commune import Commune

API_KEY = os.getenv('COMMUNE_API_KEY')


def send_email(to: str, subject: str, body: str) -> str:
    """
    Send an email using the Commune API.

    Commune provides AI agents with dedicated email addresses and a
    programmable API — not SMTP, not webmail, but an email layer built
    for agents. Use this tool when the agent needs to deliver a message,
    notification, or report to a recipient by email.

    Args:
        to: The recipient email address (e.g. user@example.com)
        subject: The subject line of the email
        body: The plain-text body content of the email

    Returns:
        A confirmation string containing the message ID and status,
        or an error description if sending fails
    """
    client = Commune(api_key=API_KEY)
    result = client.emails.send(to=to, subject=subject, body=body)
    return f"Email sent successfully. Message ID: {result['id']}, Status: {result['status']}"


def read_inbox(limit: int = 10) -> str:
    """
    Read recent emails from the Commune inbox.

    Fetches the most recent emails received by the agent's Commune
    email address. Use this tool when the agent needs to check for
    incoming messages, replies, or instructions delivered by email.

    Args:
        limit: Maximum number of emails to return (default 10, max 50)

    Returns:
        A numbered list of emails, each showing the sender, subject,
        received timestamp, and a short preview of the body. Returns
        a message if the inbox is empty.
    """
    client = Commune(api_key=API_KEY)
    emails = client.emails.list(limit=limit, unread_only=False)

    if not emails:
        return "Inbox is empty — no emails found."

    lines = []
    for idx, email in enumerate(emails, start=1):
        preview = email.get('body', '')[:120].replace('\n', ' ').strip()
        if len(email.get('body', '')) > 120:
            preview += '...'
        read_marker = '' if email.get('read') else ' [UNREAD]'
        lines.append(
            f"{idx}.{read_marker} From: {email['from_address']}\n"
            f"   Subject: {email['subject']}\n"
            f"   Received: {email['received_at']}\n"
            f"   Preview: {preview}"
        )

    return '\n\n'.join(lines)


def send_sms(to: str, body: str) -> str:
    """
    Send an SMS message using the Commune API.

    Sends a text message to a phone number via Commune's SMS service.
    Use this tool when the agent needs to deliver a time-sensitive
    alert, confirmation code, or short notification by SMS.

    Args:
        to: The recipient phone number in E.164 format (e.g. +15551234567).
            Must begin with '+' followed by the country code and number,
            with no spaces or dashes.
        body: The text message content to send (keep under 160 characters
              for a single SMS segment)

    Returns:
        A confirmation string with the message ID and status,
        or an error description if the number format is invalid or
        sending fails
    """
    # Validate E.164 format before hitting the API
    e164_pattern = re.compile(r'^\+[1-9]\d{1,14}$')
    if not e164_pattern.match(to):
        return (
            f"Invalid phone number format: '{to}'. "
            "SMS requires E.164 format — a '+' followed by country code and number "
            "with no spaces or dashes (e.g. +15551234567)."
        )

    client = Commune(api_key=API_KEY)
    result = client.sms.send(to=to, body=body)
    return f"SMS sent successfully. Message ID: {result['id']}, Status: {result['status']}"
