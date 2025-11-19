from telebot import types
from config import CHANNEL_URL

def subscription_keyboard():
    """Клавиатура для подписки на канал"""
    keyboard = types.InlineKeyboardMarkup()
    subscribe_btn = types.InlineKeyboardButton("📢 Подписаться на канал", url=CHANNEL_URL)
    check_btn = types.InlineKeyboardButton("✅ Я подписался", callback_data="check_subscription")
    keyboard.add(subscribe_btn)
    keyboard.add(check_btn)
    return keyboard


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
    keyboard.add('👥 Поиск клиента', '💸 Списать баллы')
    keyboard.add('📢 Создать рассылку', '🔙 Главное меню')  # Новая кнопка
    return keyboard

def broadcast_keyboard():
    """Клавиатура для создания рассылки"""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add('📝 Только текст', '🖼️ С фотографией')
    keyboard.add('👀 Предпросмотр', '✅ Отправить всем')
    keyboard.add('❌ Отменить рассылку')
    return keyboard

def confirm_broadcast_keyboard():
    """Клавиатура для подтверждения рассылки"""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add('✅ Да, отправить всем', '❌ Нет, отменить')
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