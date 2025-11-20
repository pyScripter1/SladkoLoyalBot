import telebot
from telebot import types
import logging
import os
from config import BOT_TOKEN, INITIAL_BONUS_POINTS, FREE_COFFEE_AFTER, ADMIN_IDS, DESSERT_PERCENTAGE, CHANNEL_USERNAME, CHANNEL_ID, CHANNEL_URL
from database import Database
from keyboards import *
from utils import *
from birthday_scheduler import start_birthday_scheduler
import sqlite3

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Создаем папку data если ее нет
os.makedirs('data', exist_ok=True)

# Инициализация бота и базы данных
bot = telebot.TeleBot(BOT_TOKEN)
db = Database()

# Словари для хранения временных данных
user_data = {}
user_subscription_status = {}  # Кэш статуса подписки
broadcast_data = {}  # Данные для рассылки

def is_admin(user_id):
    """Проверяет, является ли пользователь администратором"""
    return user_id in ADMIN_IDS


def check_subscription_required(user_id):
    """Проверяет, требуется ли подписка для пользователя"""
    # Администраторам не требуется подписка
    if is_admin(user_id):
        return False

    # Проверяем кэш
    if user_id in user_subscription_status:
        return not user_subscription_status[user_id]

    # Проверяем подписку
    is_subscribed = check_channel_subscription(bot, user_id, CHANNEL_ID)
    user_subscription_status[user_id] = is_subscribed

    return not is_subscribed


def show_subscription_required(message):
    """Показывает сообщение о необходимости подписки"""
    subscription_text = f"""
🧁 *Добро пожаловать!*

Для использования бота необходимо подписаться на наш канал {CHANNEL_USERNAME}

На канале вы найдете:
• Специальные акции и предложения
• Новинки меню
• Расписание мероприятий
• Эксклюзивные скидки для подписчиков

*После подписки нажмите кнопку «✅ Я подписался»*
    """

    bot.send_message(
        message.chat.id,
        subscription_text,
        parse_mode='Markdown',
        reply_markup=subscription_keyboard()
    )


# Обработчик callback для проверки подписки
@bot.callback_query_handler(func=lambda call: call.data == "check_subscription")
def handle_subscription_check(call):
    user_id = call.from_user.id

    # Проверяем подписку
    is_subscribed = check_channel_subscription(bot, user_id, CHANNEL_ID)
    user_subscription_status[user_id] = is_subscribed

    if is_subscribed:
        # Удаляем сообщение с кнопками подписки
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass

        # Показываем приветственное сообщение
        welcome_text = """
🧁 *Отлично! Спасибо за подписку!*

Теперь вы можете пользоваться всеми функциями бота:

• Зарегистрироваться в системе лояльности
• Копить и тратить баллы
• Участвовать в кофейной программе
• Получать персональные предложения

*Начните с регистрации — нажмите /start*
        """
        bot.send_message(call.message.chat.id, welcome_text, parse_mode='Markdown')
    else:
        # Показываем сообщение, что подписка не найдена
        bot.answer_callback_query(
            call.id,
            "❌ Вы еще не подписались на канал. Пожалуйста, подпишитесь и попробуйте снова.",
            show_alert=True
        )


# Добавляем проверку подписки ко всем основным обработчикам
def subscription_required(func):
    """Декоратор для проверки подписки"""

    def wrapper(message):
        user_id = message.from_user.id

        # Администраторам не требуется подписка
        if is_admin(user_id):
            return func(message)

        # Проверяем подписку
        if check_subscription_required(user_id):
            show_subscription_required(message)
            return

        return func(message)

    return wrapper


# Команда старт
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id

    # Проверяем подписку (кроме администраторов)
    if check_subscription_required(user_id):
        show_subscription_required(message)
        return

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
Добро пожаловать в систему лояльности *кондитерской Sladko!* 🎂

• Получайте 100 баллов за регистрацию
• Копите 3% с каждой покупки
• Каждая 6-я чашка кофе — в подарок

*Давайте начнём вкусное знакомство* — введите своё имя ⬇️
        """
        bot.send_message(message.chat.id, welcome_text, parse_mode='Markdown')
        bot.register_next_step_handler(message, process_name_step)


def process_name_step(message):
    user_id = message.from_user.id
    user_data[user_id] = {'name': message.text}

    bot.send_message(message.chat.id,
                     """
                     Чтобы сделать ваш день рождения ещё слаще — укажите дату!

Введите её в формате *ДД.ММ.ГГГГ* 
(например, 15.05.1990) ✨
""",
                     parse_mode='Markdown', reply_markup=cancel_keyboard())
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
        bot.send_message(message.chat.id, "*Выберите свой пол* — чтобы мы могли делать для вас ещё более персональные и приятные предложения:", parse_mode='Markdown', reply_markup=gender_keyboard())
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

    help_text = """
*❗️Способы указания номера телефона:*

1. *Автоматически* - нажмите кнопку "Поделиться номером"
2. *Вручную* - нажмите кнопку "Ввести номер вручную" и введите номер в формате: +79123456789 или 89123456789

_Рекомендуем использовать автоматический способ_ - это быстрее и надежнее!
    """

    bot.send_message(message.chat.id, help_text, parse_mode='Markdown')
    bot.send_message(message.chat.id,
                     "*Поделитесь вашим номером телефона* для регистрации в программе лояльности:",
                     parse_mode='Markdown',
                     reply_markup=phone_keyboard())
    # УБИРАЕМ register_next_step_handler здесь, потому что контакт обрабатывается отдельно

def process_phone_choice(message):
    user_id = message.from_user.id

    if message.text == '❌ Отмена':
        del user_data[user_id]
        bot.send_message(message.chat.id, "Регистрация отменена.", reply_markup=types.ReplyKeyboardRemove())
        return

    if message.text == '📝 Ввести номер вручную':
        bot.send_message(message.chat.id,
                        "📝 Введите ваш номер телефона в формате +79123456789 или 89123456789:",
                        reply_markup=manual_phone_keyboard())
        bot.register_next_step_handler(message, process_manual_phone)
        return

    # Если пользователь нажал "Поделиться номером" - просто ждем контакт
    if message.text == "📱 Поделиться номером":
        # Ничего не делаем, просто ждем когда пользователь отправит контакт
        # Обработчик handle_contact сам перехватит контакт
        return

    # Если это не кнопка, а сразу введен номер
    phone = validate_phone(message.text)
    if phone:
        process_valid_phone(user_id, phone)
    else:
        bot.send_message(message.chat.id,
                        "❌ Неверный формат номера. Пожалуйста, выберите способ ввода:",
                        reply_markup=phone_keyboard())
        bot.register_next_step_handler(message, process_phone_choice)

def process_manual_phone(message):
    user_id = message.from_user.id

    if message.text == '❌ Отмена':
        del user_data[user_id]
        bot.send_message(message.chat.id, "Регистрация отменена.", reply_markup=types.ReplyKeyboardRemove())
        return

    phone = validate_phone(message.text)
    if phone:
        process_valid_phone(user_id, phone)
    else:
        bot.send_message(message.chat.id,
                        "❌ Неверный формат номера. Введите номер в формате +79123456789 или 89123456789:",
                        reply_markup=manual_phone_keyboard())
        bot.register_next_step_handler(message, process_manual_phone)


def process_valid_phone(user_id, phone):
    """Обработка валидного номера телефона"""
    print(f"Processing valid phone: {phone}")

    # Проверяем, не зарегистрирован ли уже этот номер
    existing_client = db.get_client_by_phone(phone)
    if existing_client:
        bot.send_message(user_id, "❌ Этот номер телефона уже зарегистрирован.")
        if user_id in user_data:
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
🧁 * Поздравляем с регистрацией, {user_data[user_id]['name']}!* 

 *Вам начислено: {INITIAL_BONUS_POINTS} баллов*

Теперь вы можете:
• Получать *кешбэк 3%* с каждой покупки десертов
• *Наслаждать бесплатным кофе* после 5 сладких визитов

_Используйте меню ниже и откройте все вкусные возможности Sladko!_ 💛
        """
        bot.send_message(user_id, welcome_message, parse_mode='Markdown', reply_markup=main_menu())
    else:
        bot.send_message(user_id, "❌ Произошла ошибка при регистрации. Попробуйте позже.")

    if user_id in user_data:
        del user_data[user_id]


def process_phone_step(message):
    user_id = message.from_user.id

    if message.text == '❌ Отмена':
        del user_data[user_id]
        bot.send_message(message.chat.id, "Регистрация отменена.", reply_markup=types.ReplyKeyboardRemove())
        return

    # Если пользователь нажал "Поделиться номером" но не отправил контакт
    if message.text == "📱 Поделиться номером":
        bot.send_message(message.chat.id,
                        "Пожалуйста, нажмите на кнопку '📱 Поделиться номером' и подтвердите отправку контакта.",
                        reply_markup=phone_keyboard())
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
🧁 * Поздравляем с регистрацией, {user_data[user_id]['name']}!* 

 *Вам начислено: {INITIAL_BONUS_POINTS} баллов*

Теперь вы можете:
• Получать *кешбэк от 3%* с каждой покупки десертов
• *Наслаждать бесплатным кофе* после 5 сладких визитов

_Используйте меню ниже и откройте все вкусные возможности Sladko!_ 💛
            """
            bot.send_message(message.chat.id, welcome_message, parse_mode='Markdown', reply_markup=main_menu())
        else:
            bot.send_message(message.chat.id, "❌ Произошла ошибка при регистрации. Попробуйте позже.")

        del user_data[user_id]
    else:
        bot.send_message(message.chat.id,
                        "❌ Неверный формат номера. Пожалуйста, введите номер вручную или поделитесь контактом:",
                        reply_markup=phone_keyboard())
        bot.register_next_step_handler(message, process_phone_step)


def process_deduct_phone(message):
    """Обработка номера телефона для списания баллов"""
    if message.text == '❌ Отмена':
        bot.send_message(message.chat.id, "Операция отменена.", reply_markup=admin_menu())
        return

    phone = validate_phone(message.text)
    if not phone:
        bot.send_message(message.chat.id, "❌ Неверный формат номера. Попробуйте еще раз:")
        bot.register_next_step_handler(message, process_deduct_phone)
        return

    client = db.get_client_by_phone(phone)
    if not client:
        bot.send_message(message.chat.id, "❌ Клиент с таким номером не найден.")
        return

    # Сохраняем данные клиента для следующего шага
    user_data[message.from_user.id] = {
        'client_phone': phone,
        'client_name': client['name'],
        'client_points': client['points'],
        'action': 'deduct_points'
    }

    info_text = f"""
👤 *Клиент:* {client['name']}
📞 *Телефон:* {phone}
💎 *Текущие баллы:* {client['points']}

💵 *Введите сумму покупки (в рублях) для списания 50% баллов:*
    """

    bot.send_message(message.chat.id, info_text, parse_mode='Markdown', reply_markup=cancel_keyboard())
    bot.register_next_step_handler(message, process_purchase_amount_for_deduction)


def process_purchase_amount_for_deduction(message):
    """Обработка суммы покупки для списания баллов"""
    user_id = message.from_user.id
    admin_data = user_data.get(user_id, {})

    if message.text == '❌ Отмена':
        if user_id in user_data:
            del user_data[user_id]
        bot.send_message(message.chat.id, "Операция отменена.", reply_markup=admin_menu())
        return

    if admin_data.get('action') != 'deduct_points':
        bot.send_message(message.chat.id, "❌ Ошибка процесса. Начните заново.")
        if user_id in user_data:
            del user_data[user_id]
        return

    # Валидируем сумму покупки
    amount = validate_amount(message.text)
    if not amount:
        bot.send_message(message.chat.id, "❌ Неверная сумма. Введите число больше 0:")
        bot.register_next_step_handler(message, process_purchase_amount_for_deduction)
        return

    # Рассчитываем 50% от суммы покупки (максимальное списание)
    max_deduction = amount * 0.5
    points_to_deduct = min(int(max_deduction), admin_data['client_points'])

    # Обновляем данные в user_data
    user_data[user_id]['purchase_amount'] = amount
    user_data[user_id]['points_to_deduct'] = points_to_deduct

    confirmation_text = f"""
💰 *Подтверждение списания баллов*

👤 Клиент: {admin_data['client_name']}
📞 Телефон: {admin_data['client_phone']}

💵 Сумма покупки: {amount} руб.
💎 Максимальное списание (50%): {int(max_deduction)} баллов
💳 Доступно баллов: {admin_data['client_points']}

✅ *Будет списано: {points_to_deduct} баллов*

Подтвердите списание:
    """

    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add('✅ Подтвердить списание', '❌ Отмена')

    bot.send_message(message.chat.id, confirmation_text, parse_mode='Markdown', reply_markup=keyboard)
    bot.register_next_step_handler(message, process_deduction_confirmation)


def process_deduction_confirmation(message):
    """Обработка подтверждения списания баллов"""
    user_id = message.from_user.id
    admin_data = user_data.get(user_id, {})

    if message.text == '❌ Отмена':
        if user_id in user_data:
            del user_data[user_id]
        bot.send_message(message.chat.id, "Операция отменена.", reply_markup=admin_menu())
        return

    if message.text != '✅ Подтвердить списание':
        bot.send_message(message.chat.id, "❌ Операция отменена.", reply_markup=admin_menu())
        if user_id in user_data:
            del user_data[user_id]
        return

    # Выполняем списание баллов
    success, message_text = db.deduct_points(
        admin_data['client_phone'],
        admin_data['points_to_deduct']
    )

    if success:
        # Получаем обновленные данные клиента
        updated_client = db.get_client_by_phone(admin_data['client_phone'])

        receipt_text = f"""
✅ *Списание баллов успешно выполнено*

👤 Клиент: {admin_data['client_name']}
📞 Телефон: {admin_data['client_phone']}

💵 Сумма покупки: {admin_data['purchase_amount']} руб.
💎 Списано баллов: {admin_data['points_to_deduct']}
💳 Осталось баллов: {updated_client['points']}

💰 Клиент оплатил баллами: {admin_data['points_to_deduct']} руб.
💵 К оплате: {admin_data['purchase_amount'] - admin_data['points_to_deduct']} руб.

Спасибо за покупку! 🍰
        """

        # Уведомляем клиента о списании баллов
        try:
            client = db.get_client_by_phone(admin_data['client_phone'])
            if client and client['telegram_id']:
                bot.send_message(
                    client['telegram_id'],
                    f"*Списание баллов* 🍩\n\n"
                    f"С вашего счета списано: {admin_data['points_to_deduct']} баллов\n"
                    f"Остаток баллов: {updated_client['points']}\n"
                    f"Спасибо за покупку! 🎂",
                    parse_mode='Markdown'
                )
        except Exception as e:
            print(f"Не удалось отправить уведомление клиенту: {e}")

    else:
        receipt_text = f"❌ {message_text}"

    bot.send_message(message.chat.id, receipt_text, parse_mode='Markdown', reply_markup=admin_menu())

    # Очищаем временные данные
    if user_id in user_data:
        del user_data[user_id]


@bot.message_handler(func=lambda message: message.text == '💸 Списать баллы' and is_admin(message.from_user.id))
def deduct_points_start(message):
    """Начало процесса списания баллов"""
    bot.send_message(message.chat.id, "💸 Введите номер телефона клиента для списания баллов:",
                     reply_markup=cancel_keyboard())
    bot.register_next_step_handler(message, process_deduct_phone)

@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    user_id = message.from_user.id
    print(f"Contact received from user {user_id}: {message.contact}")

    # Если пользователь в процессе регистрации
    if user_id in user_data:
        phone = validate_phone(message.contact)
        print(f"Validated phone: {phone}")
        if phone:
            process_valid_phone(user_id, phone)
        else:
            bot.send_message(message.chat.id,
                           "❌ Не удалось распознать номер телефона. Пожалуйста, попробуйте другой способ:",
                           reply_markup=phone_keyboard())
    else:
        # Если контакт отправлен вне регистрации
        phone = validate_phone(message.contact)
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
        else:
            bot.send_message(message.chat.id,
                           "❌ Не удалось распознать номер телефона. Зарегистрируйтесь с помощью /start")


@bot.message_handler(func=lambda message: message.text == "📱 Поделиться номером")
@subscription_required
def handle_share_phone_button(message):
    """Обрабатывает нажатие на кнопку 'Поделиться номером'"""
    user_id = message.from_user.id
    print(f"Share phone button pressed by user {user_id}")

    if user_id in user_data:
        # Просто напоминаем пользователю отправить контакт
        bot.send_message(message.chat.id,
                         "Пожалуйста, нажмите на кнопку '📱 Поделиться номером' ниже и подтвердите отправку контакта.",
                         reply_markup=phone_keyboard())
    else:
        bot.send_message(message.chat.id,
                         "Начните регистрацию с помощью /start")


@bot.message_handler(func=lambda message: message.text == "📝 Ввести номер вручную")
@subscription_required
def handle_manual_phone_button(message):
    """Обрабатывает нажатие на кнопку 'Ввести номер вручную'"""
    user_id = message.from_user.id
    print(f"Manual phone button pressed by user {user_id}")

    if user_id in user_data:
        bot.send_message(message.chat.id,
                         "📝 Введите ваш номер телефона в формате +79123456789 или 89123456789:",
                         reply_markup=manual_phone_keyboard())
        bot.register_next_step_handler(message, process_manual_phone)
    else:
        bot.send_message(message.chat.id,
                         "Начните регистрацию с помощью /start")


# Команды пользователя
@bot.message_handler(func=lambda message: message.text == '👤 Мой профиль')
@subscription_required
def show_profile(message):
    client = db.get_client_by_telegram_id(message.from_user.id)
    if client:
        profile_text = format_profile(client)
        bot.send_message(message.chat.id, profile_text, parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, "❌ Вы не зарегистрированы. Используйте /start для регистрации.")


@bot.message_handler(func=lambda message: message.text == '💎 Мои баллы')
@subscription_required
def show_points(message):
    client = db.get_client_by_telegram_id(message.from_user.id)
    if client:
        points_text = f"""
*Ваш сладкий кешбэк: {client['points']}*

✨ *Как использовать баллы?*
1 балл = 1 рубль 
За одну покупку можно оплатить до *50%* суммы!

Просто скажите администратору, что хотите оплатить часть заказа баллами — и наслаждайтесь скидкой со вкусом! 💛

        """
        bot.send_message(message.chat.id, points_text, parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, "❌ Вы не зарегистрированы.")


@bot.message_handler(func=lambda message: message.text == '☕ Счетчик кофе')
@subscription_required
def show_coffee_counter(message):
    client = db.get_client_by_telegram_id(message.from_user.id)
    if client:
        coffee_progress = client['coffee_counter'] % FREE_COFFEE_AFTER
        cups_until_free = FREE_COFFEE_AFTER - coffee_progress

        coffee_text = f"""
*Ваша кофейная статистика, {client['name']}*

☕️ Выпито чашек кофе: {client['coffee_counter']}
{'☕️ *Следующая чашка кофе бесплатная!*' if coffee_progress == 0 and client['coffee_counter'] > 0 else ''}
И помните: *каждая {FREE_COFFEE_AFTER}-я чашка кофе в подарок!*
        """
        bot.send_message(message.chat.id, coffee_text, parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, "❌ Вы не зарегистрированы.")


@bot.message_handler(func=lambda message: message.text == '✏️ Редактировать профиль')
@subscription_required
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
        free_coffee, old_counter, new_counter = db.add_coffee_purchase(admin_data['client_phone'])

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

            # Уведомляем клиента о начислении чашки кофе
            client = db.get_client_by_phone(admin_data['client_phone'])
            if client:
                try:
                    bot.send_message(
                        client['telegram_id'],
                        f"☕️ *Начислена чашка кофе!*"
                    )
                except Exception as e:
                    print(f"Не удалось отправить уведомление клиенту: {e}")

            receipt = f"""
☕ *Покупка кофе*

👤 Клиент: {admin_data['client_name']}
📞 Телефон: {admin_data['client_phone']}

📊 *Текущий счетчик кофе:* {current_counter}
🎯 *До бесплатного кофе осталось:* {cups_until_free} чашек

✅ *Клиент уведомлен о начислении чашки кофе*

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
                f"*Спасибо за покупку десертов!* 🧁\n\n"
                f"Вам начислено: {points} баллов\n"
                f"Всего баллов: {client['points']}\n\n"
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
    conn = sqlite3.connect('data/loyalty.db')
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


@bot.message_handler(func=lambda message: message.text == '📢 Создать рассылку' and is_admin(message.from_user.id))
def start_broadcast(message):
    """Начало создания рассылки"""
    user_id = message.from_user.id

    # Инициализируем данные рассылки
    broadcast_data[user_id] = {
        'text': None,
        'photo': None,
        'message_type': None,
        'preview_message_id': None
    }

    help_text = """
📢 *Создание рассылки*

Вы можете создать рассылку двух типов:
• 📝 *Только текст* - текстовое сообщение
• 🖼️ *С фотографией* - сообщение с изображением и текстом

*Процесс:*
1. Выберите тип рассылки
2. Введите текст сообщения
3. Если нужно - прикрепите фото
4. Посмотрите предпросмотр
5. Отправьте всем клиентам
    """

    bot.send_message(message.chat.id, help_text, parse_mode='Markdown', reply_markup=broadcast_keyboard())


@bot.message_handler(func=lambda message: message.text == '📝 Только текст' and is_admin(message.from_user.id))
def text_broadcast(message):
    """Выбор рассылки только с текстом"""
    user_id = message.from_user.id

    if user_id not in broadcast_data:
        broadcast_data[user_id] = {}

    broadcast_data[user_id]['message_type'] = 'text'

    formatting_help = """
📝 ФОРМАТИРОВАНИЕ ТЕКСТА

Вы можете использовать Markdown разметку:

*Жирный текст*
_Курсивный текст_

Теперь введите текст рассылки:
    """

    bot.send_message(message.chat.id, formatting_help, reply_markup=cancel_keyboard())

    bot.register_next_step_handler(message, process_broadcast_text)


@bot.message_handler(func=lambda message: message.text == '🖼️ С фотографией' and is_admin(message.from_user.id))
def photo_broadcast(message):
    """Выбор рассылки с фотографией"""
    user_id = message.from_user.id

    if user_id not in broadcast_data:
        broadcast_data[user_id] = {}

    broadcast_data[user_id]['message_type'] = 'photo'

    bot.send_message(message.chat.id,
                     "🖼️ Отправьте фотографию для рассылки:",
                     reply_markup=cancel_keyboard())


@bot.message_handler(content_types=['photo'], func=lambda message: is_admin(message.from_user.id))
def process_broadcast_photo(message):
    """Обработка фотографии для рассылки"""
    user_id = message.from_user.id

    if user_id not in broadcast_data or broadcast_data[user_id].get('message_type') != 'photo':
        return

    # Сохраняем file_id фотографии
    broadcast_data[user_id]['photo'] = message.photo[-1].file_id

    bot.send_message(message.chat.id,
                     "✅ Фотография получена! Теперь введите текст для рассылки:\n\n*Поддерживается Markdown разметка*",
                     parse_mode='Markdown',
                     reply_markup=cancel_keyboard())

    bot.register_next_step_handler(message, process_broadcast_text)


def process_broadcast_text(message):
    """Обработка текста рассылки"""
    user_id = message.from_user.id

    if message.text == '❌ Отмена':
        if user_id in broadcast_data:
            del broadcast_data[user_id]
        bot.send_message(message.chat.id, "❌ Рассылка отменена.", reply_markup=admin_menu())
        return

    if user_id not in broadcast_data:
        bot.send_message(message.chat.id, "❌ Ошибка: данные рассылки потеряны. Начните заново.",
                         reply_markup=admin_menu())
        return

    # Сохраняем текст
    broadcast_data[user_id]['text'] = message.text

    bot.send_message(message.chat.id,
                     "✅ Текст сохранен! Теперь вы можете:\n\n• 👀 Посмотреть предпросмотр\n• ✅ Отправить всем клиентам",
                     reply_markup=broadcast_keyboard())


@bot.message_handler(func=lambda message: message.text == '👀 Предпросмотр' and is_admin(message.from_user.id))
def preview_broadcast(message):
    """Предпросмотр рассылки"""
    user_id = message.from_user.id

    if user_id not in broadcast_data:
        bot.send_message(message.chat.id, "❌ Сначала создайте рассылку.", reply_markup=broadcast_keyboard())
        return

    data = broadcast_data[user_id]

    if not data.get('text'):
        bot.send_message(message.chat.id, "❌ Текст рассылки не заполнен.", reply_markup=broadcast_keyboard())
        return

    preview_text = "👀 *ПРЕДПРОСМОТР РАССЫЛКИ*\n\n" + data['text']

    try:
        if data.get('message_type') == 'photo' and data.get('photo'):
            # Удаляем предыдущее сообщение предпросмотра, если есть
            if data.get('preview_message_id'):
                try:
                    bot.delete_message(message.chat.id, data['preview_message_id'])
                except:
                    pass

            # Отправляем фото с текстом
            sent_message = bot.send_photo(message.chat.id,
                                          data['photo'],
                                          caption=preview_text,
                                          parse_mode='Markdown')
            broadcast_data[user_id]['preview_message_id'] = sent_message.message_id
        else:
            # Только текст
            if data.get('preview_message_id'):
                try:
                    bot.delete_message(message.chat.id, data['preview_message_id'])
                except:
                    pass

            sent_message = bot.send_message(message.chat.id, preview_text, parse_mode='Markdown')
            broadcast_data[user_id]['preview_message_id'] = sent_message.message_id

        bot.send_message(message.chat.id,
                         "📊 *Статистика рассылки:*\n\n" +
                         f"👥 Будет отправлено: *{db.get_total_clients_count()}* клиентам\n" +
                         f"📝 Тип: *{'С фото' if data.get('message_type') == 'photo' else 'Только текст'}*\n",
                         parse_mode='Markdown',
                         reply_markup=broadcast_keyboard())

    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка при предпросмотре: {str(e)}", reply_markup=broadcast_keyboard())


@bot.message_handler(func=lambda message: message.text == '✅ Отправить всем' and is_admin(message.from_user.id))
def confirm_broadcast(message):
    """Подтверждение отправки рассылки"""
    user_id = message.from_user.id

    if user_id not in broadcast_data or not broadcast_data[user_id].get('text'):
        bot.send_message(message.chat.id, "❌ Сначала создайте рассылку.", reply_markup=broadcast_keyboard())
        return

    total_clients = db.get_total_clients_count()

    confirm_text = f"""
⚠️ *ПОДТВЕРЖДЕНИЕ РАССЫЛКИ*

📝 *Тип:* {'🖼️ С фотографией' if broadcast_data[user_id].get('message_type') == 'photo' else '📝 Только текст'}
👥 *Получатели:* {total_clients} клиентов

*Вы уверены, что хотите отправить эту рассылку всем клиентам?*

*Действие нельзя отменить!*
    """

    bot.send_message(message.chat.id, confirm_text, parse_mode='Markdown', reply_markup=confirm_broadcast_keyboard())


@bot.message_handler(func=lambda message: message.text == '✅ Да, отправить всем' and is_admin(message.from_user.id))
def send_broadcast(message):
    """Отправка рассылки всем клиентам"""
    user_id = message.from_user.id

    if user_id not in broadcast_data:
        bot.send_message(message.chat.id, "❌ Данные рассылки не найдены.", reply_markup=admin_menu())
        return

    data = broadcast_data[user_id]

    # Получаем всех клиентов через базу данных
    clients = db.get_all_clients()
    total_clients = len(clients)

    if total_clients == 0:
        bot.send_message(message.chat.id, "❌ В базе нет клиентов для рассылки.", reply_markup=admin_menu())
        return

    # Отправляем начальное сообщение о прогрессе
    progress_message = bot.send_message(message.chat.id,
                                        f"📤 *Начинаем рассылку...*\n\n0/{total_clients} отправлено",
                                        parse_mode='Markdown')

    success_count = 0
    fail_count = 0
    failed_clients = []

    # Отправляем сообщения всем клиентам
    for i, client in enumerate(clients, 1):
        try:
            if data.get('message_type') == 'photo' and data.get('photo'):
                # Отправляем фото с текстом
                bot.send_photo(client['telegram_id'],
                               data['photo'],
                               caption=data['text'],
                               parse_mode='Markdown')
            else:
                # Отправляем только текст
                bot.send_message(client['telegram_id'],
                                 data['text'],
                                 parse_mode='Markdown')

            success_count += 1

        except Exception as e:
            fail_count += 1
            failed_clients.append({
                'name': client['name'],
                'phone': client['phone'],
                'error': str(e)
            })

        # Обновляем прогресс каждые 10 сообщений или на последнем
        if i % 10 == 0 or i == total_clients:
            try:
                bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=progress_message.message_id,
                    text=f"📤 *Рассылка в процессе...*\n\n{i}/{total_clients} отправлено\n✅ Успешно: {success_count}\n❌ Ошибок: {fail_count}",
                    parse_mode='Markdown'
                )
            except:
                pass

        # Небольшая задержка чтобы не превысить лимиты Telegram
        import time
        if i % 20 == 0:
            time.sleep(1)

    # Формируем отчет
    report_text = f"""
📊 *ОТЧЕТ О РАССЫЛКЕ*

✅ *Успешно отправлено:* {success_count} клиентам
❌ *Не удалось отправить:* {fail_count} клиентам
📈 *Эффективность:* {success_count / total_clients * 100:.1f}%

👥 *Всего в базе:* {total_clients} клиентов
    """

    if failed_clients:
        report_text += f"\n\n*Клиенты, которым не удалось отправить:*\n"
        for client in failed_clients[:10]:  # Показываем первые 10 ошибок
            report_text += f"• {client['name']} ({client['phone']})\n"

        if len(failed_clients) > 10:
            report_text += f"• ... и еще {len(failed_clients) - 10} клиентов\n"

    # Отправляем финальный отчет
    bot.send_message(message.chat.id, report_text, parse_mode='Markdown', reply_markup=admin_menu())

    # Очищаем данные рассылки
    if user_id in broadcast_data:
        del broadcast_data[user_id]


@bot.message_handler(
    func=lambda message: message.text in ['❌ Отменить рассылку', '❌ Нет, отменить'] and is_admin(message.from_user.id))
def cancel_broadcast(message):
    """Отмена рассылки"""
    user_id = message.from_user.id

    if user_id in broadcast_data:
        del broadcast_data[user_id]

    bot.send_message(message.chat.id, "❌ Рассылка отменена.", reply_markup=admin_menu())



@bot.message_handler(func=lambda message: message.text == '🔙 Главное меню' and is_admin(message.from_user.id))
def exit_admin_mode(message):
    bot.send_message(message.chat.id, "👋 Возвращаемся в главное меню", reply_markup=main_menu())



# Запуск бота
if __name__ == '__main__':
    print("Бот запущен...")

    # Запускаем планировщик дней рождения
    try:
        start_birthday_scheduler()
        print("✅ Birthday scheduler initialized")
    except Exception as e:
        print(f"❌ Failed to start birthday scheduler: {e}")

    bot.infinity_polling()