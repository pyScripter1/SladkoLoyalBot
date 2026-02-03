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
        # Проверяем, что у клиента есть telegram_id
        if not client.get('telegram_id'):
            print(f"⚠️ Client {client['name']} ({client['phone']}) has no telegram_id, skipping notification")
            return

        # Сначала начисляем баллы
        success = db.add_birthday_bonus(client['phone'], BIRTHDAY_BONUS_POINTS)
        
        if not success:
            print(f"❌ Failed to add birthday bonus for {client['name']} ({client['phone']})")
            return

        # Получаем обновленный баланс после начисления
        updated_client = db.get_client_by_phone(client['phone'])
        if not updated_client:
            print(f"❌ Failed to get updated client data for {client['name']} ({client['phone']})")
            return

        new_balance = updated_client['points']

        # Формируем и отправляем сообщение с актуальным балансом
        message = f"""
🎉 *Скоро день рождения!* 🎂

Дорогой(ая) {client['name']}, через {BIRTHDAY_NOTIFICATION_DAYS} дней у вас день рождения! 🥳

Мы дарим вам сладкий подарок:
• *+{BIRTHDAY_BONUS_POINTS} баллов* уже начислены на ваш счет!

*Ваш текущий баланс:* {new_balance} баллов

Приходите в нашу кондитерскую Sladko и отпразднуйте ваш особенный день с нами! 🎊

*Покажите это сообщение бариста для получения подарка в день рождения!*
        """

        # Отправляем сообщение
        try:
            bot.send_message(
                client['telegram_id'],
                message,
                parse_mode='Markdown'
            )
            
            # Помечаем, что уведомление отправлено только после успешной отправки
            db.mark_birthday_notified(client['phone'], datetime.now().isoformat())
            print(f"✅ Birthday notification and {BIRTHDAY_BONUS_POINTS} points sent to {client['name']} ({client['phone']})")
            
        except Exception as send_error:
            print(f"❌ Error sending message to {client['name']} ({client['phone']}): {send_error}")
            # Баллы уже начислены, но сообщение не отправлено
            # Можно добавить логику для отката начисления, если нужно

    except Exception as e:
        print(f"❌ Error in birthday notification for {client.get('name', 'Unknown')}: {e}")


def check_birthdays():
    """Проверка дней рождения и отправка уведомлений за 7 дней"""
    print(f"🎂 Checking birthdays for {datetime.now().strftime('%Y-%m-%d %H:%M')}...")

    try:
        # Получаем клиентов с днями рождения через 7 дней
        clients = db.get_clients_with_upcoming_birthdays(BIRTHDAY_NOTIFICATION_DAYS)

        print(f"🎉 Found {len(clients)} clients with birthdays in {BIRTHDAY_NOTIFICATION_DAYS} days")

        # Отправляем поздравления и начисляем 300 баллов
        success_count = 0
        fail_count = 0
        
        for client in clients:
            try:
                send_birthday_notification(client)
                success_count += 1
            except Exception as e:
                fail_count += 1
                print(f"❌ Failed to send notification to {client.get('name', 'Unknown')}: {e}")

        if clients:
            print(f"✅ Birthday check completed: {success_count} successful, {fail_count} failed out of {len(clients)} total")
        else:
            print("✅ No birthdays found for today")

    except Exception as e:
        print(f"❌ Error in birthday check: {e}")
        import traceback
        traceback.print_exc()


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