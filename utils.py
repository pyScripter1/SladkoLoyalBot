import re
from datetime import datetime
from config import DESSERT_PERCENTAGE, FREE_COFFEE_AFTER


def validate_phone(phone):
    """Валидация номера телефона"""
    if not phone:
        return None

    # Если это объект контакта, берем phone_number
    if hasattr(phone, 'phone_number'):
        phone = phone.phone_number

    # Убираем все нецифровые символы кроме +
    if isinstance(phone, str):
        return phone
    else:
        return None




def validate_date(date_string):
    """Валидация даты рождения"""
    try:
        date = datetime.strptime(date_string, '%d.%m.%Y')
        # Проверяем, что дата не в будущем
        if date > datetime.now():
            return None
        return date_string
    except ValueError:
        return None


def validate_amount(amount_string):
    """Валидация суммы"""
    try:
        amount = float(amount_string)
        if amount <= 0:
            return None
        return amount
    except ValueError:
        return None


def calculate_dessert_points(amount):
    """Расчет баллов за десерты"""
    points = int(amount * (DESSERT_PERCENTAGE / 100))
    return points


def format_profile(client):
    """Форматирование профиля клиента для отображения"""
    profile = f"👤 *Ваш профиль:*\n\n"
    profile += f"📛 *Имя:* {client['name']}\n"
    profile += f"📞 *Телефон:* {client['phone']}\n"

    if client['birth_date']:
        profile += f"🎂 *Дата рождения:* {client['birth_date']}\n"
    if client['gender'] and client['gender'] != 'Не указывать':
        profile += f"⚧ *Пол:* {client['gender']}\n"

    profile += f"💎 *Баллы:* {client['points']}\n"
    profile += f"☕ *Выпито чашек кофе:* {client['coffee_counter']}\n"
    profile += f"💰 *Всего потрачено:* {client['total_spent']} руб.\n"

    # Показываем прогресс до бесплатного кофе
    coffee_progress = client['coffee_counter'] % FREE_COFFEE_AFTER
    cups_until_free = FREE_COFFEE_AFTER - coffee_progress

    if coffee_progress == 0 and client['coffee_counter'] > 0:
        profile += f"\n🎉 *Следующая чашка кофе бесплатная!*"
    else:
        profile += f"\n📊 *До бесплатного кофе осталось:* {cups_until_free} чашек"

    return profile