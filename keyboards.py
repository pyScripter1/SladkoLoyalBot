from telebot import types

def main_menu():
    """Главное меню для пользователя"""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add('👤 Мой профиль', '💎 Мои баллы')
    keyboard.add('☕ Счетчик кофе', '✏️ Редактировать профиль')
    return keyboard

def admin_menu():
    """Меню для администратора"""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add('📱 Начислить баллы', '📊 Статистика')
    keyboard.add('👥 Поиск клиента', '🔙 Главное меню')
    return keyboard

def gender_keyboard():
    """Клавиатура для выбора пола"""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add('Мужской', 'Женский')
    keyboard.add('Не указывать')
    return keyboard

def purchase_type_keyboard():
    """Клавиатура для выбора типа покупки"""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add('☕ Кофе', '🍰 Десерты')
    keyboard.add('❌ Отмена')
    return keyboard

def cancel_keyboard():
    """Клавиатура для отмены действия"""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add('❌ Отмена')
    return keyboard


def phone_keyboard():
    """Клавиатура для запроса номера телефона"""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)

    # Кнопка для отправки контакта - ОБЯЗАТЕЛЬНО с request_contact=True
    contact_btn = types.KeyboardButton("📱 Поделиться номером", request_contact=True)

    keyboard.add(contact_btn)
    keyboard.add(types.KeyboardButton('📝 Ввести номер вручную'))
    keyboard.add(types.KeyboardButton('❌ Отмена'))

    return keyboard


def manual_phone_keyboard():
    """Клавиатура для ручного ввода номера"""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    keyboard.add('❌ Отмена')
    return keyboard