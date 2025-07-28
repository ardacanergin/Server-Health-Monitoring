"""
Mailer Class

This module defines the Mailer class, which provides functionality for sending emails
with optional HTML content and attachments. It supports both TLS and SSL connections
for SMTP servers.

Features:
---------
- Sends emails with:
    * Plain text body
    * Optional HTML body (for rich content)
    * File attachments (e.g., JSON/HTML reports)
    * CC and BCC recipients
- Supports STARTTLS and SSL for secure SMTP communication.
- Configurable sender name for emails.

Dependencies:
-------------
- smtplib: For SMTP connections and email delivery.
- email.mime: For constructing multipart emails with text and attachments.

Usage:
------
from mailer import Mailer

mailer = Mailer(
    smtp_server="smtp.example.com",
    smtp_port=587,
    username="your-email@example.com",
    password="yourpassword",
    use_tls=True
)

mailer.send_email(
    subject="Server Health Report",
    body="Please find attached the latest server health report.",
    recipients=["admin@example.com"],
    html_body="<h1>Server Health Report</h1><p>Details attached.</p>",
    attachments=["report.html", "report.json"]
)

Key Methods:
------------
- send_email(): Constructs and sends an email with optional HTML content and file attachments.

Notes:
------
- For Gmail and similar providers, you may need to generate an app-specific password
  if two-factor authentication is enabled.
- Designed to integrate with ReportBuilder and CombinedReportBuilder for sending monitoring reports.
"""

import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication

logger = logging.getLogger(__name__)

class Mailer:
    def __init__(self, smtp_server, smtp_port, username, password, use_tls=True):
        """
        :param smtp_server: SMTP server address (e.g., smtp.gmail.com)
        :param smtp_port: SMTP port (587 for TLS, 465 for SSL)
        :param username: SMTP username
        :param password: SMTP password or app-specific password
        :param use_tls: True for STARTTLS, False for SSL
        """
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.username = username
        self.password = password
        self.use_tls = use_tls


    def send_email(self, subject, body, recipients,
                   html_body=None, attachments=None,
                   cc=None, bcc=None, sender_name="Server Monitor"):
        """
        Send an email.

        :param subject: Email subject
        :param body: Plain text body
        :param recipients: List of recipient emails
        :param html_body: Optional HTML body
        :param attachments: Optional list of file paths to attach
        :param cc: Optional list of CC emails
        :param bcc: Optional list of BCC emails
        :param sender_name: Name displayed as sender
        """
        message = MIMEMultipart()
        message['From'] = f"{sender_name} <{self.username}>"
        message['To'] = ", ".join(recipients)
        if cc:
            message['Cc'] = ", ".join(cc)
        message['Subject'] = subject

        # Add plain text and optional HTML
        message.attach(MIMEText(body, 'plain'))
        if html_body:
            message.attach(MIMEText(html_body, 'html'))

        # Add attachments
        if attachments:
            for filepath in attachments:
                with open(filepath, "rb") as f:
                    part = MIMEApplication(f.read(), Name=filepath)
                part['Content-Disposition'] = f'attachment; filename="{filepath}"'
                message.attach(part)

        # Combine all recipients
        all_recipients = recipients + (cc or []) + (bcc or [])

        try:
            if self.use_tls:
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                server.starttls()
            else:
                server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)

            server.login(self.username, self.password)
            server.sendmail(self.username, all_recipients, message.as_string())
            server.quit()
            logger.info(f" Email sent to {', '.join(all_recipients)}")
        except Exception as e:
            logger.error(f" Failed to send email: {e}")