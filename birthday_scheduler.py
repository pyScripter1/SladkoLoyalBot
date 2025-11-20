import schedule
import time
import threading
import os
from datetime import datetime, timedelta
from database import Database
from config import BIRTHDAY_NOTIFICATION_DAYS, BIRTHDAY_NOTIFICATION_TIME, BIRTHDAY_BONUS_POINTS
import telebot
from config import BOT_TOKEN

# Создаем папку data если ее нет
os.makedirs('data', exist_ok=True)

# Инициализация бота и базы данных
bot = telebot.TeleBot(BOT_TOKEN)
db = Database()


def send_birthday_notification(client):
    """Отправка поздравления и начисление 300 баллов за 7 дней до ДР"""
    try:
        message = f"""
🎉 *Скоро день рождения!* 🎂

Дорогой(ая) {client['name']}, через {BIRTHDAY_NOTIFICATION_DAYS} дней у вас день рождения! 🥳

Мы дарим вам сладкий подарок:
• *+{BIRTHDAY_BONUS_POINTS} баллов* уже начислены на ваш счет!

*Ваш текущий баланс:* {client['points'] + BIRTHDAY_BONUS_POINTS} баллов

Приходите в нашу кондитерскую Sladko и отпразднуйте ваш особенный день с нами! 🎊

*Покажите это сообщение бариста для получения подарка в день рождения!*
        """

        bot.send_message(
            client['telegram_id'],
            message,
            parse_mode='Markdown'
        )

        # Начисляем 300 баллов
        success = db.add_birthday_bonus(client['phone'], BIRTHDAY_BONUS_POINTS)

        if success:
            print(
                f"✅ Birthday notification and {BIRTHDAY_BONUS_POINTS} points sent to {client['name']} ({client['phone']})")
            db.mark_birthday_notified(client['phone'], datetime.now().isoformat())
        else:
            print(f"❌ Failed to add birthday bonus for {client['name']}")

    except Exception as e:
        print(f"❌ Error sending birthday notification to {client['name']}: {e}")


def check_birthdays():
    """Проверка дней рождения и отправка уведомлений за 7 дней"""
    print(f"🎂 Checking birthdays for {datetime.now().strftime('%Y-%m-%d %H:%M')}...")

    try:
        # Получаем клиентов с днями рождения через 7 дней
        clients = db.get_clients_with_upcoming_birthdays(BIRTHDAY_NOTIFICATION_DAYS)

        print(f"🎉 Found {len(clients)} clients with birthdays in {BIRTHDAY_NOTIFICATION_DAYS} days")

        # Отправляем поздравления и начисляем 300 баллов
        for client in clients:
            send_birthday_notification(client)

        if clients:
            print(f"✅ Successfully sent {len(clients)} birthday notifications with {BIRTHDAY_BONUS_POINTS} points each")
        else:
            print("✅ No birthdays found for today")

    except Exception as e:
        print(f"❌ Error in birthday check: {e}")


def run_birthday_scheduler():
    """Запуск планировщика дней рождения"""
    print("🎂 Birthday scheduler started...")

    # Настраиваем расписание - проверяем каждый день в 12:00
    schedule.every().day.at(BIRTHDAY_NOTIFICATION_TIME).do(check_birthdays)

    # Также запускаем при старте для отладки
    print("🔍 Running initial birthday check...")
    check_birthdays()

    # Бесконечный цикл для планировщика
    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # Проверяем каждую минуту
        except Exception as e:
            print(f"❌ Scheduler error: {e}")
            time.sleep(300)  # Ждем 5 минут при ошибке


def start_birthday_scheduler():
    """Запуск планировщика в отдельном потоке"""
    scheduler_thread = threading.Thread(target=run_birthday_scheduler, daemon=True)
    scheduler_thread.start()
    print("🎂 Birthday scheduler thread started")