import telebot
import requests
import json
import os
import time
import threading
from flask import Flask, request

# ========== ТОКЕНЫ ==========
TOKEN = os.getenv('BOT_TOKEN', '8719783774:AAHp4nEoQxqM23xpU8ppmEq9OeiVbpfCljU')
GEMINI_KEY = os.getenv('GEMINI_KEY', 'AQ.Ab8RN6I-YuXgfVn_knf_37z6qVc6k76Th...')  # ВАШ КЛЮЧ

# ========== НАСТРОЙКА ==========
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ФУНКЦИЯ ЗАПРОСА К GEMINI ЧЕРЕЗ REST API
def ask_gemini(prompt):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    data = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            # Извлекаем текст ответа
            text = result.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "😅 Не удалось получить ответ")
            return text
        else:
            return f"❌ Ошибка API: {response.status_code} - {response.text[:200]}"
    except Exception as e:
        return f"😅 Ошибка соединения: {str(e)[:100]}"

# ========== КОМАНДЫ БОТА ==========
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(
        message,
        "👋 Привет! Я **Смайл** — твой ИИ-помощник!\n\n"
        "💬 Просто напиши мне что угодно!",
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['help'])
def help_command(message):
    bot.reply_to(
        message,
        "📖 **Помощь:**\n\n"
        "💬 Напиши текст — я отвечу\n"
        "🔄 /start — приветствие\n"
        "ℹ️ /help — помощь",
        parse_mode='Markdown'
    )

@bot.message_handler(func=lambda msg: True)
def reply_to_all(message):
    try:
        # Отправляем запрос к Gemini
        response_text = ask_gemini(
            f"Ты — Смайл 😊, дружелюбный и весёлый ИИ-помощник. Ответь пользователю на русском языке, кратко и по делу (до 500 символов). Вопрос: {message.text}"
        )
        
        # Отправляем ответ (ограничиваем 1000 символов)
        bot.reply_to(message, response_text[:1000])
    except Exception as e:
        bot.reply_to(message, f"😅 Ошибка: {str(e)[:100]}")

# ========== ВЕБ-СЕРВЕР ДЛЯ RAILWAY ==========
@app.route('/')
def index():
    return "🤖 Бот Смайл работает 24/7!"

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    try:
        bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode('utf-8'))])
        return "OK", 200
    except Exception as e:
        return f"Error: {e}", 400

# ========== ЗАПУСК БОТА В ФОНЕ ==========
def run_bot():
    while True:
        try:
            bot.remove_webhook()
            bot.polling(none_stop=True, interval=1, timeout=30)
        except Exception as e:
            print(f"⚠️ Ошибка бота: {e}")
            time.sleep(5)

# ========== ЗАПУСК ==========
if __name__ == '__main__':
    # Запускаем бота в отдельном потоке
    thread = threading.Thread(target=run_bot)
    thread.daemon = True
    thread.start()
    
    # Запускаем веб-сервер
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)