import telebot
from telebot import types
import logging
from config import BOT_TOKEN, INITIAL_BONUS_POINTS, FREE_COFFEE_AFTER, ADMIN_IDS, DESSERT_PERCENTAGE
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

def is_admin(user_id):
    """Проверяет, является ли пользователь администратором"""
    return user_id in ADMIN_IDS

# Команда старт
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id

    if is_admin(user_id):
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
    bot.send_message(message.chat.id,
                    "📱 Поделитесь вашим номером телефона для регистрации в программе лояльности:",
                    reply_markup=phone_keyboard())
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
        bot.send_message(message.chat.id, "❌ Неверный формат номера. Введите номер вручную:")
        bot.register_next_step_handler(message, process_phone_step)


@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    user_id = message.from_user.id

    # Если пользователь в процессе регистрации
    if user_id in user_data:
        process_phone_step(message)
    else:
        # Если контакт отправлен вне регистрации
        phone = validate_phone(message.contact.phone_number)
        if phone:
            client = db.get_client_by_phone(phone)
            if client:
                bot.send_message(message.chat.id,
                                 f"✅ Найден профиль: {client['name']}\n"
                                 f"📞 Телефон: {phone}",
                                 reply_markup=main_menu())
            else:
                bot.send_message(message.chat.id,
                                 "❌ Профиль с этим номером не найден. Зарегистрируйтесь с помощью /start")

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
    if not is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "❌ У вас нет прав администратора.")
        return

    bot.send_message(message.chat.id,
                     "🔐 *Режим администратора активирован*\n\n"
                     "Доступные функции:\n"
                     "• 📱 Начислить баллы за покупку\n"
                     "• 👥 Поиск информации о клиенте\n"
                     "• 📊 Просмотр статистики",
                     parse_mode='Markdown',
                     reply_markup=admin_menu())


@bot.message_handler(func=lambda message: message.text == '📱 Начислить баллы' and is_admin(message.from_user.id))
def add_points_start(message):
    bot.send_message(message.chat.id, "📱 Введите номер телефона клиента:", reply_markup=cancel_keyboard())
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

    user_data[message.from_user.id] = {'client_phone': phone, 'client_name': client['name']}

    bot.send_message(message.chat.id,
                     f"👤 Клиент: {client['name']}\n"
                     f"☕ Счетчик кофе: {client['coffee_counter']}\n\n"
                     "Выберите тип покупки:",
                     reply_markup=purchase_type_keyboard())
    bot.register_next_step_handler(message, process_purchase_type)


def process_purchase_type(message):
    user_id = message.from_user.id
    admin_data = user_data.get(user_id, {})

    if message.text == '❌ Отмена':
        if user_id in user_data:
            del user_data[user_id]
        bot.send_message(message.chat.id, "Операция отменена.", reply_markup=admin_menu())
        return

    if message.text == '☕ Кофе':
        # Обработка покупки кофе
        free_coffee = db.add_coffee_purchase(admin_data['client_phone'])

        if free_coffee:
            # Это 6-я чашка - бесплатное кофе и сброс счетчика
            db.reset_coffee_counter(admin_data['client_phone'])

            # Уведомляем клиента
            client = db.get_client_by_phone(admin_data['client_phone'])
            if client:
                try:
                    bot.send_message(
                        client['telegram_id'],
                        f"🎉 Поздравляем! Вы получили бесплатную чашку кофе! 🎉\n\n"
                        f"Приходите в нашу кондитерскую и получите свой подарок! ☕\n"
                        f"Счетчик кофе обнулен."
                    )
                except Exception as e:
                    print(f"Не удалось отправить уведомление клиенту: {e}")

            receipt = f"""
☕ *Покупка кофе*

👤 Клиент: {admin_data['client_name']}
📞 Телефон: {admin_data['client_phone']}

🎉 *Это была 6-я чашка кофе!*
💝 *Клиент получает бесплатное кофе!*
🔄 *Счетчик кофе обнулен.*

Спасибо за покупку! ☕
            """
        else:
            # Обычная покупка кофе
            current_counter = db.get_coffee_counter(admin_data['client_phone'])
            cups_until_free = FREE_COFFEE_AFTER - (current_counter % FREE_COFFEE_AFTER)

            receipt = f"""
☕ *Покупка кофе*

👤 Клиент: {admin_data['client_name']}
📞 Телефон: {admin_data['client_phone']}

📊 *Текущий счетчик кофе:* {current_counter}
🎯 *До бесплатного кофе осталось:* {cups_until_free} чашек

Спасибо за покупку! ☕
            """

        bot.send_message(message.chat.id, receipt, parse_mode='Markdown', reply_markup=admin_menu())
        del user_data[user_id]

    elif message.text == '🍰 Десерты':
        # Обработка покупки десертов
        bot.send_message(message.chat.id, "💵 Введите сумму покупки десертов (в рублях):",
                         reply_markup=cancel_keyboard())
        bot.register_next_step_handler(message, process_dessert_amount)
    else:
        bot.send_message(message.chat.id, "❌ Пожалуйста, выберите тип покупки:", reply_markup=purchase_type_keyboard())
        bot.register_next_step_handler(message, process_purchase_type)


def process_dessert_amount(message):
    user_id = message.from_user.id
    admin_data = user_data.get(user_id, {})

    if message.text == '❌ Отмена':
        if user_id in user_data:
            del user_data[user_id]
        bot.send_message(message.chat.id, "Операция отменена.", reply_markup=admin_menu())
        return

    amount = validate_amount(message.text)
    if not amount:
        bot.send_message(message.chat.id, "❌ Неверная сумма. Введите число больше 0:")
        bot.register_next_step_handler(message, process_dessert_amount)
        return

    # Рассчитываем баллы
    points = calculate_dessert_points(amount)

    # Начисляем баллы
    db.add_dessert_purchase(admin_data['client_phone'], amount, points)

    # Формируем чек
    receipt = f"""
🍰 *Покупка десертов*

👤 Клиент: {admin_data['client_name']}
📞 Телефон: {admin_data['client_phone']}

💰 *Сумма покупки:* {amount} руб.
💎 *Начислено баллов:* {points} ({DESSERT_PERCENTAGE}%)
💳 *Всего баллов у клиента:* {db.get_client_by_phone(admin_data['client_phone'])['points']}

Спасибо за покупку! 🍰
    """

    bot.send_message(message.chat.id, receipt, parse_mode='Markdown', reply_markup=admin_menu())

    # Уведомляем клиента о начисленных баллах
    client = db.get_client_by_phone(admin_data['client_phone'])
    if client:
        try:
            bot.send_message(
                client['telegram_id'],
                f"🍰 *Спасибо за покупку десертов!*\n\n"
                f"💎 Вам начислено: {points} баллов\n"
                f"💰 Сумма покупки: {amount} руб.\n"
                f"💳 Всего баллов: {client['points']}\n\n"
                f"Ждем вас снова! 🎂",
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"Не удалось отправить уведомление клиенту: {e}")

    del user_data[user_id]



# Поиск клиента администратором (добавленная функция)
@bot.message_handler(func=lambda message: message.text == '👥 Поиск клиента' and is_admin(message.from_user.id))
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
@bot.message_handler(func=lambda message: message.text == '📊 Статистика' and is_admin(message.from_user.id))
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
        stats_text += f"{i}. {name} ({phone}) - {points} баллов\n"

    bot.send_message(message.chat.id, stats_text, parse_mode='Markdown', reply_markup=admin_menu())


@bot.message_handler(func=lambda message: message.text == '🔙 Главное меню' and is_admin(message.from_user.id))
def exit_admin_mode(message):
    bot.send_message(message.chat.id, "👋 Возвращаемся в главное меню", reply_markup=main_menu())



# Запуск бота
if __name__ == '__main__':
    print("Бот запущен...")
    bot.infinity_polling()