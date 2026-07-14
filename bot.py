import telebot
import requests
import os
import re
import random
import time
from flask import Flask, request
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

TOKEN = '8926765429:AAEtCcaPz0MaolgHBv84MhOUOOH6yWYjlqk'
MISTRAL_KEY = 'zgWg7QFAdA9NMlPjL04lwruEj1NS1NvP'

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ==============================================
# 1. MISTRAL
# ==============================================
def ask_mistral(prompt):
    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {MISTRAL_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "mistral-small-latest",
        "messages": [
            {"role": "system", "content": "Ты — Смайл 😊, умный помощник. Отвечай кратко, по делу, на русском."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 400,
        "temperature": 0.7
    }
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        return f"❌ Ошибка Mistral: {response.status_code}"
    except Exception as e:
        return f"😅 Ошибка: {str(e)[:100]}"

# ==============================================
# 2. ГЕНЕРАЦИЯ КАРТИНОК
# ==============================================
def generate_image(prompt):
    clean_prompt = re.sub(r'^(нарисуй|сгенерируй|изобрази|покажи)\s+', '', prompt, flags=re.IGNORECASE)
    clean_prompt = clean_prompt.strip()
    if not clean_prompt:
        clean_prompt = "красивый пейзаж"
    styles = ["реалистичный", "акварельный", "фэнтези", "киберпанк"]
    style = random.choice(styles)
    full_prompt = f"{clean_prompt}, {style}, высокое качество"
    seed = random.randint(1, 999999)
    url = f"https://image.pollinations.ai/prompt/{full_prompt.replace(' ', '%20')}?width=1024&height=1024&seed={seed}"
    try:
        response = requests.get(url, timeout=60)
        if response.status_code == 200:
            with open('image.jpg', 'wb') as f:
                f.write(response.content)
            return 'image.jpg', clean_prompt
        return None, None
    except:
        return None, None

# ==============================================
# 3. КОМАНДЫ
# ==============================================
@bot.message_handler(commands=['start'])
def start(message):
    user_name = message.from_user.first_name or "пользователь"
    bot.reply_to(
        message,
        f"👋 Привет, **{user_name}**! Я Смайл 😊\n\n"
        "🎨 **Нарисуй** [описание] — картинка\n"
        "🖼️ **Отправь фото** — анализ (бета)\n"
        "🎬 **Отправь видео** — анализ (бета)\n"
        "ℹ️ **/info** — обо мне",
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['info'])
def info(message):
    bot.reply_to(
        message,
        "🤖 **Смайл** — ИИ-помощник\n\n"
        "🧠 **Mistral** — основной ИИ\n"
        "🎨 **Pollinations.ai** — генерация картинок\n"
        "⚡ Бесплатно и безлимитно",
        parse_mode='Markdown'
    )

# ==============================================
# 4. ОБРАБОТКА ФОТО (ЗАГЛУШКА)
# ==============================================
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    bot.reply_to(message, "🖼️ Фото получено! Анализ пока в разработке (бета)")

# ==============================================
# 5. ОБРАБОТКА ВИДЕО (ЗАГЛУШКА)
# ==============================================
@bot.message_handler(content_types=['video'])
def handle_video(message):
    bot.reply_to(message, "🎬 Видео получено! Анализ пока в разработке (бета)")

# ==============================================
# 6. ОСНОВНАЯ ОБРАБОТКА ТЕКСТА
# ==============================================
@bot.message_handler(func=lambda msg: True)
def handle_message(message):
    text = message.text
    text_lower = text.lower()
    user_name = message.from_user.first_name or "пользователь"

    # === КАРТИНКА ===
    draw_keywords = ['нарисуй', 'сгенерируй', 'изобрази', 'покажи']
    is_draw = any(text_lower.startswith(kw) for kw in draw_keywords)
    
    if is_draw:
        prompt = text
        for kw in draw_keywords:
            prompt = re.sub(r'^' + kw + r'\s+', '', prompt, flags=re.IGNORECASE)
        prompt = prompt.strip()
        
        if not prompt:
            bot.reply_to(message, f"📝 **{user_name}**, уточните, что нарисовать.", parse_mode='Markdown')
            return
        
        status = bot.reply_to(message, f"🎨 Создаю: *{prompt}*...", parse_mode='Markdown')
        image_path, clean_prompt = generate_image(prompt)
        
        if image_path:
            with open(image_path, 'rb') as f:
                bot.send_photo(message.chat.id, f, caption=f"🎨 *{clean_prompt.capitalize()}* готов!", parse_mode='Markdown')
            os.remove(image_path)
            bot.delete_message(message.chat.id, status.id)
        else:
            bot.edit_message_text("😅 Не удалось создать картинку.", message.chat.id, status.id)
        return

    # === ОБЫЧНЫЙ ОТВЕТ ===
    status = bot.reply_to(message, f"🤔 Размышляю, **{user_name}**...")
    response = ask_mistral(text)
    bot.edit_message_text(response, message.chat.id, status.id, parse_mode='Markdown')

# ==============================================
# 7. WEBHOOK
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
# 8. ЗАПУСК
# ==============================================
if __name__ == '__main__':
    bot.remove_webhook()
    webhook_url = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'localhost')}/{TOKEN}"
    bot.set_webhook(url=webhook_url)
    print(f"✅ Вебхук установлен: {webhook_url}")
    
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)