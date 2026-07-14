import telebot
import requests
import os
import time
from flask import Flask, request
from googlesearch import search

TOKEN = '8926765429:AAEtCcaPz0MaolgHBv84MhOUOOH6yWYjlqk'
YANDEX_KEY = 'AQVN2jkFEhOY-aSEW3DbBaKjh6YcIv_ynkC5x87K'

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ==============================================
# YANDEX GPT
# ==============================================
def ask_yandex(prompt):
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        "Authorization": f"Api-Key {YANDEX_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "modelUri": "gpt://latest/yandexgpt",
        "completionOptions": {"temperature": 0.8, "maxTokens": 800},
        "messages": [{"role": "user", "text": f"Ты — Смайл 😊, дружелюбный помощник. Отвечай кратко, с эмодзи. Вопрос: {prompt}"}]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        if response.status_code == 200:
            return response.json()["result"]["alternatives"][0]["message"]["text"]
        return f"❌ Ошибка Yandex: {response.status_code}"
    except Exception as e:
        return f"😅 Ошибка: {str(e)[:100]}"

# ==============================================
# ГЕНЕРАЦИЯ КАРТИНОК
# ==============================================
def generate_image(prompt):
    try:
        url = f"https://image.pollinations.ai/prompt/{prompt.replace(' ', '%20')}?width=512&height=512"
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            with open('image.jpg', 'wb') as f:
                f.write(response.content)
            return 'image.jpg'
        return None
    except:
        return None

# ==============================================
# ПОИСК В ИНТЕРНЕТЕ
# ==============================================
def search_internet(query):
    try:
        results = []
        for url in search(query, num_results=3):
            results.append(f"🔗 {url}")
        return "\n".join(results) if results else "❌ Ничего не найдено"
    except Exception as e:
        return f"😅 Ошибка поиска: {e}"

# ==============================================
# КОМАНДЫ БОТА
# ==============================================
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(
        message,
        "👋 Привет! Я **Смайл** 🤖\n\n"
        "🎨 **Нарисуй** [описание] – картинка\n"
        "🔍 **Найди** [запрос] – поиск в интернете\n"
        "💬 **Просто напиши** вопрос",
        parse_mode='Markdown'
    )

@bot.message_handler(func=lambda msg: True)
def handle_message(message):
    text = message.text
    text_lower = text.lower()

    # === КАРТИНКА ===
    if text_lower.startswith('нарисуй') or text_lower.startswith('сгенерируй'):
        prompt = text[7:].strip()
        if not prompt:
            bot.reply_to(message, "📝 Что нарисовать?")
            return
        
        status = bot.reply_to(message, f"🎨 Рисую...")
        image_path = generate_image(prompt)
        
        if image_path:
            with open(image_path, 'rb') as f:
                bot.send_photo(message.chat.id, f, caption=f"🖼️ {prompt}")
            os.remove(image_path)
            bot.delete_message(message.chat.id, status.id)
        else:
            bot.edit_message_text("😅 Не удалось создать картинку.", message.chat.id, status.id)
        return

    # === ПОИСК ===
    if 'найди' in text_lower or 'поищи' in text_lower:
        query = text.replace('найди', '').replace('поищи', '').strip()
        if not query:
            bot.reply_to(message, "📝 Что найти?")
            return
        
        status = bot.reply_to(message, f"🔍 Ищу...")
        search_results = search_internet(query)
        
        if "Ошибка" not in search_results:
            response = ask_yandex(f"Вопрос: {query}\nИнформация: {search_results}\nОтветь кратко.")
        else:
            response = ask_yandex(f"Вопрос: {query}")
        
        bot.edit_message_text(response, message.chat.id, status.id, parse_mode='Markdown')
        return

    # === ОБЫЧНЫЙ ОТВЕТ ===
    status = bot.reply_to(message, "🤔 Думаю...")
    response = ask_yandex(text)
    bot.edit_message_text(response, message.chat.id, status.id, parse_mode='Markdown')

# ==============================================
# WEBHOOK (ВМЕСТО POLLING)
# ==============================================
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    try:
        update = telebot.types.Update.de_json(request.stream.read().decode('utf-8'))
        bot.process_new_updates([update])
        return "OK", 200
    except Exception as e:
        return f"Error: {e}", 400

@app.route('/')
def index():
    return "🤖 Бот Смайл работает!"

# ==============================================
# ЗАПУСК
# ==============================================
if __name__ == '__main__':
    # Удаляем старый вебхук
    bot.remove_webhook()
    
    # Ставим новый вебхук
    webhook_url = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'localhost')}/{TOKEN}"
    bot.set_webhook(url=webhook_url)
    print(f"✅ Вебхук установлен: {webhook_url}")
    
    # Запускаем веб-сервер
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)