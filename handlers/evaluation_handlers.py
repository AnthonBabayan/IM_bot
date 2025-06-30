from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from db import save_evaluation_to_db, set_pending_feedback, get_pending_feedback, clear_pending_feedback
from services.email_service import send_complaint_email
from keyboards import get_main_menu
from constants import SELECT_TYPE
import logging

logger = logging.getLogger(__name__)

async def evaluation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    data = query.data.split('_')
    rating = int(data[1])
    num = int(data[2])
    user_id = query.from_user.id

    if rating == 0:
        save_evaluation_to_db(num, user_id, 0)
        await query.edit_message_text("Спасибо, что уделили время!")
        return ConversationHandler.END

    if rating in [1, 2]:
        set_pending_feedback(user_id, num)
        await query.edit_message_text("Нам жаль, что у вас остались негативные впечатления. Пожалуйста, опишите, что пошло не так, чтобы мы могли стать лучше.")
        return FEEDBACK
    else:
        save_evaluation_to_db(num, user_id, rating)
        await query.edit_message_text("Спасибо за высокую оценку! Мы рады, что смогли помочь.")
        return ConversationHandler.END

async def feedback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.message.from_user.id
    feedback = update.message.text
    
    pending = get_pending_feedback(user_id)
    if not pending:
        await update.message.reply_text("Не найдено заявки для отзыва.")
        return ConversationHandler.END

    num, rating = pending
    save_evaluation_to_db(num, user_id, rating, feedback)
    clear_pending_feedback(user_id)
    
    # Send complaint email
    user_data = {
        'user_id': user_id,
        'fio': context.user_data.get('fio'),
        'location': context.user_data.get('location'),
        'email': context.user_data.get('email')
    }
    await send_complaint_email(num, feedback, user_data)

    await update.message.reply_text("Спасибо за ваш отзыв, мы обязательно его учтём!")
    
    await update.message.reply_text(
        "👋 Добро пожаловать в техподдержку ТНС-РУ!\nВыберите причину обращения:",
        reply_markup=get_main_menu()
    )
    return SELECT_TYPE

async def noop_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Вы уже оценили эту заявку.")
    return ConversationHandler.END 