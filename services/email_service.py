import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import logging

logger = logging.getLogger(__name__)

SMTP_SERVER = 'YOUR_SMTP_SERVER'
SMTP_PORT = 25
SMTP_USER = 'YOUR_SMTP_USER'
EMAIL_TO = 'email_for_tickets@example.com'

def send_support_email(subject: str, body: str, photo_paths=None, fio=None, location=None, email=None, tg_id=None):
    msg = MIMEMultipart()
    msg['From'] = SMTP_USER
    msg['To'] = EMAIL_TO
    msg['Subject'] = subject

    email_body = f"""Описание проблемы:
{body}

Информация о пользователе:
ФИО: {fio}
Рабочее место: {location}
Email: {email}
Telegram ID: {tg_id}"""
    msg.attach(MIMEText(email_body, 'plain'))

    if photo_paths:
        for path in photo_paths:
            with open(path, 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f'attachment; filename="{os.path.basename(path)}"')
                msg.attach(part)
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.sendmail(SMTP_USER, EMAIL_TO, msg.as_string())
    except Exception as e:
        logger.error(f"Ошибка отправки письма: {e}")
        raise

async def send_complaint_email(num, feedback, user_data):
    subject = f'Жалоба по заявке #{num}'
    body = f"""Пользователь оставил жалобу на решение заявки #{num}.
    
Текст жалобы:
{feedback}

Информация о пользователе:
ФИО: {user_data.get('fio')}
Рабочее место: {user_data.get('location')}
Email: {user_data.get('email')}
Telegram ID: {user_data.get('user_id')}
"""
    msg = MIMEMultipart()
    msg['From'] = SMTP_USER
    msg['To'] = EMAIL_TO
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.sendmail(SMTP_USER, EMAIL_TO, msg.as_string())
        logger.info(f"Жалоба по заявке #{num} отправлена на {EMAIL_TO}")
    except Exception as e:
        logger.error(f"Ошибка при отправке жалобы по заявке #{num}: {e}") 