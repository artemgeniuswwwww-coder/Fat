import telebot
import requests
import os
from flask import Flask, request

# ========== ТОКЕНЫ (ВАШИ) ==========
TOKEN = '8719783774:AAHp4nEoQxqM23xpU8ppmEq9OeiVbpfCljU'
DEEPSEEK_KEY = 'sk-2e34591f3fbd430b8e1d4cc642955fbf'

# ========== НАСТРОЙКА ==========
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ========== ФУНКЦИЯ ОТВЕТА ==========
def ask_deepseek(prompt):
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 500
    }
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"😅 Ошибка: {e}"

# ========== КОМАНДЫ БОТА ==========
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "👋 Привет! Я Смайл! Напиши что-нибудь.")

@bot.message_handler(func=lambda msg: True)
def reply(message):
    try:
        answer = ask_deepseek(message.text)
        bot.reply_to(message, answer)
    except Exception as e:
        bot.reply_to(message, f"😅 Ошибка: {e}")

# ========== ВЕБ-СЕРВЕР (ДЛЯ RENDER) ==========
@app.route('/')
def index():
    return "🤖 Бот Смайл работает!"

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    try:
        bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode('utf-8'))])
        return "OK", 200
    except:
        return "Error", 400

# ========== ЗАПУСК БОТА ==========
import threading
import time

def run_bot():
    while True:
        try:
            bot.remove_webhook()
            bot.polling(none_stop=True, interval=1, timeout=30)
        except Exception as e:
            print(f"Ошибка бота: {e}")
            time.sleep(5)

if __name__ == '__main__':
    # Запускаем бота в фоне
    thread = threading.Thread(target=run_bot)
    thread.daemon = True
    thread.start()
    
    # Запускаем веб-сервер
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)