import os
import sqlite3
from config import DB_PATH

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_folder = os.path.join(BASE_DIR, 'database')
os.makedirs(db_folder, exist_ok=True)

def clear_location_column():
    # Проверяем существование базы данных
    if not os.path.exists(DB_PATH):
        print(f'Ошибка: База данных {DB_PATH} не найдена')
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # Проверяем количество записей перед очисткой
        c.execute('SELECT COUNT(*) FROM auth')
        count = c.fetchone()[0]
        
        if count == 0:
            print('В таблице auth нет записей')
            return
            
        # Очищаем колонку location
        c.execute('UPDATE auth SET location = NULL')
        conn.commit()
        
        print(f'Колонка location очищена для {count} пользователей')
        
    except sqlite3.Error as e:
        print(f'Ошибка при работе с базой данных: {e}')
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    clear_location_column() 