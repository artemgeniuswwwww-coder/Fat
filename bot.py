import telebot
import google.generativeai as genai
import time
import threading
from flask import Flask, request

# ========== ТОКЕНЫ (ВАШИ) ==========
TOKEN = '8719783774:AAHp4nEoQxqM23xpU8ppmEq9OeiVbpfCljU'
GEMINI_KEY = 'AQ.Ab8RN6JJzEAFFt8IvzQ2ou_z1ADHRXte2hF3cJPzObXHYjhYwg'

# ========== НАСТРОЙКА GEMINI ==========
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

# ========== НАСТРОЙКА БОТА ==========
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ========== КОМАНДЫ БОТА ==========
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(
        message,
        "👋 Привет! Я **Смайл** — твой ИИ-друг!\n\n"
        "💬 Просто напиши мне что угодно!",
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['help'])
def help_command(message):
    bot.reply_to(
        message,
        "📖 Просто напиши текст — я отвечу!\n"
        "🔄 /start — приветствие\n"
        "ℹ️ /help — помощь",
        parse_mode='Markdown'
    )

@bot.message_handler(func=lambda msg: True)
def reply_to_all(message):
    try:
        # Отправляем запрос в Gemini
        response = model.generate_content(
            f"Ты — Смайл 😊, дружелюбный помощник. Ответь на вопрос: {message.text}"
        )
        # Отправляем ответ (ограничиваем 1000 символов)
        bot.reply_to(message, response.text[:1000])
    except Exception as e:
        bot.reply_to(message, f"😅 Ошибка: {str(e)[:100]}")

# ========== ВЕБ-СЕРВЕР ДЛЯ RENDER ==========
@app.route('/')
def index():
    return "🤖 Бот Смайл работает!"

@app.route('/' + TOKEN, methods=['POST'])
def webhook():
    try:
        bot.process_new_updates([telebot.types.Update.de_json(request.stream.read().decode('utf-8'))])
        return "OK", 200
    except:
        return "Error", 400

# ========== ЗАПУСК ==========
if __name__ == '__main__':
    # Запускаем бота в фоновом режиме
    def run_bot():
        try:
            bot.remove_webhook()
            bot.polling(none_stop=True, interval=1, timeout=30)
        except Exception as e:
            print(f"Ошибка бота: {e}")
    
    thread = threading.Thread(target=run_bot)
    thread.daemon = True
    thread.start()
    
    # Запускаем веб-сервер
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)