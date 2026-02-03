import re
from datetime import datetime

from telebot.types import Contact

from config import DESSERT_PERCENTAGE, FREE_COFFEE_AFTER, CHANNEL_ID


def check_channel_subscription(bot, user_id, channel_id):
    """
    Проверяет, подписан ли пользователь на канал
    """
    try:
        member = bot.get_chat_member(channel_id, user_id)
        print(f"Статус пользователя {user_id} в канале: {member.status}")
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"Ошибка при проверке подписки пользователя {user_id}: {e}")
        return False


def validate_phone(phone):
    print(f"validate_phone received: {phone}, type: {type(phone)}")
    """Валидация номера телефона"""
    if not phone:
        print("Phone is None or empty")
        return None

    # Если это объект контакта, берем phone_number
    if isinstance(phone, Contact):
        print("Processing Contact object")
        phone = phone.phone_number
        print(f"Extracted phone from Contact: {phone}")

    # Если у объекта есть атрибут phone_number, используем его
    elif hasattr(phone, 'phone_number'):
        print("Object has phone_number attribute")
        phone = phone.phone_number
        print(f"Extracted phone from object: {phone}")

    # Если это строка, проверяем формат
    if isinstance(phone, str):
        print(f"Processing string phone: {phone}")
        # Убираем все нецифровые символы кроме +
        if phone.startswith('+'):
            cleaned_phone = '+' + re.sub(r'\D', '', phone[1:])
        else:
            cleaned_phone = '+' + re.sub(r'\D', '', phone)

        # Получаем только цифры для проверки
        digits_only = re.sub(r'\D', '', cleaned_phone)
        
        # Нормализация российских номеров: заменяем первую 8 на 7
        # Если номер имеет 11 цифр и начинается с 8 (формат 89969090490 или +89969090490)
        if len(digits_only) == 11 and digits_only[0] == '8':
            # Заменяем первую 8 на 7
            cleaned_phone = '+7' + digits_only[1:]
            digits_only = '7' + digits_only[1:]
        
        print(f"Cleaned phone: {cleaned_phone}, digits only: {digits_only}, length: {len(digits_only)}")

        # Проверяем длину (10 или 11 цифр без +)
        # Для российских номеров должно быть 11 цифр (7 + 10 цифр номера)
        if len(digits_only) == 11 and cleaned_phone.startswith('+7'):
            print(f"Phone validation successful: {cleaned_phone}")
            return cleaned_phone
        elif len(digits_only) == 10:
            # Если 10 цифр, добавляем +7 в начало
            cleaned_phone = '+7' + digits_only
            print(f"Phone validation successful: {cleaned_phone}")
            return cleaned_phone
        else:
            print(f"Invalid phone length: {len(digits_only)}")
    else:
        print(f"Phone is not string, type: {type(phone)}")

    print("Phone validation failed")
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


def calculate_points_deduction(purchase_amount, available_points):
    """
    Расчет списываемых баллов (50% от суммы покупки, но не более доступных баллов)

    Args:
        purchase_amount (float): Сумма покупки
        available_points (int): Доступные баллы клиента

    Returns:
        int: Количество баллов для списания
    """
    max_deduction = int(purchase_amount * 0.5)  # 50% от суммы
    return min(max_deduction, available_points)


def format_profile(client):
    """Форматирование профиля клиента для отображения"""
    profile = f"*Ваш профиль, {client['name']}*\n\n"
    profile += f"Телефон: {client['phone']}\n"

    if client['birth_date']:
        profile += f"Дата рождения: {client['birth_date']}\n\n"


    profile += f"• Кешбэк: {client['points']}\n"
    profile += f"• Выпито чашек кофе: {client['coffee_counter']}\n"

    # Показываем прогресс до бесплатного кофе
    coffee_progress = client['coffee_counter'] % FREE_COFFEE_AFTER
    cups_until_free = FREE_COFFEE_AFTER - coffee_progress

    # Если осталась 1 чашка до бесплатной, показываем специальное сообщение
    if cups_until_free == 1:
        profile += f"\n☕️ *Следующая чашка кофе бесплатная!*"
    elif coffee_progress == 0 and client['coffee_counter'] > 0:
        profile += f"\n☕️ *Следующая чашка кофе бесплатная!*"
    else:
        profile += f"\n☕️ *До бесплатного кофе осталось:* {cups_until_free} чашек"

    return profile

def export_clients_to_excel(db_path="data/loyalty.db"):
    import sqlite3
    from openpyxl import Workbook
    from datetime import datetime

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM clients")
    rows = cursor.fetchall()
    headers = [desc[0] for desc in cursor.description]

    wb = Workbook()
    ws = wb.active
    ws.title = "Clients"

    ws.append(headers)
    for row in rows:
        ws.append(row)

    filename = f"clients_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    wb.save(filename)
    conn.close()
    return filename
