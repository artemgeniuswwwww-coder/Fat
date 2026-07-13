import telebot
import requests
import os
import time
import threading
from flask import Flask, request
from googlesearch import search

# ========== ТОКЕН ТЕЛЕГРАМ ==========
TOKEN = '8719783774:AAHp4nEoQxqM23xpU8ppmEq9OeiVbpfCljU'
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ========== 1. БЕСПЛАТНЫЙ GPT ЧЕРЕЗ ПРОКСИ ==========
def ask_gpt(prompt):
    """Отправляет запрос к GPT через бесплатный прокси"""
    url = "https://api.pawan.krd/v1/chat/completions"
    
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": "Ты — Смайл 😊, дружелюбный ИИ-помощник. Отвечай кратко, с эмодзи, на русском языке."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 500,
        "temperature": 0.7
    }
    
    try:
        response = requests.post(url, json=data, timeout=30)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            return f"❌ Ошибка API: {response.status_code}"
    except requests.exceptions.Timeout:
        return "⏰ Превышено время ожидания. Попробуй ещё раз."
    except Exception as e:
        return f"😅 Ошибка: {str(e)[:100]}"

# ========== 2. ГЕНЕРАЦИЯ КАРТИНОК ==========
def generate_image(prompt):
    """Генерирует картинку через Pollinations.ai"""
    try:
        url = f"https://image.pollinations.ai/prompt/{prompt.replace(' ', '%20')}?width=512&height=512"
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            with open('image.jpg', 'wb') as f:
                f.write(response.content)
            return 'image.jpg'
        return None
    except Exception as e:
        print(f"Ошибка генерации картинки: {e}")
        return None

# ========== 3. ПОИСК В ИНТЕРНЕТЕ ==========
def search_internet(query):
    """Ищет информацию в интернете через Google"""
    try:
        results = []
        for url in search(query, num_results=3):
            results.append(f"🔗 {url}")
        return "\n".join(results) if results else "❌ Ничего не найдено"
    except Exception as e:
        return f"😅 Ошибка поиска: {e}"

# ========== 4. КОМАНДЫ БОТА ==========
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(
        message,
        "👋 Привет! Я **Смайл** 🤖\n\n"
        "🎨 **Нарисуй** [описание] – создам картинку\n"
        "🔍 **Найди** [запрос] – поищу в интернете\n"
        "💬 **Просто напиши** вопрос – я отвечу через GPT\n\n"
        "Примеры:\n"
        "• Нарисуй кота в космосе\n"
        "• Найди новости про ИИ\n"
        "• Как работает квантовый компьютер?",
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['help'])
def help_command(message):
    bot.reply_to(
        message,
        "📖 **Помощь:**\n\n"
        "🎨 Нарисуй [текст] – генерация картинки\n"
        "🔍 Найди [текст] – поиск в интернете\n"
        "💬 Любой текст – ответ через GPT\n\n"
        "🔄 /start – приветствие\n"
        "ℹ️ /help – помощь",
        parse_mode='Markdown'
    )

@bot.message_handler(func=lambda msg: True)
def handle_message(message):
    text = message.text
    text_lower = text.lower()

    # === ГЕНЕРАЦИЯ КАРТИНКИ ===
    if text_lower.startswith('нарисуй') or text_lower.startswith('сгенерируй') or text_lower.startswith('изобрази'):
        prompt = text[7:].strip()
        if not prompt:
            bot.reply_to(message, "📝 Напиши, что нарисовать! Например: *Нарисуй закат на море*", parse_mode='Markdown')
            return
        
        status = bot.reply_to(message, f"🎨 Рисую: *{prompt[:50]}*...⏳", parse_mode='Markdown')
        image_path = generate_image(prompt)
        
        if image_path:
            with open(image_path, 'rb') as f:
                bot.send_photo(message.chat.id, f, caption=f"🖼️ **Вот что получилось:**\n{prompt}")
            os.remove(image_path)
            bot.delete_message(message.chat.id, status.id)
        else:
            bot.edit_message_text("😅 Не удалось сгенерировать картинку. Попробуй другой запрос.", message.chat.id, status.id)
        return

    # === ПОИСК В ИНТЕРНЕТЕ ===
    if 'найди' in text_lower or 'поищи' in text_lower or 'узнай' in text_lower:
        # Убираем команды из текста
        query = text
        for cmd in ['найди', 'поищи', 'узнай']:
            query = query.replace(cmd, '')
        query = query.strip()
        
        if not query:
            bot.reply_to(message, "📝 Напиши, что именно найти! Например: *Найди погоду в Москве*", parse_mode='Markdown')
            return
        
        status = bot.reply_to(message, f"🔍 Ищу: *{query}*...⏳", parse_mode='Markdown')
        search_results = search_internet(query)
        
        # Отправляем результаты поиска + ответ GPT
        if "Ошибка" not in search_results:
            response = ask_gpt(f"Вопрос пользователя: {query}\n\nИнформация из интернета:\n{search_results}\n\nОтветь на вопрос, используя эту информацию. Будь кратким и точным (до 500 символов). Укажи источники.")
        else:
            response = ask_gpt(f"Вопрос пользователя: {query}\n\nНе удалось найти информацию в интернете. Ответь на вопрос своими знаниями.")
        
        bot.edit_message_text(response, message.chat.id, status.id, parse_mode='Markdown')
        return

    # === ОБЫЧНЫЙ ОТВЕТ ===
    status = bot.reply_to(message, "🤔 Думаю...⏳")
    response = ask_gpt(text)
    bot.edit_message_text(response, message.chat.id, status.id, parse_mode='Markdown')

# ========== 5. ВЕБ-СЕРВЕР ДЛЯ RENDER ==========
@app.route('/')
def index():
    return "🤖 Бот Смайл работает 24/7!"

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    try:
        update = telebot.types.Update.de_json(request.stream.read().decode('utf-8'))
        bot.process_new_updates([update])
        return "OK", 200
    except Exception as e:
        return f"Error: {e}", 400

# ========== 6. ЗАПУСК БОТА В ФОНЕ ==========
def run_bot():
    while True:
        try:
            bot.remove_webhook()
            bot.polling(none_stop=True, interval=1, timeout=30)
        except Exception as e:
            print(f"⚠️ Ошибка бота: {e}")
            time.sleep(10)

# ========== 7. ЗАПУСК ==========
if __name__ == '__main__':
    # Запускаем бота в отдельном потоке
    thread = threading.Thread(target=run_bot)
    thread.daemon = True
    thread.start()
    print("🚀 Бот Смайл запущен!")
    
    # Запускаем веб-сервер
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)