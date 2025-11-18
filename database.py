import sqlite3
import logging
from datetime import datetime
from config import INITIAL_BONUS_POINTS, DESSERT_PERCENTAGE, FREE_COFFEE_AFTER


class Database:
    def __init__(self, db_name='loyalty.db'):
        self.db_name = db_name
        self.init_db()

    def init_db(self):
        """Инициализация базы данных"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        # Таблица клиентов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS clients (
                telegram_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                birth_date TEXT,
                gender TEXT,
                phone TEXT UNIQUE NOT NULL,
                points INTEGER DEFAULT 100,
                coffee_counter INTEGER DEFAULT 0,
                registration_date TEXT,
                total_spent REAL DEFAULT 0
            )
        ''')

        # Таблица транзакций
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_phone TEXT,
                amount REAL,
                points_earned INTEGER,
                products TEXT,
                date TEXT,
                transaction_type TEXT,
                FOREIGN KEY (client_phone) REFERENCES clients (phone)
            )
        ''')

        conn.commit()
        conn.close()

    def add_client(self, telegram_id, name, birth_date, gender, phone):
        """Добавление нового клиента"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO clients 
                (telegram_id, name, birth_date, gender, phone, points, coffee_counter, registration_date)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (telegram_id, name, birth_date, gender, phone,
                  INITIAL_BONUS_POINTS, 0, datetime.now().isoformat()))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def get_client_by_phone(self, phone):
        """Получение клиента по номеру телефона"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM clients WHERE phone = ?', (phone,))
        client = cursor.fetchone()
        conn.close()

        if client:
            return {
                'telegram_id': client[0],
                'name': client[1],
                'birth_date': client[2],
                'gender': client[3],
                'phone': client[4],
                'points': client[5],
                'coffee_counter': client[6],
                'registration_date': client[7],
                'total_spent': client[8]
            }
        return None

    def get_client_by_telegram_id(self, telegram_id):
        """Получение клиента по Telegram ID"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        cursor.execute('SELECT * FROM clients WHERE telegram_id = ?', (telegram_id,))
        client = cursor.fetchone()
        conn.close()

        if client:
            return {
                'telegram_id': client[0],
                'name': client[1],
                'birth_date': client[2],
                'gender': client[3],
                'phone': client[4],
                'points': client[5],
                'coffee_counter': client[6],
                'registration_date': client[7],
                'total_spent': client[8]
            }
        return None

    def update_client_profile(self, telegram_id, name=None, birth_date=None, gender=None, phone=None):
        """Обновление профиля клиента"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        updates = []
        params = []

        if name:
            updates.append("name = ?")
            params.append(name)
        if birth_date:
            updates.append("birth_date = ?")
            params.append(birth_date)
        if gender:
            updates.append("gender = ?")
            params.append(gender)
        if phone:
            updates.append("phone = ?")
            params.append(phone)

        if updates:
            params.append(telegram_id)
            cursor.execute(f'UPDATE clients SET {", ".join(updates)} WHERE telegram_id = ?', params)
            conn.commit()

        conn.close()

    def add_coffee_purchase(self, phone):
        """Добавление покупки кофе"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        # Получаем текущий счетчик перед обновлением
        cursor.execute('SELECT coffee_counter FROM clients WHERE phone = ?', (phone,))
        old_counter = cursor.fetchone()[0]

        # Увеличиваем счетчик кофе
        cursor.execute('UPDATE clients SET coffee_counter = coffee_counter + 1 WHERE phone = ?', (phone,))

        # Получаем обновленный счетчик
        cursor.execute('SELECT coffee_counter FROM clients WHERE phone = ?', (phone,))
        new_counter = cursor.fetchone()[0]

        # Добавляем запись о транзакции
        cursor.execute('''
            INSERT INTO transactions (client_phone, amount, points_earned, products, date, transaction_type)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (phone, 0, 0, "кофе", datetime.now().isoformat(), "coffee"))

        conn.commit()
        conn.close()

        # Возвращаем кортеж: (это бесплатная чашка, старый счетчик, новый счетчик)
        return new_counter % FREE_COFFEE_AFTER == 0, old_counter, new_counter

    def add_dessert_purchase(self, phone, amount, points):
        """Добавление покупки десертов с начислением баллов"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        # Обновляем баллы клиента и общую сумму
        cursor.execute('UPDATE clients SET points = points + ?, total_spent = total_spent + ? WHERE phone = ?',
                       (points, amount, phone))

        # Добавляем запись о транзакции
        cursor.execute('''
            INSERT INTO transactions (client_phone, amount, points_earned, products, date, transaction_type)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (phone, amount, points, "десерты", datetime.now().isoformat(), "dessert"))

        conn.commit()
        conn.close()

    def reset_coffee_counter(self, phone):
        """Сброс счетчика кофе после бесплатного кофе"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        cursor.execute('UPDATE clients SET coffee_counter = 0 WHERE phone = ?', (phone,))
        conn.commit()
        conn.close()

    def get_coffee_counter(self, phone):
        """Получение текущего счетчика кофе"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        cursor.execute('SELECT coffee_counter FROM clients WHERE phone = ?', (phone,))
        counter = cursor.fetchone()[0]
        conn.close()

        return counter

    def deduct_points(self, phone, points_to_deduct):
        """Списание баллов у клиента"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()

        try:
            # Получаем текущее количество баллов
            cursor.execute('SELECT points FROM clients WHERE phone = ?', (phone,))
            current_points = cursor.fetchone()[0]

            # Проверяем, достаточно ли баллов
            if current_points < points_to_deduct:
                return False, "Недостаточно баллов"

            # Списание баллов
            cursor.execute('UPDATE clients SET points = points - ? WHERE phone = ?',
                           (points_to_deduct, phone))

            # Добавляем запись о транзакции списания
            cursor.execute('''
                INSERT INTO transactions (client_phone, amount, points_earned, products, date, transaction_type)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (phone, 0, -points_to_deduct, "списание баллов", datetime.now().isoformat(), "points_deduction"))

            conn.commit()
            return True, "Баллы успешно списаны"

        except Exception as e:
            conn.rollback()
            return False, f"Ошибка при списании баллов: {str(e)}"
        finally:
            conn.close()

    def get_total_clients_count(self):
        """Получение общего количества клиентов"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM clients')
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def get_all_clients(self):
        """Получение списка всех клиентов"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        cursor.execute('SELECT telegram_id, name, phone FROM clients')
        clients = []
        for row in cursor.fetchall():
            clients.append({
                'telegram_id': row[0],
                'name': row[1],
                'phone': row[2]
            })
        conn.close()
        return clients