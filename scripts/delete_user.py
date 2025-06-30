import os
import sqlite3
from config import DB_PATH

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_folder = os.path.join(BASE_DIR, 'database')
os.makedirs(db_folder, exist_ok=True)

def delete_user(user_id=None, email=None):
    if not user_id and not email:
        print('Укажите user_id или email для удаления пользователя.')
        return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if user_id:
        c.execute('DELETE FROM auth WHERE user_id = ?', (user_id,))
        print(f'Пользователь с user_id={user_id} удалён.')
    elif email:
        c.execute('DELETE FROM auth WHERE email = ?', (email,))
        print(f'Пользователь с email={email} удалён.')
    conn.commit()
    conn.close()

if __name__ == "__main__":
    # Замените значения ниже на нужные вам
    # delete_user(user_id=123456789)
    # delete_user(email='your_email@domain.com')
    print("Для удаления пользователя раскомментируйте и измените строку в `delete_user.py`") 