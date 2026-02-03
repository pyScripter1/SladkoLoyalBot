import os

# Конфигурация бота
BOT_TOKEN = os.getenv('BOT_TOKEN', '')

# Настройки лояльности
INITIAL_BONUS_POINTS = 100
DESSERT_PERCENTAGE = 3  # 3% от стоимости десертов начисляется баллами
FREE_COFFEE_AFTER = 6  # Каждая 6-я чашка бесплатная

# Список администраторов
ADMIN_IDS = []  # Ваш Telegram ID
#1920466733,
# Настройки канала для обязательной подписки
CHANNEL_USERNAME = ""
CHANNEL_URL = "https://t.me/"
CHANNEL_ID = ""

# Настройки birthday рассылки
BIRTHDAY_NOTIFICATION_DAYS = 7  # За сколько дней уведомлять
BIRTHDAY_NOTIFICATION_TIME = "12:00"  # Время отправки (12:00)
BIRTHDAY_BONUS_POINTS = 300  # 300 баллов за 7 денй до др