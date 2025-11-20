from database import Database
from birthday_scheduler import check_birthdays
import sys


def test_birthday_function():
    """Тестирование функции дней рождения"""
    db = Database()

    print("🔍 Testing birthday functions...")

    # Тестируем поиск дней рождения через 7 дней
    clients = db.get_clients_with_upcoming_birthdays(7)
    print(f"🎂 Found {len(clients)} clients with birthdays in 7 days")

    for client in clients:
        print(f"  - {client['name']}: {client['birth_date']} - Current points: {client['points']}")

    # Тестируем полную проверку
    print("\n🔍 Running full birthday check...")
    check_birthdays()


if __name__ == '__main__':
    test_birthday_function()