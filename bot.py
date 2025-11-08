import telebot
from telebot import types
import logging
from config import BOT_TOKEN, INITIAL_BONUS_POINTS, FREE_COFFEE_AFTER
from database import Database
from keyboards import *
from utils import *
import sqlite3

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота и базы данных
bot = telebot.TeleBot(BOT_TOKEN)
db = Database()

# Словари для хранения временных данных
user_data = {}
admin_mode = (1920466733, )


# Команда старт
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id

    if user_id in admin_mode:
        bot.send_message(message.chat.id, "👨‍💼 Режим администратора", reply_markup=admin_menu())
        return

    client = db.get_client_by_telegram_id(user_id)

    if client:
        welcome_back = f"""
🎉 *С возвращением, {client['name']}!*

Рады видеть вас снова в нашей кондитерской! 🍰

Ваши баллы: {client['points']} 💎
Выпито кофе: {client['coffee_counter']} ☕

Используйте меню ниже для управления вашим профилем!
        """
        bot.send_message(message.chat.id, welcome_back, parse_mode='Markdown', reply_markup=main_menu())
    else:
        welcome_text = """
✨ *Добро пожаловать в нашу кондитерскую!* ✨

🍰 *Сладкие моменты начинаются здесь!* 🍰

Зарегистрируйтесь в нашей программе лояльности и получайте:
• 🎁 100 баллов при регистрации
• 💎 Начисление баллов за каждую покупку
• ☕ Бесплатную чашку кофе за каждые 5 покупок
• 🎂 Специальные предложения в день рождения

*Давайте начнем! Введите ваше имя:*
        """
        bot.send_message(message.chat.id, welcome_text, parse_mode='Markdown')
        bot.register_next_step_handler(message, process_name_step)


def process_name_step(message):
    user_id = message.from_user.id
    user_data[user_id] = {'name': message.text}

    bot.send_message(message.chat.id,
                     "📅 Теперь введите вашу дату рождения в формате ДД.ММ.ГГГГ (например, 15.05.1990):",
                     reply_markup=cancel_keyboard())
    bot.register_next_step_handler(message, process_birth_date_step)


def process_birth_date_step(message):
    user_id = message.from_user.id

    if message.text == '❌ Отмена':
        del user_data[user_id]
        bot.send_message(message.chat.id, "Регистрация отменена.", reply_markup=types.ReplyKeyboardRemove())
        return

    birth_date = validate_date(message.text)

    if birth_date:
        user_data[user_id]['birth_date'] = birth_date
        bot.send_message(message.chat.id, "⚧ Выберите ваш пол:", reply_markup=gender_keyboard())
        bot.register_next_step_handler(message, process_gender_step)
    else:
        bot.send_message(message.chat.id, "❌ Неверный формат даты. Попробуйте еще раз (ДД.ММ.ГГГГ):")
        bot.register_next_step_handler(message, process_birth_date_step)


def process_gender_step(message):
    user_id = message.from_user.id

    if message.text == '❌ Отмена':
        del user_data[user_id]
        bot.send_message(message.chat.id, "Регистрация отменена.", reply_markup=types.ReplyKeyboardRemove())
        return

    user_data[user_id]['gender'] = message.text
    bot.send_message(message.chat.id, "📱 Введите ваш номер телефона (например, +79123456789):",
                     reply_markup=cancel_keyboard())
    bot.register_next_step_handler(message, process_phone_step)


def process_phone_step(message):
    user_id = message.from_user.id

    if message.text == '❌ Отмена':
        del user_data[user_id]
        bot.send_message(message.chat.id, "Регистрация отменена.", reply_markup=types.ReplyKeyboardRemove())
        return

    phone = validate_phone(message.text)

    if phone:
        # Проверяем, не зарегистрирован ли уже этот номер
        existing_client = db.get_client_by_phone(phone)
        if existing_client:
            bot.send_message(message.chat.id, "❌ Этот номер телефона уже зарегистрирован.")
            del user_data[user_id]
            return

        user_data[user_id]['phone'] = phone

        # Сохраняем пользователя в базу
        success = db.add_client(
            user_id,
            user_data[user_id]['name'],
            user_data[user_id].get('birth_date'),
            user_data[user_id].get('gender'),
            phone
        )

        if success:
            welcome_message = f"""
🎊 *Поздравляем с регистрацией, {user_data[user_id]['name']}!* 🎊

✅ *Вы успешно зарегистрированы в нашей программе лояльности!*

🎁 *Вам начислено: {INITIAL_BONUS_POINTS} баллов*
📞 *Ваш номер: {phone}*

Теперь вы можете:
• 💎 Копить баллы за покупки
• ☕ Получать бесплатное кофе
• 🎂 Получать специальные предложения

*Используйте меню ниже для управления профилем!*
            """
            bot.send_message(message.chat.id, welcome_message, parse_mode='Markdown', reply_markup=main_menu())
        else:
            bot.send_message(message.chat.id, "❌ Произошла ошибка при регистрации. Попробуйте позже.")

        del user_data[user_id]
    else:
        bot.send_message(message.chat.id, "❌ Неверный формат номера. Попробуйте еще раз:")
        bot.register_next_step_handler(message, process_phone_step)


# Команды пользователя
@bot.message_handler(func=lambda message: message.text == '👤 Мой профиль')
def show_profile(message):
    client = db.get_client_by_telegram_id(message.from_user.id)
    if client:
        profile_text = format_profile(client)
        bot.send_message(message.chat.id, profile_text, parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, "❌ Вы не зарегистрированы. Используйте /start для регистрации.")


@bot.message_handler(func=lambda message: message.text == '💎 Мои баллы')
def show_points(message):
    client = db.get_client_by_telegram_id(message.from_user.id)
    if client:
        points_text = f"""
💎 *Ваши баллы: {client['points']}*

🎯 *Как использовать баллы?*
1 балл = 1 рубль скидки
Просто сообщите администратору о желании использовать баллы при оплате!

💰 *Накоплено всего: {client['total_spent']} руб.*
        """
        bot.send_message(message.chat.id, points_text, parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, "❌ Вы не зарегистрированы.")


@bot.message_handler(func=lambda message: message.text == '☕ Счетчик кофе')
def show_coffee_counter(message):
    client = db.get_client_by_telegram_id(message.from_user.id)
    if client:
        coffee_progress = client['coffee_counter'] % FREE_COFFEE_AFTER
        cups_until_free = FREE_COFFEE_AFTER - coffee_progress

        coffee_text = f"""
☕ *Ваша кофейная статистика:*

🍵 *Выпито чашек кофе:* {client['coffee_counter']}
🎯 *До бесплатного кофе:* {cups_until_free} чашек

{'🎉 *Следующая чашка кофе бесплатная!*' if coffee_progress == 0 and client['coffee_counter'] > 0 else ''}

*Каждая {FREE_COFFEE_AFTER}-я чашка кофе бесплатна!*
        """
        bot.send_message(message.chat.id, coffee_text, parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, "❌ Вы не зарегистрированы.")


@bot.message_handler(func=lambda message: message.text == '✏️ Редактировать профиль')
def edit_profile(message):
    client = db.get_client_by_telegram_id(message.from_user.id)
    if client:
        keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        keyboard.add('📛 Изменить имя', '📅 Изменить дату рождения', '📱 Изменить телефон')
        keyboard.add('🔙 Назад')

        bot.send_message(message.chat.id, "✏️ Что вы хотите изменить?", reply_markup=keyboard)
    else:
        bot.send_message(message.chat.id, "❌ Вы не зарегистрированы.")


@bot.message_handler(func=lambda message: message.text == '📛 Изменить имя')
def change_name(message):
    bot.send_message(message.chat.id, "Введите новое имя:", reply_markup=cancel_keyboard())
    bot.register_next_step_handler(message, process_new_name)


def process_new_name(message):
    if message.text == '❌ Отмена':
        bot.send_message(message.chat.id, "Изменение отменено.", reply_markup=main_menu())
        return

    db.update_client_profile(message.from_user.id, name=message.text)
    bot.send_message(message.chat.id, "✅ Имя успешно изменено!", reply_markup=main_menu())


@bot.message_handler(func=lambda message: message.text == "📅 Изменить дату рождения")
def change_birth_date(message):
    bot.send_message(message.chat.id, "Введите новую дату:", reply_markup=cancel_keyboard())
    bot.register_next_step_handler(message, process_new_date)


def process_new_date(message):
    if message.text == "❌ Отмена":
        bot.send_message(message.chat.id, "Изменение отменено.", reply_markup=main_menu())
        return

    db.update_client_profile(message.from_user.id, birth_date=message.text)
    bot.send_message(message.chat.id, "✅ Дата рождения успешно изменена!", reply_markup=main_menu())


@bot.message_handler(func=lambda message: message.text == "📱 Изменить телефон")
def change_phone(message):
    bot.send_message(message.chat.id, "Введите новый номер:", reply_markup=cancel_keyboard())
    bot.register_next_step_handler(message, process_new_phone)


def process_new_phone(message):
    if message.text == "❌ Отмена":
        bot.send_message(message.chat.id, "Изменение отменено.", reply_markup=main_menu())
        return

    db.update_client_profile(message.from_user.id, phone=message.text)
    bot.send_message(message.chat.id, "✅ Номер телефона успешно изменен!", reply_markup=main_menu())


# Администраторские функции
@bot.message_handler(commands=['admin'])
def admin_command(message):
    # Здесь должна быть проверка прав администратора
    bot.send_message(message.chat.id,
                     "🔐 *Режим администратора активирован*\n\n"
                     "Доступные функции:\n"
                     "• 📱 Начислить баллы за покупку\n"
                     "• 👥 Поиск информации о клиенте\n"
                     "• 📊 Просмотр статистики",
                     parse_mode='Markdown',
                     reply_markup=admin_menu())


@bot.message_handler(func=lambda message: message.text == '📱 Начислить баллы' and message.from_user.id in admin_mode)
def add_points_start(message):
    bot.send_message(message.chat.id, "📱 Введите номер телефона клиента (10 цифр):", reply_markup=cancel_keyboard())
    bot.register_next_step_handler(message, process_admin_phone)


def process_admin_phone(message):
    if message.text == '❌ Отмена':
        bot.send_message(message.chat.id, "Операция отменена.", reply_markup=admin_menu())
        return

    phone = validate_phone(message.text)
    if not phone:
        bot.send_message(message.chat.id, "❌ Неверный формат номера. Попробуйте еще раз:")
        bot.register_next_step_handler(message, process_admin_phone)
        return

    client = db.get_client_by_phone(phone)
    if not client:
        bot.send_message(message.chat.id, "❌ Клиент с таким номером не найден.")
        return

    user_data[message.from_user.id] = {'client_phone': phone, 'products': {}}

    bot.send_message(message.chat.id, f"👤 Клиент: {client['name']}\nВыберите продукты:",
                     reply_markup=products_keyboard())
    bot.register_next_step_handler(message, process_product_selection)


def process_product_selection(message):
    user_id = message.from_user.id
    admin_data = user_data.get(user_id, {})

    if message.text == '❌ Отмена':
        if user_id in user_data:
            del user_data[user_id]
        bot.send_message(message.chat.id, "Операция отменена.", reply_markup=admin_menu())
        return

    if message.text == '✅ Завершить выбор':
        if not admin_data.get('products'):
            bot.send_message(message.chat.id, "❌ Не выбрано ни одного продукта. Попробуйте еще раз:")
            bot.register_next_step_handler(message, process_product_selection)
            return

        # Рассчитываем баллы
        points, total_amount, coffee_count = calculate_points(admin_data['products'])

        # Начисляем баллы
        db.add_points(admin_data['client_phone'], points, total_amount, admin_data['products'])

        # Увеличиваем счетчик кофе
        for _ in range(coffee_count):
            free_coffee = db.increment_coffee_counter(admin_data['client_phone'])
            if free_coffee:
                # Уведомляем клиента о бесплатном кофе
                client = db.get_client_by_phone(admin_data['client_phone'])
                if client:
                    try:
                        bot.send_message(
                            client['telegram_id'],
                            f"🎉 Поздравляем! Вы получили бесплатную чашку кофе! 🎉\n\n"
                            f"Приходите в нашу кондитерскую и получите свой подарок! ☕"
                        )
                    except:
                        pass  # Если пользователь заблокировал бота

        # Формируем чек
        receipt = f"""
🧾 *Чек покупки*

👤 Клиент: {db.get_client_by_phone(admin_data['client_phone'])['name']}
📞 Телефон: +7{admin_data['client_phone']}

📦 *Товары:*
"""
        for product, quantity in admin_data['products'].items():
            receipt += f"• {product} x{quantity} - {PRODUCTS[product] * quantity} руб.\n"

        receipt += f"\n💰 *Итого:* {total_amount} руб."
        receipt += f"\n💎 *Начислено баллов:* {points}"
        receipt += f"\n☕ *Чашек кофе:* {coffee_count}"

        if coffee_count > 0:
            receipt += f"\n📊 *Общий счетчик кофе:* {db.get_client_by_phone(admin_data['client_phone'])['coffee_counter']}"

        bot.send_message(message.chat.id, receipt, parse_mode='Markdown', reply_markup=admin_menu())
        del user_data[user_id]
        return

    product = message.text.lower()
    if product in PRODUCTS:
        if product not in admin_data['products']:
            admin_data['products'][product] = 0
        admin_data['products'][product] += 1

        # Обновляем данные
        user_data[user_id] = admin_data

        bot.send_message(message.chat.id, f"✅ {product} добавлен. Выберите еще продукты или завершите выбор:",
                         reply_markup=products_keyboard())
        bot.register_next_step_handler(message, process_product_selection)
    else:
        bot.send_message(message.chat.id, "❌ Продукт не найден. Выберите из списка:",
                         reply_markup=products_keyboard())
        bot.register_next_step_handler(message, process_product_selection)


# Поиск клиента администратором (добавленная функция)
@bot.message_handler(func=lambda message: message.text == '👥 Поиск клиента' and message.from_user.id in admin_mode)
def search_client_start(message):
    bot.send_message(message.chat.id, "🔍 Введите номер телефона клиента для поиска (10 цифр):",
                     reply_markup=cancel_keyboard())
    bot.register_next_step_handler(message, process_client_search)


def process_client_search(message):
    if message.text == '❌ Отмена':
        bot.send_message(message.chat.id, "🔍 Поиск отменен.", reply_markup=admin_menu())
        return

    phone = validate_phone(message.text)
    if not phone:
        bot.send_message(message.chat.id, "❌ Неверный формат номера. Попробуйте еще раз:")
        bot.register_next_step_handler(message, process_client_search)
        return

    client = db.get_client_by_phone(phone)
    if not client:
        bot.send_message(message.chat.id, "❌ Клиент с таким номером не найден.", reply_markup=admin_menu())
        return

    # Форматируем информацию о клиенте
    client_info = format_client_info_for_admin(client)
    bot.send_message(message.chat.id, client_info, parse_mode='Markdown', reply_markup=admin_menu())


def format_client_info_for_admin(client):
    """Форматирование информации о клиенте для администратора"""
    info = f"""
👤 *Информация о клиенте:*

📛 *Имя:* {client['name']}
📞 *Телефон:* {client['phone']}
"""

    if client['birth_date']:
        info += f"🎂 *Дата рождения:* {client['birth_date']}\n"
    if client['gender'] and client['gender'] != 'Не указывать':
        info += f"⚧ *Пол:* {client['gender']}\n"

    info += f"""
💎 *Баллы:* {client['points']}
☕ *Выпито чашек кофе:* {client['coffee_counter']}
💰 *Всего потрачено:* {client['total_spent']:.2f} руб.
🆔 *Telegram ID:* {client['telegram_id']}
"""

    # Показываем прогресс до бесплатного кофе
    coffee_progress = client['coffee_counter'] % FREE_COFFEE_AFTER
    cups_until_free = FREE_COFFEE_AFTER - coffee_progress

    if coffee_progress == 0 and client['coffee_counter'] > 0:
        info += f"\n🎉 *Следующая чашка кофе бесплатная!*"
    else:
        info += f"\n📊 *До бесплатного кофе осталось:* {cups_until_free} чашек"

    # Добавляем информацию о регистрации
    if client['registration_date']:
        reg_date = datetime.fromisoformat(client['registration_date'])
        info += f"\n📅 *Дата регистрации:* {reg_date.strftime('%d.%m.%Y %H:%M')}"

    return info


# Статистика
@bot.message_handler(func=lambda message: message.text == '📊 Статистика' and message.from_user.id in admin_mode)
def show_statistics(message):
    """Показывает общую статистику"""
    conn = sqlite3.connect('loyalty.db')
    cursor = conn.cursor()

    # Общее количество клиентов
    cursor.execute('SELECT COUNT(*) FROM clients')
    total_clients = cursor.fetchone()[0]

    # Общая сумма потраченных средств
    cursor.execute('SELECT SUM(total_spent) FROM clients')
    total_spent = cursor.fetchone()[0] or 0

    # Общее количество начисленных баллов
    cursor.execute('SELECT SUM(points) FROM clients')
    total_points = cursor.fetchone()[0] or 0

    # Клиенты с наибольшим количеством баллов
    cursor.execute('SELECT name, phone, points FROM clients ORDER BY points DESC LIMIT 5')
    top_clients = cursor.fetchall()

    conn.close()

    stats_text = f"""
📊 *Статистика системы лояльности*

👥 *Всего клиентов:* {total_clients}
💰 *Общая сумма покупок:* {total_spent:.2f} руб.
💎 *Всего баллов в системе:* {total_points}

🏆 *Топ-5 клиентов по баллам:*
"""

    for i, (name, phone, points) in enumerate(top_clients, 1):
        stats_text += f"{i}. {name} (+7{phone}) - {points} баллов\n"

    bot.send_message(message.chat.id, stats_text, parse_mode='Markdown', reply_markup=admin_menu())


@bot.message_handler(func=lambda message: message.text == '🔙 Главное меню' and message.from_user.id in admin_mode)
def exit_admin_mode(message):
    if message.from_user.id in admin_mode:
        admin_mode.remove(message.from_user.id)
    bot.send_message(message.chat.id, "👋 Возвращаемся в главное меню", reply_markup=main_menu())



# Запуск бота
if __name__ == '__main__':
    print("Бот запущен...")
    bot.infinity_polling()