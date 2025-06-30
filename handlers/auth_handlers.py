from telegram import Update
from telegram.ext import ContextTypes
from auth import check_email_in_ldap, get_user_info_from_ldap, generate_code, send_code_to_email, save_code, verify_code_and_issue_token, is_user_authorized
from keyboards import get_main_menu
from constants import SELECT_TYPE, AUTH_EMAIL, AUTH_CODE

async def auth_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id if update.effective_user else None
    if user_id and is_user_authorized(user_id):
        await update.message.reply_text(
            "👋 Добро пожаловать в техподдержку ТНС-РУ!\nВыберите причину обращения:",
            reply_markup=get_main_menu()
        )
        return SELECT_TYPE
    await update.message.reply_text("Для доступа к боту введите ваш рабочий email:")
    return AUTH_EMAIL


async def auth_email_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    email = update.message.text.strip()
    user_id = update.message.from_user.id
    if not check_email_in_ldap(email):
        await update.message.reply_text("Email не найден в корпоративной базе. Попробуйте ещё раз или обратитесь в поддержку.")
        return AUTH_EMAIL
    fio, location = get_user_info_from_ldap(email)
    context.user_data['fio'] = fio
    context.user_data['location'] = location
    context.user_data['email'] = email
    code = generate_code()
    send_code_to_email(email, code)
    save_code(user_id, email, code)
    await update.message.reply_text(f"На вашу почту отправлен код. Введите его для подтверждения:")
    return AUTH_CODE


async def auth_code_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    code = update.message.text.strip()
    user_id = update.message.from_user.id
    ok, result = verify_code_and_issue_token(user_id, code)
    if ok:
        context.user_data.clear()
        await update.message.reply_text(
            "✅ Авторизация успешна! Теперь вы можете пользоваться ботом.\n\n"
            "👋 Добро пожаловать в техподдержку ТНС-РУ!\nВыберите причину обращения:",
            reply_markup=get_main_menu()
        )
        return SELECT_TYPE
    else:
        await update.message.reply_text(f"❗️ Ошибка: {result}\nВведите код ещё раз:")
        return AUTH_CODE 