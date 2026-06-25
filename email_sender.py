"""
Summit Tax Services — Email Sender Module
Supports SMTP (HostGator) and SendGrid.
"""

import smtplib
import ssl
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from datetime import datetime

# Configuration — set via environment variables or defaults
SMTP_HOST = os.environ.get('SMTP_HOST', 'mail.taxesrx.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 465))
SMTP_USER = os.environ.get('SMTP_USER', 'info@taxesrx.com')
SMTP_PASS = os.environ.get('SMTP_PASS', '')  # Must be set
FROM_NAME = os.environ.get('FROM_NAME', 'Summit Tax Services')
FROM_EMAIL = os.environ.get('FROM_EMAIL', 'info@taxesrx.com')

SENDGRID_API_KEY = os.environ.get('SENDGRID_API_KEY', '')


def send_email(to_email, to_name, subject, html_body, attachments=None):
    """
    Send an email with optional PDF attachments.
    Works with SMTP (HostGator) or SendGrid.
    Returns True on success, False on failure.
    """
    if SENDGRID_API_KEY:
        return _send_via_sendgrid(to_email, to_name, subject, html_body, attachments)
    else:
        return _send_via_smtp(to_email, to_name, subject, html_body, attachments)


def _send_via_smtp(to_email, to_name, subject, html_body, attachments):
    """Send via SMTP (HostGator)."""
    if not SMTP_PASS:
        print("WARNING: SMTP_PASS not set. Email would be sent but cannot authenticate.")
        # For development, just log what would be sent
        print(f"  To: {to_name} <{to_email}>")
        print(f"  Subject: {subject}")
        print(f"  Attachments: {attachments}")
        return True

    msg = MIMEMultipart()
    msg['From'] = f'{FROM_NAME} <{FROM_EMAIL}>'
    msg['To'] = f'{to_name} <{to_email}>'
    msg['Subject'] = subject
    msg.attach(MIMEText(html_body, 'html'))

    # Add PDF attachments
    if attachments:
        for filepath in attachments:
            if os.path.exists(filepath):
                with open(filepath, 'rb') as f:
                    part = MIMEApplication(f.read(), Name=os.path.basename(filepath))
                part['Content-Disposition'] = f'attachment; filename="{os.path.basename(filepath)}"'
                msg.attach(part)

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"SMTP error: {e}")
        return False


def _send_via_sendgrid(to_email, to_name, subject, html_body, attachments):
    """Send via SendGrid API."""
    if not SENDGRID_API_KEY:
        return False

    import urllib.request
    import json
    import base64

    data = {
        "personalizations": [{
            "to": [{"email": to_email, "name": to_name}],
            "subject": subject,
        }],
        "from": {"email": FROM_EMAIL, "name": FROM_NAME},
        "content": [{"type": "text/html", "value": html_body}],
    }

    # Add attachments
    if attachments:
        att_list = []
        for filepath in attachments:
            if os.path.exists(filepath):
                with open(filepath, 'rb') as f:
                    b64 = base64.b64encode(f.read()).decode()
                att_list.append({
                    "content": b64,
                    "filename": os.path.basename(filepath),
                    "type": "application/pdf",
                    "disposition": "attachment"
                })
        if att_list:
            data["attachments"] = att_list

    req = urllib.request.Request(
        "https://api.sendgrid.com/v3/mail/send",
        data=json.dumps(data).encode(),
        headers={
            "Authorization": f"Bearer {SENDGRID_API_KEY}",
            "Content-Type": "application/json"
        },
        method="POST"
    )

    try:
        resp = urllib.request.urlopen(req)
        return resp.status in (200, 201, 202)
    except urllib.error.HTTPError as e:
        print(f"SendGrid error: {e.code} - {e.read().decode()[:200]}")
        return False


def send_guide_email(to_email, to_name, guide_pdf_path):
    """Send the personalized MaxSS guide PDF to a client."""
    subject = "Your Free Social Security Guide — Prepared for " + to_name
    html_body = f"""
    <div style="font-family: Georgia, serif; max-width: 600px; margin: 0 auto; color: #2c3345;">
      <div style="background: #1a2744; padding: 24px; border-radius: 8px 8px 0 0; text-align: center;">
        <h1 style="color: #f5f0e7; margin: 0; font-size: 22pt;">Summit Tax Services</h1>
        <p style="color: #c9a84c; font-size: 10pt; letter-spacing: 3px; text-transform: uppercase; margin: 8px 0 0;">Social Security Maximization</p>
      </div>
      <div style="padding: 28px 24px; background: #faf8f4; border-radius: 0 0 8px 8px;">
        <p style="font-size: 14pt;">{to_name},</p>
        <p style="font-size: 11pt; line-height: 1.7;">Your personalized copy of <strong>The Maximizer's Guide to Social Security</strong> is attached. Inside, you'll discover:</p>
        <ul style="font-size: 11pt; line-height: 1.8; color: #2c3345;">
          <li>Why <strong>96% of retirees</strong> leave money on the table</li>
          <li>How your own savings can <strong>tax your Social Security at 85%</strong></li>
          <li>The <strong>widow tax hit</strong> — paying more on less income</li>
          <li>The <strong>Roth conversion</strong> that un-taxes your Social Security</li>
        </ul>
        <p style="font-size: 11pt; line-height: 1.7;">The guide includes <strong>links to free calculators</strong> where you can run your own numbers — no email required, no sign-up.</p>
        <div style="background: #1a2744; border: 2px solid #c9a84c; border-radius: 6px; padding: 18px; text-align: center; margin: 20px 0;">
          <a href="https://taxesrx.com/maxss" style="display: inline-block; background: #c9a84c; color: #1a2744; font-family: Arial, sans-serif; font-size: 10pt; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; padding: 12px 28px; border-radius: 4px; text-decoration: none;">Book Your Free Strategy Session</a>
        </div>
        <p style="font-size: 11pt; line-height: 1.7;">Every month you wait costs you <strong>$500–$1,500 in permanently lost benefits</strong>. The clock is running.</p>
        <hr style="border: none; height: 1px; background: #e8e0d0; margin: 20px 0;">
        <p style="font-size: 9pt; color: #5a6070;">Summit Tax Services | taxesrx.com | myrothrx.com<br>
        Roth conversions. Tax strategy. Retirement confidence.</p>
      </div>
    </div>
    """
    return send_email(to_email, to_name, subject, html_body, [guide_pdf_path])


def send_report_email(to_email, to_name, calculator_name, report_pdf_path):
    """Send a personalized calculator report PDF to a client."""
    calc_titles = {
        'ss-calculator': 'Social Security Claiming Strategy',
        'torpedo-calculator': 'Tax Torpedo Analysis',
        'capital-gains': 'Capital Gains Bump Zone',
    }
    title = calc_titles.get(calculator_name, calculator_name)

    subject = f"Your {title} Report — Prepared for {to_name}"
    html_body = f"""
    <div style="font-family: Georgia, serif; max-width: 600px; margin: 0 auto; color: #2c3345;">
      <div style="background: #1a2744; padding: 24px; border-radius: 8px 8px 0 0; text-align: center;">
        <h1 style="color: #f5f0e7; margin: 0; font-size: 22pt;">Summit Tax Services</h1>
        <p style="color: #c9a84c; font-size: 10pt; letter-spacing: 3px; text-transform: uppercase; margin: 8px 0 0;">{title}</p>
      </div>
      <div style="padding: 28px 24px; background: #faf8f4; border-radius: 0 0 8px 8px;">
        <p style="font-size: 14pt;">{to_name},</p>
        <p style="font-size: 11pt; line-height: 1.7;">Your personalized <strong>{title}</strong> report is attached. This report was generated using the numbers you entered in our calculator, along with a detailed explanation of the strategies that apply to your situation.</p>
        <p style="font-size: 11pt; line-height: 1.7;">The report includes:</p>
        <ul style="font-size: 11pt; line-height: 1.8; color: #2c3345;">
          <li>Your specific numbers and calculations</li>
          <li>A plain-English explanation of what they mean</li>
          <li>Strategy recommendations for your situation</li>
          <li>Your next steps</li>
        </ul>
        <div style="background: #1a2744; border: 2px solid #c9a84c; border-radius: 6px; padding: 18px; text-align: center; margin: 20px 0;">
          <p style="color: #c9a84c; font-family: Arial, sans-serif; font-size: 9pt; letter-spacing: 2px; text-transform: uppercase; margin: 0 0 8px;">Ready to see the full picture?</p>
          <a href="https://taxesrx.com/maxss" style="display: inline-block; background: #c9a84c; color: #1a2744; font-family: Arial, sans-serif; font-size: 10pt; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; padding: 12px 28px; border-radius: 4px; text-decoration: none;">Book Your Free Strategy Session</a>
        </div>
        <hr style="border: none; height: 1px; background: #e8e0d0; margin: 20px 0;">
        <p style="font-size: 9pt; color: #5a6070;">Summit Tax Services | taxesrx.com | myrothrx.com<br>
        Roth conversions. Tax strategy. Retirement confidence.</p>
      </div>
    </div>
    """
    return send_email(to_email, to_name, subject, html_body, [report_pdf_path])
