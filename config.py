import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.makedirs(os.path.join(BASE_DIR, 'database'), exist_ok=True)
DB_PATH = os.path.join(BASE_DIR, 'database', 'dialogs.db') 