import telebot
import google.generativeai as genai
import os
import time
import threading
from flask import Flask, request

# ТОКЕНЫ
TOKEN = os.getenv('BOT_TOKEN')
GEMINI_KEY = os.getenv('GEMINI_KEY')

if not TOKEN or not GEMINI_KEY:
    print("❌ ОШИБКА: Токены не найдены!")
    exit(1)

# НАСТРОЙКА
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

print(f"✅ Бот запущен!")

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
        bot.reply_to(message, f"😅 Ошибка: {e}")

# ВЕБ-СЕРВЕР ДЛЯ RENDER
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

# ЗАПУСК БОТА В ФОНЕ
def run_bot():
    while True:
        try:
            bot.remove_webhook()
            bot.polling(none_stop=True, interval=1, timeout=30)
        except Exception as e:
            print(f"⚠️ Ошибка бота: {e}")
            time.sleep(5)

# ЗАПУСК
if __name__ == '__main__':
    # Запускаем бота в отдельном потоке
    thread = threading.Thread(target=run_bot)
    thread.daemon = True
    thread.start()
    
    # Запускаем веб-сервер
    port = int(os.getenv('PORT', 10000))
    app.run(host='0.0.0.0', port=port)