import asyncio
import logging
import re
import poplib
import email as email_lib
from email.header import decode_header
import html
import sqlite3
from telegram import Bot
from telegram.error import BadRequest, Forbidden
from db import add_unreachable_user, is_unreachable_user, has_evaluation
from keyboards import get_evaluation_keyboard
from config import DB_PATH

logger = logging.getLogger(__name__)

HOST = 'YOUR_POP3_HOST'
PORT = 110
USERNAME = 'YOUR_POP3_USERNAME'
PASSWORD = 'YOUR_POP3_PASSWORD'

def decode_mime_header(header):
    if header is None:
        return ""
    decoded_parts = decode_header(header)
    return ''.join([
        part.decode(encoding or 'utf-8') if isinstance(part, bytes) else part
        for part, encoding in decoded_parts
    ])

def extract_solutions(body_clean):
    match = re.search(r'Решение:\s*(.*)', body_clean, re.DOTALL)
    if not match:
        return None
    after_solution = match.group(1)
    lines = after_solution.splitlines()
    solutions = []
    current = []
    for line in lines:
        if re.match(r'^\d{2}\.\d{2}\.\d{4} - ', line.strip()):
            if current:
                solutions.append('\n'.join(current).strip())
                current = []
            current.append(line.strip())
        elif current and line.strip():
            current.append(line.strip())
        elif current and not line.strip():
            solutions.append('\n'.join(current).strip())
            current = []
        else:
            break
    if current:
        solutions.append('\n'.join(current).strip())
    return solutions if solutions else None

def extract_info_from_email(msg):
    subject = decode_mime_header(msg['Subject'])
    body = ""

    if msg.is_multipart():
        parts = []
        for part in msg.walk():
            if part.get_content_type() in ["text/plain", "text/html"]:
                try:
                    parts.append(part.get_payload(decode=True).decode(errors='ignore'))
                except Exception as e:
                    logger.error(f"Ошибка декодирования части письма: {e}")
        body = "\n".join(parts)
    else:
        try:
            body = msg.get_payload(decode=True).decode(errors='ignore')
        except Exception as e:
            logger.error(f"Ошибка декодирования письма: {e}")

    body_clean = re.sub(r'<[^>]+>', '', body)
    body_clean = html.unescape(body_clean)

    tg_id_match = re.search(r'Telegram ID[: ]*([0-9]+)', body_clean, re.IGNORECASE)
    tg_id = tg_id_match.group(1) if tg_id_match else None

    if "получена и рассмотрена" in subject:
        num_match = re.search(r'№\s*IM-CL-(\d+)', subject)
        deadline_match = re.search(r'Обещанное время решения:\s*([0-9]{2}\.[0-9]{2}\.[0-9]{4}\s+[0-9]{2}:[0-9]{2}:[0-9]{2})', body_clean)
        return {
            "type": "received", "num": num_match.group(1) if num_match else None,
            "deadline": deadline_match.group(1) if deadline_match else None, "tg_id": tg_id
        }
    elif "выполнена" in subject:
        num_match = re.search(r'№\s*IM-CL-(\d+)', subject)
        return {
            "type": "done", "num": num_match.group(1) if num_match else None,
            "solutions": extract_solutions(body_clean), "tg_id": tg_id
        }
    # ... (add other email types: waiting, returned) ...
    return None

def is_message_processed(msg_id):
    # ... (database logic) ...
    pass

def mark_message_processed(msg_id):
    # ... (database logic) ...
    pass

async def check_mail_and_notify(bot: Bot):
    try:
        pop3_server = poplib.POP3(HOST, PORT)
        pop3_server.user(USERNAME)
        pop3_server.pass_(PASSWORD)
        
        num_messages = len(pop3_server.list()[1])
        for i in range(num_messages):
            response, lines, octets = pop3_server.retr(i + 1)
            msg_content = b'\n'.join(lines)
            msg = email_lib.message_from_bytes(msg_content)
            msg_id = msg.get('Message-ID') or str(hash(msg_content))

            if is_message_processed(msg_id):
                continue

            info = extract_info_from_email(msg)
            if info and info['tg_id']:
                # ... (logic to build message text) ...
                text = "..."
                
                if is_unreachable_user(int(info['tg_id'])):
                    continue
                
                try:
                    await bot.send_message(chat_id=int(info['tg_id']), text=text)
                    if info['type'] == 'done':
                        await send_evaluation_request(bot, int(info['tg_id']), info['num'])
                    mark_message_processed(msg_id)
                    pop3_server.dele(i + 1)
                except (BadRequest, Forbidden) as e:
                    logger.warning(f"Не удалось отправить сообщение пользователю {info['tg_id']}: {e}")
                    if isinstance(e, Forbidden) or "Chat not found" in str(e):
                        add_unreachable_user(int(info['tg_id']))
            else:
                 pop3_server.dele(i + 1)

        pop3_server.quit()
    except Exception as e:
        logger.error(f"Ошибка проверки почты: {e}", exc_info=True)

async def check_mail_and_notify_periodically(bot: Bot, interval=60):
    while True:
        await check_mail_and_notify(bot)
        await asyncio.sleep(interval)
        
async def send_evaluation_request(bot: Bot, chat_id: int, num: int):
    if has_evaluation(num, chat_id):
        return
    await bot.send_message(
        chat_id=chat_id,
        text="Пожалуйста, оцените работу по заявке:",
        reply_markup=get_evaluation_keyboard(num)
    ) 