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
    keyboard.add('📱 Начислить баллы', '📊 Статистика', '👥 Поиск клиента')
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


def yes_no_keyboard():
    """Клавиатура Да/Нет"""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add('✅ Да', '❌ Нет')
    return keyboard


def phone_keyboard():
    """Клавиатура для запроса номера телефона"""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    button = types.KeyboardButton("📱 Поделиться номером", request_contact=True)
    keyboard.add(button)
    keyboard.add('📝 Ввести номер вручную', '❌ Отмена')
    return keyboard