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


def products_keyboard():
    """Клавиатура для выбора продуктов"""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    products = ["кофе", "чай", "пирожное", "торт", "эклер", "макарон"]

    # Создаем кнопки по 2 в ряду
    row = []
    for product in products:
        row.append(product)
        if len(row) == 2:
            keyboard.add(*row)
            row = []
    if row:
        keyboard.add(*row)

    keyboard.add('✅ Завершить выбор')
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