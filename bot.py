import telebot
import google.generativeai as genai
import os
import time
import threading
from flask import Flask, request

TOKEN = '8719783774:AAHp4nEoQxqM23xpU8ppmEq9OeiVbpfCljU'
GEMINI_KEY = 'AQ.Ab8RN6JJzEAFFt8IvzQ2ou_z1ADHRXte2hF3cJPzObXHYjhYwg'

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "👋 Привет! Я Смайл!")

@bot.message_handler(func=lambda msg: True)
def reply(message):
    try:
        response = model.generate_content(f"Ты — Смайл, дружелюбный помощник. Ответь: {message.text}")
        bot.reply_to(message, response.text[:1000])
    except Exception as e:
        bot.reply_to(message, f"Ошибка: {e}")

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

def run_bot():
    while True:
        try:
            bot.remove_webhook()
            bot.polling(none_stop=True, interval=1, timeout=30)
        except Exception as e:
            print(f"Ошибка: {e}")
            time.sleep(5)

if __name__ == '__main__':
    thread = threading.Thread(target=run_bot)
    thread.daemon = True
    thread.start()
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)