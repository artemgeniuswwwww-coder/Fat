import telebot
import requests
import os
import time
import threading
from flask import Flask, request
import json

# ========== ТОКЕНЫ ==========
TOKEN = '8719783774:AAHp4nEoQxqM23xpU8ppmEq9OeiVbpfCljU'
DEEPSEEK_KEY = 'sk-2e34591f3fbd430b8e1d4cc642955fbf'  # ВАШ КЛЮЧ

# ========== НАСТРОЙКА ==========
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ========== ФУНКЦИЯ ЗАПРОСА К DEEPSEEK (С ПРОВЕРКОЙ) ==========
def ask_deepseek(prompt):
    url = "https://api.deepseek.com/v1/chat/completions"
    
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "Ты — Смайл, дружелюбный помощник. Отвечай кратко."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 500,
        "temperature": 0.7
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        
        # ПРОВЕРЯЕМ СТАТУС ОТВЕТА
        if response.status_code != 200:
            error_detail = response.text
            return f"❌ Ошибка API ({response.status_code}): {error_detail[:200]}"
        
        # ПРОВЕРЯЕМ СТРУКТУРУ ОТВЕТА
        result = response.json()
        if 'choices' not in result or len(result['choices']) == 0:
            return f"⚠️ Странный ответ от API: {json.dumps(result, ensure_ascii=False)[:200]}"
        
        # ВСЁ ХОРОШО, ИЗВЛЕКАЕМ ТЕКСТ
        return result["choices"][0]["message"]["content"]
        
    except requests.exceptions.Timeout:
        return "⏰ Таймаут. Сервер DeepSeek не отвечает."
    except Exception as e:
        return f"😅 Ошибка соединения: {str(e)[:100]}"

# ========== КОМАНДЫ БОТА ==========
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(
        message,
        "👋 Привет! Я **Смайл**!\n\n"
        "💬 Напиши что угодно, я отвечу через DeepSeek.\n"
        "🔄 /start — перезапустить",
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['test'])
def test_deepseek(message):
    """Тестовая команда для проверки API"""
    status = bot.reply_to(message, "🔍 Проверяю соединение с DeepSeek...")
    response = ask_deepseek("Ответь 'Привет' одним словом.")
    bot.edit_message_text(f"📊 **Результат теста:**\n\n{response}", message.chat.id, status.id, parse_mode='Markdown')

@bot.message_handler(func=lambda msg: True)
def reply_to_all(message):
    # Показываем статус "печатает"
    bot.send_chat_action(message.chat.id, 'typing')
    
    try:
        answer = ask_deepseek(message.text)
        bot.reply_to(message, answer)
    except Exception as e:
        bot.reply_to(message, f"😅 Критическая ошибка: {e}")

# ========== ВЕБ-СЕРВЕР ==========
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

# ========== ЗАПУСК БОТА В ФОНЕ ==========
def run_bot():
    while True:
        try:
            bot.remove_webhook()
            bot.polling(none_stop=True, interval=1, timeout=30)
        except Exception as e:
            print(f"⚠️ Ошибка бота: {e}")
            time.sleep(10)

# ========== ЗАПУСК ==========
if __name__ == '__main__':
    thread = threading.Thread(target=run_bot)
    thread.daemon = True
    thread.start()
    print("🚀 Бот Смайл запущен!")
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)