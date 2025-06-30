import os
import glob
from datetime import datetime, timedelta
import logging
import asyncio

logger = logging.getLogger(__name__)

PHOTO_DIR = 'photos'

def cleanup_old_photos():
    """Удаляет фотографии старше 180 дней."""
    cutoff = datetime.now() - timedelta(days=180)
    for photo_path in glob.glob(os.path.join(PHOTO_DIR, '*')):
        try:
            mtime = datetime.fromtimestamp(os.path.getmtime(photo_path))
            if mtime < cutoff:
                os.remove(photo_path)
                logger.info(f"Удалено старое фото: {photo_path}")
        except Exception as e:
            logger.error(f"Ошибка при удалении фото {photo_path}: {e}")

async def periodic_photos_cleanup():
    """Периодическая задача для очистки старых фотографий."""
    while True:
        cleanup_old_photos()
        # Пауза на 24 часа
        await asyncio.sleep(86400) 