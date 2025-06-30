from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
import os
from keyboards import get_main_menu, get_sw_menu, get_hw_menu, get_restart_menu
from constants import SELECT_TYPE, SW_SUBMENU, HW_SUBMENU, SUMMARY, PHOTO_UPLOAD
from db import save_dialog_to_db, get_user_data_from_db
from services.email_service import send_support_email
import logging

logger = logging.getLogger(__name__)

PHOTO_DIR = 'photos'

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "👋 Добро пожаловать в техподдержку ТНС-РУ!\nВыберите причину обращения:",
        reply_markup=get_main_menu()
    )
    return SELECT_TYPE


async def type_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    choice = query.data

    if choice == 'finish':
        await query.edit_message_text("✅ Диалог завершён. Спасибо за обращение!")
        await query.edit_message_reply_markup(get_restart_menu())
        context.user_data.clear()
        return ConversationHandler.END

    if choice == 'consult':
        await query.edit_message_text("📞 +7 (499) 973 74 74 доб. 7016\n✉️ help@globse.com")
        await query.edit_message_reply_markup(get_restart_menu())
        return ConversationHandler.END

    if choice == 'soft':
        await query.edit_message_text(
            "Выберите действие с программным обеспечением:",
            reply_markup=get_sw_menu()
        )
        context.user_data['current_state'] = SW_SUBMENU
        return SW_SUBMENU

    if choice == 'hw':
        await query.edit_message_text(
            "Выберите тип оборудования:",
            reply_markup=get_hw_menu()
        )
        context.user_data['current_state'] = HW_SUBMENU
        return HW_SUBMENU

async def sw_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    choice = query.data

    context.user_data['type'] = choice
    await query.edit_message_text(
        "Опишите проблему или укажите, какое ПО нужно установить (например, 'Не работает Outlook' или 'Установить Microsoft Office'):"
    )
    context.user_data['current_state'] = SUMMARY
    return SUMMARY

async def hw_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    choice = query.data

    context.user_data['type'] = choice
    await query.edit_message_text("Опишите проблему (например, 'Не включается компьютер' или 'Не печатает принтер'):")
    context.user_data['current_state'] = SUMMARY
    return SUMMARY

async def summary_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['summary'] = update.message.text
    keyboard = [
        [
            InlineKeyboardButton("Отправить без фото", callback_data='send_no_photo'),
            InlineKeyboardButton("Прикрепить фото", callback_data='attach_photo')
        ],
        [InlineKeyboardButton("Изменить описание", callback_data='edit_description')]
    ]
    await update.message.reply_text(
        f"Ваша заявка:\nТип: {context.user_data['type']}\nОписание: {context.user_data['summary']}\n\nВсё верно?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CONFIRM

async def photo_upload_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    photo_file = await update.message.photo[-1].get_file()
    
    # Создаем уникальное имя файла
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    file_ext = os.path.splitext(photo_file.file_path)[1]
    file_name = f'{user_id}_{timestamp}{file_ext}'
    file_path = os.path.join(PHOTO_DIR, file_name)

    await photo_file.download_to_drive(file_path)

    if 'photos' not in context.user_data:
        context.user_data['photos'] = []
    context.user_data['photos'].append(file_path)

    keyboard = [
        [InlineKeyboardButton("Отправить заявку", callback_data='confirm')],
        [InlineKeyboardButton("Прикрепить ещё фото", callback_data='next_photo')]
    ]
    await update.message.reply_text(
        "Фото добавлено. Хотите прикрепить ещё или отправить заявку?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return PHOTO_UPLOAD

async def confirm_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    user_data = context.user_data
    fio, location, email = get_user_data_from_db(user_id)

    subject = f"Заявка от {fio or query.from_user.username}"
    body = user_data['summary']
    photo_paths = user_data.get('photos')

    try:
        send_support_email(subject, body, photo_paths, fio, location, email, user_id)
        save_dialog_to_db(
            user_id, query.from_user.username, user_data['type'],
            body, photo_paths, 'sent'
        )
        await query.edit_message_text("✅ Ваша заявка отправлена в техподдержку. Спасибо!")
        await query.edit_message_reply_markup(get_restart_menu())

    except Exception as e:
        logger.error(f"Ошибка при отправке заявки: {e}")
        await query.edit_message_text("❗️ Произошла ошибка при отправке заявки. Пожалуйста, попробуйте снова.")

    context.user_data.clear()
    return ConversationHandler.END

async def edit_description_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Введите новое описание проблемы:")
    return SUMMARY

async def send_without_photo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # This is essentially the same as confirm_callback but without photos
    context.user_data['photos'] = []
    return await confirm_callback(update, context)

async def next_photo_upload_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Прикрепите следующее фото.")
    return PHOTO_UPLOAD

async def attach_photo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Пожалуйста, прикрепите фото.")
    return PHOTO_UPLOAD

async def back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    current_state = context.user_data.get('current_state')

    if current_state in [SW_SUBMENU, HW_SUBMENU]:
        await query.edit_message_text(
            "👋 Добро пожаловать в техподдержку ТНС-РУ!\nВыберите причину обращения:",
            reply_markup=get_main_menu()
        )
        context.user_data['current_state'] = SELECT_TYPE
        return SELECT_TYPE
    # Add more back logic if needed for other states
    
    # Default back action
    await query.edit_message_text(
        "👋 Добро пожаловать в техподдержку ТНС-РУ!\nВыберите причину обращения:",
        reply_markup=get_main_menu()
    )
    return SELECT_TYPE

async def restart_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.message.reply_text(
        "👋 Добро пожаловать в техподдержку ТНС-РУ!\nВыберите причину обращения:",
        reply_markup=get_main_menu()
    )
    return SELECT_TYPE

async def cancel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Действие отменено.")
    context.user_data.clear()
    await update.message.reply_text(
        "👋 Добро пожаловать в техподдержку ТНС-РУ!\nВыберите причину обращения:",
        reply_markup=get_main_menu()
    )
    return SELECT_TYPE 