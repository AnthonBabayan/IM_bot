import os
import logging
from logging.handlers import TimedRotatingFileHandler
import asyncio
import signal
import sys
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
)
from telegram.error import BadRequest, Forbidden
from config import DB_PATH
from db import init_db, add_unreachable_user, has_evaluation
from auth import init_auth_db
from constants import *
from keyboards import get_evaluation_keyboard
from handlers.auth_handlers import auth_start, auth_email_handler, auth_code_handler
from handlers.conversation_handlers import (
    start, type_callback, sw_callback, hw_callback, summary_handler, photo_upload_handler,
    confirm_callback, edit_description_callback, send_without_photo_callback,
    next_photo_upload_callback, attach_photo_callback, back_callback, restart_callback, cancel_callback
)
from handlers.evaluation_handlers import evaluation_callback, feedback_handler, noop_callback
from services.mail_checker import check_mail_and_notify_periodically
from services.cleanup_service import periodic_photos_cleanup, PHOTO_DIR

# --- Глобальные настройки ---
TG_TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'
LOG_DIR = '/path/to/your/logs/imbot/'

# --- Настройка логгирования ---
def setup_logging():
    os.makedirs(LOG_DIR, exist_ok=True)
    log_file = os.path.join(LOG_DIR, 'imbot.log')
    
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    file_handler = TimedRotatingFileHandler(
        log_file, when='M', interval=720, backupCount=7, encoding='utf-8'
    )
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    
    if not root_logger.handlers:
        root_logger.addHandler(file_handler)

    # Модульный логгер
    logger = logging.getLogger(__name__)

    def handle_exception(exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        logger.error("Необработанное исключение:", exc_info=(exc_type, exc_value, exc_traceback))

    sys.excepthook = handle_exception

# --- Обработчики ошибок ---
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Ошибка: {context.error}", exc_info=context.error)
    if isinstance(context.error, BadRequest):
        # обработка специфичных ошибок API
        pass
    elif isinstance(context.error, Forbidden):
        # пользователь заблокировал бота
        user_id = 0
        if isinstance(update, Update) and update.effective_user:
            user_id = update.effective_user.id
            add_unreachable_user(user_id)
            logger.warning(f"Пользователь {user_id} заблокировал бота.")

# --- Регистрация хендлеров ---
def register_handlers(app: ApplicationBuilder):
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', auth_start)],
        states={
            AUTH_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, auth_email_handler)],
            AUTH_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, auth_code_handler)],
            SELECT_TYPE: [CallbackQueryHandler(type_callback, pattern='^(soft|hw|consult|finish)$')],
            SW_SUBMENU: [CallbackQueryHandler(sw_callback, pattern='^sw_')],
            HW_SUBMENU: [CallbackQueryHandler(hw_callback, pattern='^hw_')],
            SUMMARY: [MessageHandler(filters.TEXT & ~filters.COMMAND, summary_handler)],
            PHOTO_UPLOAD: [
                MessageHandler(filters.PHOTO, photo_upload_handler),
                CallbackQueryHandler(next_photo_upload_callback, pattern='^next_photo$'),
                CallbackQueryHandler(confirm_callback, pattern='^confirm$')
            ],
            CONFIRM: [
                CallbackQueryHandler(send_without_photo_callback, pattern='^send_no_photo$'),
                CallbackQueryHandler(attach_photo_callback, pattern='^attach_photo$'),
                CallbackQueryHandler(edit_description_callback, pattern='^edit_description$')
            ],
            FEEDBACK: [MessageHandler(filters.TEXT & ~filters.COMMAND, feedback_handler)],
        },
        fallbacks=[
            CallbackQueryHandler(back_callback, pattern='^back$'),
            CallbackQueryHandler(restart_callback, pattern='^restart$'),
            CommandHandler('cancel', cancel_callback),
        ],
        per_message=False
    )
    
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(evaluation_callback, pattern=r'^rate_'))
    app.add_handler(CallbackQueryHandler(noop_callback, pattern=r'^noop_'))
    app.add_error_handler(error_handler)

# --- Фоновые задачи ---
async def on_startup(app):
    init_db()
    init_auth_db()
    os.makedirs(PHOTO_DIR, exist_ok=True)
    
    loop = asyncio.get_running_loop()
    loop.create_task(check_mail_and_notify_periodically(app.bot))
    loop.create_task(periodic_photos_cleanup())
    
    logger.info("Бот запущен и готов к работе.")

# --- Запуск ---
def main():
    setup_logging()

    application = ApplicationBuilder().token(TG_TOKEN).build()
    
    register_handlers(application)

    loop = asyncio.get_event_loop()
    
    # Запуск фоновых задач при старте
    loop.run_until_complete(on_startup(application))
    
    # Graceful shutdown
    stop = asyncio.Event()
    loop.add_signal_handler(signal.SIGTERM, stop.set)
    loop.add_signal_handler(signal.SIGINT, stop.set)

    # Запускаем приложение
    try:
        application.run_polling()
    except Exception as e:
        logger.critical(f"Критическая ошибка, приложение остановлено: {e}", exc_info=True)
    finally:
        logger.info("Приложение завершило работу.")

if __name__ == '__main__':
    main()
