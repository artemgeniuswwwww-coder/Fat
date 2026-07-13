import telebot
import google.generativeai as genai

# ТОКЕНЫ
TOKEN = '8719783774:AAHp4nEoQxqM23xpU8ppmEq9OeiVbpfCljU'
GEMINI_KEY = 'AQ.Ab8RN6JJzEAFFt8IvzQ2ou_z1ADHRXte2hF3cJPzObXHYjhYwg'  # ЗАМЕНИТЕ НА РЕАЛЬНЫЙ

# НАСТРОЙКА
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "👋 Привет! Я Смайл! Напиши что-нибудь.")

@bot.message_handler(func=lambda msg: True)
def reply(message):
    try:
        response = model.generate_content(f"Ответь кратко: {message.text}")
        bot.reply_to(message, response.text[:500])
    except Exception as e:
        bot.reply_to(message, f"Ошибка: {e}")

print("Бот запущен!")
bot.polling()