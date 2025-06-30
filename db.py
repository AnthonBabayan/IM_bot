import os
import sqlite3
from datetime import datetime
from config import DB_PATH

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_folder = os.path.join(BASE_DIR, 'database')
os.makedirs(db_folder, exist_ok=True)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS dialogs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            type TEXT,
            description TEXT,
            photo_paths TEXT,
            status TEXT,
            created_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

def save_dialog_to_db(user_id, username, type_, description, photo_paths, status):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        INSERT INTO dialogs (user_id, username, type, description, photo_paths, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        user_id,
        username,
        type_,
        description,
        ','.join(photo_paths) if photo_paths else '',
        status,
        datetime.now().isoformat()
    ))
    conn.commit()
    conn.close() 

def add_unreachable_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS unreachable_users (user_id INTEGER PRIMARY KEY)')
    c.execute('INSERT OR IGNORE INTO unreachable_users (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

def is_unreachable_user(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS unreachable_users (user_id INTEGER PRIMARY KEY)')
    c.execute('SELECT 1 FROM unreachable_users WHERE user_id=?', (user_id,))
    result = c.fetchone()
    conn.close()
    return result is not None

def has_evaluation(num, user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('SELECT 1 FROM evaluations WHERE num=? AND user_id=?', (num, user_id))
    result = c.fetchone()
    conn.close()
    return result is not None

# logger.error(f"Ошибка работы с базой данных: {e}") 