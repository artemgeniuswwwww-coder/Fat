import telebot
import requests
import os
from flask import Flask, request
from googlesearch import search

TOKEN = '8719783774:AAHp4nEoQxqM23xpU8ppmEq9OeiVbpfCljU'
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ====== 1. БЕСПЛАТНЫЙ ChatGPT ======
def ask_free_ai(prompt):
    url = "https://api.pawan.krd/v1/chat/completions"
    
    headers = {
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 500
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        return f"❌ Ошибка {response.status_code}"
    except:
        return "😅 Сервер временно недоступен"

# ====== 2. ГЕНЕРАЦИЯ КАРТИНОК ======
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

# ====== 3. ПОИСК В ИНТЕРНЕТЕ ======
def search_internet(query):
    try:
        results = []
        for url in search(query, num_results=3):
            results.append(f"🔗 {url}")
        return "\n".join(results) if results else "❌ Ничего не найдено"
    except:
        return "😅 Ошибка поиска"

# ====== 4. КОМАНДЫ БОТА ======
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(
        message,
        "👋 Привет! Я **Смайл** 🤖\n\n"
        "🎨 **Нарисуй** [описание] – создам картинку\n"
        "🔍 **Найди** [запрос] – поищу в интернете\n"
        "💬 **Просто напиши** вопрос – я отвечу",
        parse_mode='Markdown'
    )

@bot.message_handler(func=lambda msg: True)
def handle_message(message):
    text = message.text
    text_lower = text.lower()

    # Генерация картинки
    if text_lower.startswith('нарисуй') or text_lower.startswith('сгенерируй'):
        prompt = text[7:].strip()
        status = bot.reply_to(message, f"🎨 Рисую: *{prompt[:50]}*...", parse_mode='Markdown')
        image_path = generate_image(prompt)
        if image_path:
            with open(image_path, 'rb') as f:
                bot.send_photo(message.chat.id, f, caption=f"🖼️ {prompt}")
            os.remove(image_path)
            bot.delete_message(message.chat.id, status.id)
        else:
            bot.edit_message_text("😅 Не удалось сгенерировать картинку.", message.chat.id, status.id)
        return

    # Поиск в интернете
    if 'найди' in text_lower or 'поищи' in text_lower:
        query = text.replace('найди', '').replace('поищи', '').strip()
        if not query:
            bot.reply_to(message, "📝 Напиши, что именно найти!")
            return
        status = bot.reply_to(message, f"🔍 Ищу: *{query}*...", parse_mode='Markdown')
        search_results = search_internet(query)
        response = ask_free_ai(f"Вопрос: {query}\nИнформация: {search_results}\nОтветь кратко.")
        bot.edit_message_text(response, message.chat.id, status.id, parse_mode='Markdown')
        return

    # Обычный ответ
    status = bot.reply_to(message, "🤔 Думаю...")
    response = ask_free_ai(text)
    bot.edit_message_text(response, message.chat.id, status.id, parse_mode='Markdown')

# ====== 5. ВЕБХУК (ВМЕСТО POLLING) ======
@app.route('/')
def index():
    return "🤖 Бот Смайл работает!"

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    try:
        update = telebot.types.Update.de_json(request.stream.read().decode('utf-8'))
        bot.process_new_updates([update])
        return "OK", 200
    except Exception as e:
        return f"Error: {e}", 400

# ====== 6. ЗАПУСК ======
if __name__ == '__main__':
    # Удаляем старый вебхук и ставим новый
    bot.remove_webhook()
    webhook_url = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'localhost')}/{TOKEN}"
    bot.set_webhook(url=webhook_url)
    print(f"✅ Вебхук установлен: {webhook_url}")
    
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)