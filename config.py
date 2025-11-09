import os

# Конфигурация бота
BOT_TOKEN = os.getenv('BOT_TOKEN', '')

# Настройки лояльности
INITIAL_BONUS_POINTS = 100
DESSERT_PERCENTAGE = 3  # 3% от стоимости десертов начисляется баллами
FREE_COFFEE_AFTER = 6  # Каждая 6-я чашка бесплатная

# Список администраторов
ADMIN_IDS = []  # Ваш Telegram ID

