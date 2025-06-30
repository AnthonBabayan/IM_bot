from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_main_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("Программное обеспечение", callback_data='soft')],
        [InlineKeyboardButton("Оборудование", callback_data='hw')],
        [InlineKeyboardButton("Консультация", callback_data='consult')],
        [InlineKeyboardButton("Завершить", callback_data='finish')]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_sw_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("Проблема в работе ПО", callback_data='sw_issue')],
        [InlineKeyboardButton("Установка ПО", callback_data='sw_install')],
        [InlineKeyboardButton("Назад", callback_data='back')]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_hw_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("Проблема с ПК/ноутбуком", callback_data='hw_pc')],
        [InlineKeyboardButton(
            "Проблема с периферийным устройством\n(клавиатура, мышь, принтер, колонки и т.д.)",
            callback_data='hw_peripheral'
        )],
        [InlineKeyboardButton("Другое", callback_data='hw_other')],
        [InlineKeyboardButton("Назад", callback_data='back')]
    ]
    return InlineKeyboardMarkup(keyboard)


def get_stage_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("Назад", callback_data='back')]])

def get_restart_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("Новое обращение", callback_data='restart')]])

def get_consult_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("Новое обращение", callback_data='restart')]])

def get_evaluation_keyboard(num: int) -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("⭐", callback_data=f'rate_1_{num}'),
            InlineKeyboardButton("⭐⭐", callback_data=f'rate_2_{num}'),
            InlineKeyboardButton("⭐⭐⭐", callback_data=f'rate_3_{num}'),
            InlineKeyboardButton("⭐⭐⭐⭐", callback_data=f'rate_4_{num}'),
            InlineKeyboardButton("⭐⭐⭐⭐⭐", callback_data=f'rate_5_{num}'),
        ],
        [InlineKeyboardButton("Без оценки", callback_data=f'rate_0_{num}')]
    ]
    return InlineKeyboardMarkup(keyboard) 