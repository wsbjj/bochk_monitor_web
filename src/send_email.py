"""
Email sending module with support for multiple email providers.
Supports: QQ, Gmail, Outlook, Office365
"""
import smtplib
from email.mime.text import MIMEText
import resend
import os

from .config import load_config


# Email provider configurations
EMAIL_PROVIDERS = {
    "smtp.qq.com": {"ssl_port": 465, "tls_port": 587},
    "smtp.163.com": {"ssl_port": 465, "tls_port": 25},
    "smtp.gmail.com": {"ssl_port": 465, "tls_port": 587},
    "smtp.office365.com": {"ssl_port": 465, "tls_port": 587},
    "smtp-mail.outlook.com": {"ssl_port": 465, "tls_port": 587},
}


def send_email(title, content):
    """
    Send email notification.
    
    Args:
        title: Email subject
        content: Email body text
        
    Returns:
        bool: True if sent successfully, False otherwise
    """
    config = load_config()
    email_config = config.get("email", {})
    mail_host = email_config.get("mail_host", "smtp.qq.com")
    mail_port = email_config.get("mail_port", None)
    mail_user = email_config.get("mail_user", "")
    mail_pass = email_config.get("mail_pass", "")
    sender = email_config.get("sender", "")
    receivers = email_config.get("receivers", [])

    # Handle receivers as string
    if isinstance(receivers, str):
        receivers = [item.strip() for item in receivers.split(",") if item.strip()]

    # Validate configuration
    if not (mail_user and mail_pass and sender and receivers):
        print("Email settings are incomplete. Please update config.json.")
        return False

    # Auto-detect port if not specified
    if mail_port is None:
        if mail_host in EMAIL_PROVIDERS:
            # Outlook/Office365 prefers TLS (587), others prefer SSL (465)
            if "outlook" in mail_host.lower() or "office365" in mail_host.lower():
                mail_port = EMAIL_PROVIDERS[mail_host]["tls_port"]
            else:
                mail_port = EMAIL_PROVIDERS[mail_host]["ssl_port"]
        else:
            # Unknown provider, default to SSL
            mail_port = 465

    # Build email message
    message = MIMEText(content, "plain", "utf-8")
    message["From"] = sender
    message["To"] = ",".join(receivers)
    message["Subject"] = title
    
    try:
        # Choose connection method based on port
        if mail_port == 587:
            # TLS method (Outlook recommended)
            smtp_obj = smtplib.SMTP(mail_host, mail_port, timeout=10)
            smtp_obj.starttls()  # Enable TLS encryption
        else:
            # SSL method (QQ, Gmail, etc.)
            smtp_obj = smtplib.SMTP_SSL(mail_host, mail_port, timeout=10)
        
        smtp_obj.login(mail_user, mail_pass)
        smtp_obj.sendmail(sender, receivers, message.as_string())
        smtp_obj.quit()
        print("Email sent successfully!")
        return True
    except Exception as e:
        print(f"SMTP Error: {e}")
        print("Attempting to send via Resend fallback...")
        return send_via_resend(title, content, receivers)


def send_via_resend(title, content, receivers):
    """
    Send email using Resend API as a fallback.
    """
    try:
        api_key = os.getenv("RESEND_API_KEY")
        if not api_key:
            print("RESEND_API_KEY not found in environment variables.")
            return False
            
        resend.api_key = api_key
        
        # Format content as HTML since Resend prefers it, or supports it
        html_content = f"<p>{content}</p>"
        
        params = {
            "from": "onboarding@resend.dev",
            "to": receivers,
            "subject": title,
            "html": html_content
        }
        
        r = resend.Emails.send(params)
        print(f"Resend email sent: {r}")
        return True
    except Exception as e:
        print(f"Resend Error: {e}")
        return False


if __name__ == "__main__":
    send_email('test', 'test content')
