import telebot
import requests
import os
import re
import random
import time
from flask import Flask, request

TOKEN = '8926765429:AAEtCcaPz0MaolgHBv84MhOUOOH6yWYjlqk'
MISTRAL_KEY = 'zgWg7QFAdA9NMlPjL04lwruEj1NS1NvP'

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ==============================================
# 1. ИСТОРИЯ ДИАЛОГА (ХРАНИТСЯ ВСЯ)
# ==============================================
user_history = {}

def get_history(user_id):
    if user_id not in user_history:
        user_history[user_id] = []
    return user_history[user_id]

def add_to_history(user_id, role, text):
    history = get_history(user_id)
    history.append({"role": role, "content": text})

def clear_history(user_id):
    if user_id in user_history:
        user_history[user_id] = []

def get_full_context(user_id):
    history = get_history(user_id)
    context = ""
    for msg in history:
        if msg["role"] == "user":
            context += f"Пользователь: {msg['content']}\n"
        else:
            context += f"Смайл: {msg['content']}\n"
    return context

# ==============================================
# 2. MISTRAL (С ПОЛНОЙ ИСТОРИЕЙ)
# ==============================================
def ask_mistral(user_id, prompt):
    context = get_full_context(user_id)
    
    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {MISTRAL_KEY}",
        "Content-Type": "application/json"
    }
    
    full_prompt = f"""Ты — Смайл 😊, умный и дружелюбный помощник. 
    Вот полная история нашего диалога:
    {context}
    
    Пользователь спросил: {prompt}
    
    Отвечай кратко, по делу, на русском языке. Если вопрос уточняющий — задай его."""
    
    data = {
        "model": "mistral-small-latest",
        "messages": [{"role": "user", "content": full_prompt}],
        "max_tokens": 500,
        "temperature": 0.7
    }
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        return f"❌ Ошибка: {response.status_code}"
    except Exception as e:
        return f"😅 Ошибка: {str(e)[:100]}"

# ==============================================
# 3. РЕАЛИСТИЧНЫЕ КАРТИНКИ
# ==============================================
def generate_image(prompt):
    clean_prompt = re.sub(r'^(нарисуй|сгенерируй|изобрази|покажи)\s+', '', prompt, flags=re.IGNORECASE)
    clean_prompt = clean_prompt.strip()
    if not clean_prompt:
        clean_prompt = "красивый пейзаж"
    
    styles = [
        "photorealistic, 8k, highly detailed",
        "realistic, cinematic lighting, sharp focus",
        "hyperrealistic, professional photography, detailed texture",
        "realistic, natural lighting, high resolution"
    ]
    style = random.choice(styles)
    
    full_prompt = f"{clean_prompt}, {style}"
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
# 4. КОМАНДЫ
# ==============================================
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "пользователь"
    clear_history(user_id)
    bot.reply_to(
        message,
        f"👋 Привет, **{user_name}**! Я Смайл 😊\n\n"
        "🎨 **Нарисуй** [описание] — картинка\n"
        "💬 **Просто напиши** вопрос — отвечу с учётом истории\n"
        "🔄 **/newchat** — начать новый диалог (очистить историю)\n"
        "🧹 **/clear** — очистить историю\n"
        "ℹ️ **/info** — обо мне",
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['newchat'])
def new_chat(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "пользователь"
    clear_history(user_id)
    bot.reply_to(
        message,
        f"🔄 **{user_name}**, начал новый диалог! История очищена. 😊\n\n"
        "Теперь я не помню предыдущие сообщения. Начинай!",
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['clear'])
def clear_chat(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "пользователь"
    clear_history(user_id)
    bot.reply_to(
        message,
        f"🧹 **{user_name}**, история диалога очищена! 😊",
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['info'])
def info(message):
    bot.reply_to(
        message,
        "🤖 **Смайл** — ИИ-помощник\n\n"
        "🧠 **Mistral** — основной ИИ\n"
        "🎨 **Pollinations.ai** — генерация картинок\n"
        "📝 **Бесконечная история** — помню всё\n"
        "🔄 **/newchat** — новый диалог\n"
        "🧹 **/clear** — очистить историю\n"
        "⚡ Бесплатно и безлимитно",
        parse_mode='Markdown'
    )

# ==============================================
# 5. ОСНОВНАЯ ОБРАБОТКА ТЕКСТА
# ==============================================
@bot.message_handler(func=lambda msg: True)
def handle_message(message):
    user_id = message.from_user.id
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
        
        add_to_history(user_id, "user", f"Попросил нарисовать: {prompt}")
        status = bot.reply_to(message, f"🎨 Создаю: *{prompt}*...", parse_mode='Markdown')
        image_path, clean_prompt = generate_image(prompt)
        
        if image_path:
            with open(image_path, 'rb') as f:
                bot.send_photo(message.chat.id, f, caption=f"🎨 *{clean_prompt.capitalize()}* готов!", parse_mode='Markdown')
            os.remove(image_path)
            add_to_history(user_id, "assistant", f"Отправил картинку {clean_prompt}")
            bot.delete_message(message.chat.id, status.id)
        else:
            bot.edit_message_text("😅 Не удалось создать картинку.", message.chat.id, status.id)
        return

    # === ОБЫЧНЫЙ ОТВЕТ ===
    add_to_history(user_id, "user", text)
    status = bot.reply_to(message, f"🤔 Размышляю, **{user_name}**...")
    response = ask_mistral(user_id, text)
    add_to_history(user_id, "assistant", response)
    bot.edit_message_text(response, message.chat.id, status.id, parse_mode='Markdown')

# ==============================================
# 6. WEBHOOK
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
# 7. ЗАПУСК
# ==============================================
if __name__ == '__main__':
    bot.remove_webhook()
    webhook_url = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'localhost')}/{TOKEN}"
    bot.set_webhook(url=webhook_url)
    print(f"✅ Вебхук установлен: {webhook_url}")
    
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)