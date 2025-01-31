import sqlite3
import json
import random
import threading
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler


db_ready = threading.Event()

# Инициализация Flask
app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)  # Разрешить запросы с любого домена

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('crypto_game.db')
    cursor = conn.cursor()
    
    print("Создание таблиц...")
    
    # Таблица игроков
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            balance REAL,
            portfolio TEXT,
            referrer_id INTEGER,
            referral_code TEXT
        )
    ''')
    print("Таблица players создана или уже существует.")
    
    # Таблица истории цен TND
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tnd_price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,  -- Автоинкрементное поле
            timestamp INTEGER,
            price REAL
        )
    ''')
    print("Таблица tnd_price_history создана или уже существует.")
    
    # Добавляем начальную цену токена (10 TNDUSD)
    cursor.execute('SELECT COUNT(*) FROM tnd_price_history')
    if cursor.fetchone()[0] == 0:  # Если таблица пустая
        cursor.execute('INSERT INTO tnd_price_history (timestamp, price) VALUES (?, ?)', (int(time.time()), 10.0))
        print("Начальная цена токена добавлена.")
    
    # Таблица заявок
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            order_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            type TEXT,  -- buy или sell
            price REAL,
            amount REAL,
            status TEXT  -- active или completed
        )
    ''')
    print("Таблица orders создана или уже существует.")
    
    conn.commit()
    conn.close()
    print("База данных инициализирована.")
    
    db_ready.set()  # Сигнализируем, что база данных готова

# Регистрация нового игрока
def register_player(user_id, username, referrer_id=None):
    conn = sqlite3.connect('crypto_game.db')
    cursor = conn.cursor()
    referral_code = f"ref_{user_id}"
    cursor.execute('INSERT OR IGNORE INTO players (user_id, username, balance, portfolio, referrer_id, referral_code) VALUES (?, ?, ?, ?, ?, ?)',
                   (user_id, username, 1000.0, json.dumps({"TND": 0}), referrer_id, referral_code))
    conn.commit()
    conn.close()

# Получение данных игрока
def get_player_data(user_id):
    conn = sqlite3.connect('crypto_game.db')
    cursor = conn.cursor()
    cursor.execute('SELECT balance, portfolio, referral_code FROM players WHERE user_id = ?', (user_id,))
    data = cursor.fetchone()
    conn.close()
    if data:
        return {'balance': data[0], 'portfolio': json.loads(data[1]), 'referral_code': data[2]}
    return None

# Обновление данных игрока
def update_player_data(user_id, balance, portfolio):
    conn = sqlite3.connect('crypto_game.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE players SET balance = ?, portfolio = ? WHERE user_id = ?',
                   (balance, json.dumps(portfolio), user_id))
    conn.commit()
    conn.close()

# Динамическая цена TND
def update_tnd_price():
    db_ready.wait()  # Ждем, пока база данных не будет готова
    
    while True:
        conn = sqlite3.connect('crypto_game.db')
        cursor = conn.cursor()
        
        # Получаем текущую цену
        cursor.execute('SELECT price FROM tnd_price_history ORDER BY timestamp DESC LIMIT 1')
        last_price = cursor.fetchone()
        last_price = last_price[0] if last_price else 10.0  # Стартовая цена
        
        # Изменяем цену случайным образом (не более чем на 10%)
        new_price = last_price * (1 + random.uniform(-0.1, 0.1))
        
        # Сохраняем новую цену
        current_timestamp = int(time.time())  # Уникальное значение времени
        cursor.execute('INSERT INTO tnd_price_history (timestamp, price) VALUES (?, ?)', (current_timestamp, new_price))
        conn.commit()
        conn.close()
        
        # Ждем 10 минут
        time.sleep(600)

# Запуск в отдельном потоке
threading.Thread(target=update_tnd_price, daemon=True).start()

# Маршруты Flask
@app.route('/')
def index():
    return app.send_static_file('index.html')

@app.route('/get_player_data')
def get_player_data_web():
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({"error": "user_id не указан"}), 400

    player_data = get_player_data(user_id)
    if player_data:
        return jsonify(player_data)
    return jsonify({"error": "Игрок не найден."}), 404

@app.route('/get_tnd_price_history')
def get_tnd_price_history():
    conn = sqlite3.connect('crypto_game.db')
    cursor = conn.cursor()
    cursor.execute('SELECT timestamp, price FROM tnd_price_history ORDER BY timestamp DESC LIMIT 144')  # Последние 24 часа
    data = cursor.fetchall()
    conn.close()
    return jsonify([{"timestamp": entry[0], "price": entry[1]} for entry in data])

@app.route('/get_order_book')
def get_order_book():
    conn = sqlite3.connect('crypto_game.db')
    cursor = conn.cursor()
    cursor.execute('SELECT type, price, amount FROM orders WHERE status = "active"')
    data = cursor.fetchall()
    conn.close()
    return jsonify([{"type": entry[0], "price": entry[1], "amount": entry[2]} for entry in data])

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    referrer_id = context.args[0] if context.args else None

    # Регистрируем игрока
    register_player(user_id, username, referrer_id)

    # Отправляем сообщение с кнопкой для открытия Web App
    web_app_url = "https://riddlerspb.github.io/Lottery_bot/"  # Измените версию при каждом обновлении
    keyboard = [
        [InlineKeyboardButton("Открыть игру", web_app=WebAppInfo(url=web_app_url))]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Добро пожаловать! Нажмите кнопку, чтобы открыть игру:", reply_markup=reply_markup)

# Основная функция
def main():
    init_db()  # Инициализация базы данных

    # Запуск потока для обновления цены токена
    threading.Thread(target=update_tnd_price, daemon=True).start()

    application = Application.builder().token("8050714665:AAHCof0RXKlSqcqtoqw1iVNKhch9POiFYsI").build()
    application.add_handler(CommandHandler("start", start))
    application.run_polling()

if __name__ == "__main__":
    # Запуск Flask в отдельном потоке
    threading.Thread(target=app.run, kwargs={"port": 5000}, daemon=True).start()
    
    # Запуск бота
    main()