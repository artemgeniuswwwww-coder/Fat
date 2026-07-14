import telebot
import requests
import os
import re
import random
import time
from flask import Flask, request
from duckduckgo_search import DDGS

TOKEN = '8926765429:AAEtCcaPz0MaolgHBv84MhOUOOH6yWYjlqk'
MISTRAL_KEY = 'zgWg7QFAdA9NMlPjL04lwruEj1NS1NvP'

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ==============================================
# 1. ИСТОРИЯ ДИАЛОГА
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
    for msg in history[-10:]:
        if msg["role"] == "user":
            context += f"Пользователь: {msg['content']}\n"
        else:
            context += f"Смайл: {msg['content']}\n"
    return context

# ==============================================
# 2. ШУТКИ
# ==============================================
JOKES = [
    "Почему программисты не любят природу? — Слишком много багов. 🐛",
    "Как назвать кота, который умеет программировать? — Котлин. 🐱💻",
    "Что сказал один алгоритм другому? — Я тебя отсортирую! 😂",
    "Сколько нужно программистов, чтобы заменить лампочку? — Ни одного, это аппаратная проблема. 💡",
    "Что такое идеальный код? — Тот, который никто не трогал. 😏",
    "Почему программисты путают Хэллоуин и Рождество? — Потому что 31 окт = 25 дек. 🎃🎄",
    "Что такое 'баг' в программировании? — Это запланированная фича, которая работает не так, как задумано. 🪲"
]

# ==============================================
# 3. MISTRAL (5-6 ПРЕДЛОЖЕНИЙ, БЕЗ ФАКТОВ)
# ==============================================
def ask_mistral(prompt):
    url = "https://api.mistral.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {MISTRAL_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "mistral-small-latest",
        "messages": [{"role": "user", "content": f"{prompt} (Отвечай на 5-6 предложений. Будь дружелюбным, живым, с лёгким юмором.)"}],
        "max_tokens": 500,
        "temperature": 0.9
    }
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        return f"❌ Ошибка Mistral: {response.status_code}"
    except Exception as e:
        return f"😅 Ошибка: {e}"

# ==============================================
# 4. ГЕНЕРАЦИЯ КАРТИНОК
# ==============================================
def generate_image(prompt):
    clean_prompt = re.sub(r'^(нарисуй|сгенерируй|изобрази|покажи)\s+', '', prompt, flags=re.IGNORECASE)
    clean_prompt = clean_prompt.strip()
    if not clean_prompt:
        clean_prompt = "красивый пейзаж"
    styles = ["photorealistic, 8k, highly detailed", "cinematic lighting, sharp focus"]
    style = random.choice(styles)
    seed = random.randint(1, 999999)
    url = f"https://image.pollinations.ai/prompt/{clean_prompt.replace(' ', '%20')}, {style}?width=1024&height=1024&seed={seed}"
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
# 5. ПОИСК В ИНТЕРНЕТЕ
# ==============================================
def search_internet(query):
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5, region='ru-ru'))
            if not results:
                results = list(ddgs.text(query, max_results=5))
            if not results:
                return None
            answer = "🔍 **Результаты поиска:**\n\n"
            for i, r in enumerate(results, 1):
                title = r.get('title', 'Без заголовка')
                body = r.get('body', '')
                href = r.get('href', '')
                answer += f"{i}. **{title}**\n{body}\n[Источник]({href})\n\n"
            return answer
    except:
        return None

# ==============================================
# 6. ОТПРАВКА ДЛИННЫХ СООБЩЕНИЙ
# ==============================================
def send_long_message(chat_id, text):
    if len(text) <= 4096:
        bot.send_message(chat_id, text, parse_mode='Markdown')
    else:
        for i in range(0, len(text), 4096):
            bot.send_message(chat_id, text[i:i+4096], parse_mode='Markdown')

# ==============================================
# 7. КОМАНДЫ
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
        "🔍 **Найди** [запрос] — поиск в интернете\n"
        "💬 **Просто напиши** вопрос — я отвечу\n"
        "😂 **/joke** — шутка\n"
        "🔄 **/newchat** — новый диалог\n"
        "🧹 **/clear** — очистить историю",
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['joke'])
def joke_cmd(message):
    bot.reply_to(message, f"😂 {random.choice(JOKES)}")

@bot.message_handler(commands=['newchat'])
def new_chat(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "пользователь"
    clear_history(user_id)
    bot.reply_to(message, f"🔄 **{user_name}**, начал новый диалог! История очищена. 😊")

@bot.message_handler(commands=['clear'])
def clear_chat(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "пользователь"
    clear_history(user_id)
    bot.reply_to(message, f"🧹 **{user_name}**, история диалога очищена! 😊")

# ==============================================
# 8. ОСНОВНАЯ ОБРАБОТКА
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
            bot.reply_to(message, f"📝 **{user_name}**, что нарисовать?", parse_mode='Markdown')
            return
        add_to_history(user_id, "user", f"Попросил нарисовать: {prompt}")
        status = bot.reply_to(message, f"🎨 Рисую...")
        image_path, clean_prompt = generate_image(prompt)
        if image_path:
            with open(image_path, 'rb') as f:
                bot.send_photo(message.chat.id, f, caption=f"🎨 *{clean_prompt.capitalize()}* готово!")
            os.remove(image_path)
            add_to_history(user_id, "assistant", f"Отправил картинку {clean_prompt}")
            bot.delete_message(message.chat.id, status.id)
        else:
            bot.edit_message_text("😅 Не удалось создать картинку.", message.chat.id, status.id)
        return

    # === ПОИСК ===
    if text_lower.startswith('найди') or text_lower.startswith('поищи'):
        query = text
        for word in ['найди', 'поищи', 'найди мне', 'поищи мне']:
            query = query.replace(word, '')
        query = query.strip()
        if not query:
            bot.reply_to(message, f"📝 **{user_name}**, что найти?", parse_mode='Markdown')
            return
        status = bot.reply_to(message, f"🔍 Ищу...")
        search_results = search_internet(query)
        if search_results:
            add_to_history(user_id, "user", f"Поиск: {query}")
            response = ask_mistral(f"Вопрос: {query}\nИнформация: {search_results}\nОтветь кратко.")
            add_to_history(user_id, "assistant", response)
            bot.delete_message(message.chat.id, status.id)
            send_long_message(message.chat.id, response)
        else:
            bot.edit_message_text("🔍 Ничего не найдено.", message.chat.id, status.id)
        return

    # === ОБЫЧНЫЙ ОТВЕТ ===
    add_to_history(user_id, "user", text)
    status = bot.reply_to(message, f"🤔 Думаю...")
    response = ask_mistral(text)
    add_to_history(user_id, "assistant", response)
    bot.delete_message(message.chat.id, status.id)
    send_long_message(message.chat.id, response)

# ==============================================
# 9. WEBHOOK
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
    return "🤖 Бот Смайл работает на Mistral!"

# ==============================================
# 10. ЗАПУСК
# ==============================================
if __name__ == '__main__':
    bot.remove_webhook()
    webhook_url = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'localhost')}/{TOKEN}"
    bot.set_webhook(url=webhook_url)
    print(f"✅ Вебхук установлен: {webhook_url}")
    
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)