import telebot
import google.generativeai as genai
import os
import time
import threading
from flask import Flask, request

# ТОКЕНЫ
TOKEN = os.getenv('BOT_TOKEN', '8719783774:AAHp4nEoQxqM23xpU8ppmEq9OeiVbpfCljU')
GEMINI_KEY = os.getenv('GEMINI_KEY', 'AQ.Ab8RN6I-YuXgfVn_knf_37z6qVc6k76Th...')

# НАСТРОЙКА GEMINI (НОВЫЙ СПОСОБ)
genai.configure(api_key=GEMINI_KEY)

# ПРОВЕРКА: используем правильную модель
model = genai.GenerativeModel('gemini-2.0-flash-exp')  # или 'gemini-2.0-flash'

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# КОМАНДЫ БОТА
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "👋 Привет! Я Смайл! Напиши что-нибудь.")

@bot.message_handler(func=lambda msg: True)
def reply(message):
    try:
        response = model.generate_content(f"Ты — Смайл, дружелюбный помощник. Ответь: {message.text}")
        bot.reply_to(message, response.text[:1000])
    except Exception as e:
        bot.reply_to(message, f"😅 Ошибка: {str(e)[:200]}")

# ВЕБ-СЕРВЕР
@app.route('/')
def index():
    return "🤖 Бот Смайл работает!"

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    try:
        bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode('utf-8'))])
        return "OK", 200
    except Exception as e:
        return f"Error: {e}", 400

# ЗАПУСК БОТА В ФОНЕ
def run_bot():
    while True:
        try:
            bot.remove_webhook()
            bot.polling(none_stop=True, interval=1, timeout=30)
        except Exception as e:
            print(f"⚠️ Ошибка бота: {e}")
            time.sleep(5)

if __name__ == '__main__':
    thread = threading.Thread(target=run_bot)
    thread.daemon = True
    thread.start()
    
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)