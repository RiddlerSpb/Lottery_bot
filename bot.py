import sqlite3
import json
import random
import threading
import time
from flask import Flask, request, jsonify
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

# Инициализация Flask для Web App
app = Flask(__name__)

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('crypto_game.db')
    cursor = conn.cursor()
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
    conn.commit()
    conn.close()

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

# Покупка TND
@app.route('/buy_tnd')
def buy_tnd():
    user_id = request.args.get('user_id')
    player_data = get_player_data(user_id)
    if player_data:
        balance = player_data['balance']
        portfolio = player_data['portfolio']
        tnd_price = 10  # Цена TND в Шикоинах

        if balance >= tnd_price:
            balance -= tnd_price
            portfolio["TND"] = portfolio.get("TND", 0) + 1
            update_player_data(user_id, balance, portfolio)
            return jsonify({"message": f"Вы купили 1 TND за {tnd_price} Шикоинов."})
        else:
            return jsonify({"message": "Недостаточно средств для покупки TND."})
    return jsonify({"message": "Ошибка: игрок не найден."})

# Продажа TND
@app.route('/sell_tnd')
def sell_tnd():
    user_id = request.args.get('user_id')
    player_data = get_player_data(user_id)
    if player_data:
        balance = player_data['balance']
        portfolio = player_data['portfolio']
        tnd_price = 10  # Цена TND в Шикоинах
        tnd_amount = portfolio.get("TND", 0)

        if tnd_amount >= 1:
            balance += tnd_price
            portfolio["TND"] = tnd_amount - 1
            update_player_data(user_id, balance, portfolio)
            return jsonify({"message": f"Вы продали 1 TND за {tnd_price} Шикоинов."})
        else:
            return jsonify({"message": "У вас нет TND для продажи."})
    return jsonify({"message": "Ошибка: игрок не найден."})

# Получение данных игрока для Web App
@app.route('/get_player_data')
def get_player_data_web():
    user_id = request.args.get('user_id')
    player_data = get_player_data(user_id)
    if player_data:
        return jsonify(player_data)
    return jsonify({"error": "Игрок не найден."})

# Веб-интерфейс (Web App)
@app.route('/')
def web_app():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>CryptoSnark Trader</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                text-align: center;
                padding: 20px;
            }
            button {
                padding: 10px 20px;
                font-size: 16px;
                margin: 10px;
            }
            .container {
                max-width: 400px;
                margin: 0 auto;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>CryptoSnark Trader</h1>
            <p id="balance">💰 Баланс: Загрузка...</p>
            <p id="tnd">🪙 TND: Загрузка...</p>
            <button onclick="buyTND()">Купить TND</button>
            <button onclick="sellTND()">Продать TND</button>
            <h2>Реферальная система</h2>
            <p id="referralLink">🔗 Реферальная ссылка: Загрузка...</p>
            <p id="referrals">👥 Приглашенные: Загрузка...</p>
        </div>

        <script>
            // Инициализация Web App
            Telegram.WebApp.ready();

            // Загрузка данных игрока
            async function loadPlayerData() {
                const user = Telegram.WebApp.initDataUnsafe.user;
                if (!user) {
                    alert("Ошибка: пользователь не авторизован.");
                    return;
                }

                const response = await fetch(`/get_player_data?user_id=${user.id}`);
                const data = await response.json();

                document.getElementById("balance").textContent = `💰 Баланс: ${data.balance} Шикоинов`;
                document.getElementById("tnd").textContent = `🪙 TND: ${data.portfolio.TND || 0}`;
                document.getElementById("referralLink").textContent = `🔗 Реферальная ссылка: https://t.me/ваш_бот?start=${data.referral_code}`;
                document.getElementById("referrals").textContent = `👥 Приглашенные: ${data.referrals || 0}`;
            }

            // Покупка TND
            async function buyTND() {
                const user = Telegram.WebApp.initDataUnsafe.user;
                const response = await fetch(`/buy_tnd?user_id=${user.id}`);
                const result = await response.json();
                alert(result.message);
                loadPlayerData();  // Обновляем данные
            }

            // Продажа TND
            async function sellTND() {
                const user = Telegram.WebApp.initDataUnsafe.user;
                const response = await fetch(`/sell_tnd?user_id=${user.id}`);
                const result = await response.json();
                alert(result.message);
                loadPlayerData();  // Обновляем данные
            }

            // Загружаем данные при открытии
            loadPlayerData();
        </script>
    </body>
    </html>
    '''

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    username = update.message.from_user.username
    referrer_id = context.args[0] if context.args else None
    register_player(user_id, username, referrer_id)

    keyboard = [
        [InlineKeyboardButton("Открыть игру", web_app=WebAppInfo(url="http://localhost:5000"))]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Добро пожаловать! Нажмите кнопку, чтобы открыть игру:", reply_markup=reply_markup)

# Основная функция
def main():
    init_db()
    application = Application.builder().token("8050714665:AAHCof0RXKlSqcqtoqw1iVNKhch9POiFYsI").build()
    application.add_handler(CommandHandler("start", start))
    application.run_polling()

if __name__ == "__main__":
    # Запуск Flask в отдельном потоке
    threading.Thread(target=app.run, kwargs={"port": 5000}, daemon=True).start()
    
    # Запуск бота
    main()