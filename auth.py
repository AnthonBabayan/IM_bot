import os
import sqlite3
import random
import string
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from ldap3 import Server, Connection, ALL
from config import DB_PATH

import logging
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_folder = os.path.join(BASE_DIR, 'database')
os.makedirs(db_folder, exist_ok=True)
DB_PATH = os.path.join(db_folder, 'dialogs.db')

# --- Настройки LDAP и SMTP ---
LDAP_HOST = 'YOUR_LDAP_HOST'  # Например, 'ldap://172.17.1.50'
LDAP_PORT = 389 # YOUR_LDAP_PORT
LDAP_USER = 'YOUR_LDAP_USER'  # Например, 'user@domain' или 'cn=...'
LDAP_PASSWORD = 'YOUR_LDAP_PASSWORD'
LDAP_BASE_DN = 'YOUR_LDAP_BASE_DN'  # Например, 'dc=gse,dc=globse,dc=local'

SMTP_SERVER = 'YOUR_SMTP_SERVER' # Например, 'smtp.example.com'
SMTP_PORT = 25 # YOUR_SMTP_PORT
SMTP_USER = 'YOUR_SMTP_USER' # Например, 'user@example.com'
SMTP_PASSWORD = 'YOUR_SMTP_PASSWORD'

# --- Таблица авторизации ---
def init_auth_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS auth (
            user_id INTEGER PRIMARY KEY,
            email TEXT,
            code TEXT,
            code_sent_at TEXT,
            token TEXT,
            expires_at TEXT,
            is_verified INTEGER,
            fio TEXT,
            location TEXT
        )
    ''')
    conn.commit()
    conn.close()

# --- LDAP проверка ---
def check_email_in_ldap(email):
    server = Server(LDAP_HOST, port=LDAP_PORT, get_info=ALL)
    conn = Connection(server, user=LDAP_USER, password=LDAP_PASSWORD, auto_bind=True)
    conn.search(LDAP_BASE_DN, f'(mail={email})', attributes=['mail'])
    found = len(conn.entries) > 0
    conn.unbind()
    return found

# --- Генерация и отправка кода ---
def generate_code(length=6):
    return ''.join(random.choices(string.digits, k=length))

def send_code_to_email(email, code):
    msg = MIMEMultipart()
    msg['From'] = SMTP_USER
    msg['To'] = email
    msg['Subject'] = 'Код подтверждения для Telegram бота'
    body = f'Ваш код подтверждения: {code}'
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.sendmail(SMTP_USER, email, msg.as_string())
    except Exception as e:
        logger.error(f"Ошибка отправки кода: {e}")
        raise

# --- Сохранение кода в БД ---
def save_code(user_id, email, code):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT OR REPLACE INTO auth (user_id, email, code, code_sent_at, is_verified)
        VALUES (?, ?, ?, ?, 0)
    ''', (user_id, email, code, datetime.now().isoformat()))
    conn.commit()
    conn.close()

# --- Проверка кода и выдача токена ---
def verify_code_and_issue_token(user_id, code):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT code, code_sent_at, email FROM auth WHERE user_id=?', (user_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return False, 'Сначала запросите код.'
    db_code, code_sent_at, email = row
    if db_code != code:
        conn.close()
        return False, 'Неверный код.'
    if datetime.fromisoformat(code_sent_at) + timedelta(minutes=10) < datetime.now():
        conn.close()
        return False, 'Срок действия кода истёк.'
    token = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
    expires_at = (datetime.now() + timedelta(days=180)).isoformat()
    from auth import get_user_info_from_ldap
    fio, location = get_user_info_from_ldap(email)
    c.execute('''
        UPDATE auth SET token=?, expires_at=?, is_verified=1, fio=?, location=? WHERE user_id=?
    ''', (token, expires_at, fio, location, user_id))
    conn.commit()
    conn.close()
    return True, token

# --- Проверка токена ---
def is_user_authorized(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT token, expires_at, is_verified FROM auth WHERE user_id=?', (user_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return False
    token, expires_at, is_verified = row
    if not token or not is_verified:
        return False
    if datetime.fromisoformat(expires_at) < datetime.now():
        return False
    return True

def get_user_info_from_ldap(email):
    server = Server(LDAP_HOST, port=LDAP_PORT, get_info=ALL)
    conn = Connection(server, user=LDAP_USER, password=LDAP_PASSWORD, auto_bind=True)
    conn.search(LDAP_BASE_DN, f'(mail={email})', attributes=['displayName', 'physicalDeliveryOfficeName'])
    if conn.entries:
        entry = conn.entries[0]
        fio = str(entry.displayName) if 'displayName' in entry else ''
        location = str(entry.physicalDeliveryOfficeName) if 'physicalDeliveryOfficeName' in entry else ''
        conn.unbind()
        return fio, location
    conn.unbind()
    return '', ''

def fill_fio_and_location_for_all():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT user_id, email FROM auth')
    users = c.fetchall()
    for user_id, email in users:
        fio, location = get_user_info_from_ldap(email)
        c.execute('UPDATE auth SET fio=?, location=? WHERE user_id=?', (fio, location, user_id))
    conn.commit()
    conn.close()

if __name__ == "__main__":
    fill_fio_and_location_for_all()
    print('fio и location обновлены для всех пользователей.')