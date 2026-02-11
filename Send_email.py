#发邮件引用的库
import smtplib
from email.mime.text import MIMEText

from config_store import load_config


def send_email(title, content):
    config = load_config()
    email_config = config.get("email", {})
    mail_host = email_config.get("mail_host", "smtp.qq.com")
    mail_user = email_config.get("mail_user", "")
    mail_pass = email_config.get("mail_pass", "")
    sender = email_config.get("sender", "")
    receivers = email_config.get("receivers", [])

    if isinstance(receivers, str):
        receivers = [item.strip() for item in receivers.split(",") if item.strip()]

    if not (mail_user and mail_pass and sender and receivers):
        print("Email settings are incomplete. Please update config.json.")
        return False

    message = MIMEText(content, "plain", "utf-8")
    message["From"] = "{}".format(sender)
    message["To"] = ",".join(receivers)
    message["Subject"] = title
    try:
        smtpObj = smtplib.SMTP_SSL(mail_host, 465)
        smtpObj.login(mail_user, mail_pass)
        smtpObj.sendmail(sender, receivers, message.as_string())
        print("email send successful!")
        return True
    except smtplib.SMTPException as e:
        print(e)
        return False


if __name__ == "__main__":
    send_email('title','content')