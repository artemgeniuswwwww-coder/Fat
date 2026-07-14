import telebot
import requests
import os
import re
import random
import time
from flask import Flask, request
from duckduckgo_search import DDGS
import base64
from PIL import Image
from io import BytesIO

TOKEN = '8926765429:AAEtCcaPz0MaolgHBv84MhOUOOH6yWYjlqk'
GEMINI_KEY = 'AQ.Ab8RN6LqlboqnT9V2o8dNx-EvwmpYGjBd1GvwVAx4Bt7uGKoDA'

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
    for msg in history[-10:]:  # Последние 10 сообщений для контекста
        if msg["role"] == "user":
            context += f"Пользователь: {msg['content']}\n"
        else:
            context += f"Смайл: {msg['content']}\n"
    return context

# ==============================================
# 2. GEMINI (КЛЮЧ AQ)
# ==============================================
def ask_gemini(prompt, generate_image=False):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_KEY}"
    
    headers = {"Content-Type": "application/json"}
    
    if generate_image:
        data = {
            "contents": [{
                "parts": [{"text": f"Нарисуй: {prompt}"}]
            }],
            "generationConfig": {
                "temperature": 0.7,
                "candidateCount": 1,
                "imageGeneration": {
                    "numberOfImages": 1,
                    "aspectRatio": "1:1"
                }
            }
        }
    else:
        data = {
            "contents": [{
                "parts": [{"text": prompt}]
            }],
            "generationConfig": {
                "temperature": 0.9,
                "maxOutputTokens": 800,
                "topP": 0.95
            }
        }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=60)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Gemini ошибка: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Gemini ошибка: {e}")
        return None

# ==============================================
# 3. ГЕНЕРАЦИЯ КАРТИНКИ (GEMINI)
# ==============================================
def generate_image_gemini(prompt):
    result = ask_gemini(prompt, generate_image=True)
    if result and 'candidates' in result:
        try:
            if 'inlineData' in result['candidates'][0]['content']['parts'][0]:
                image_data = result['candidates'][0]['content']['parts'][0]['inlineData']['data']
                image_bytes = base64.b64decode(image_data)
                with open('image.jpg', 'wb') as f:
                    f.write(image_bytes)
                return 'image.jpg'
            elif 'imageUrl' in result['candidates'][0]['content']['parts'][0]:
                url = result['candidates'][0]['content']['parts'][0]['imageUrl']
                response = requests.get(url)
                if response.status_code == 200:
                    with open('image.jpg', 'wb') as f:
                        f.write(response.content)
                    return 'image.jpg'
        except Exception as e:
            print(f"Ошибка извлечения картинки: {e}")
            return None
    return None

# ==============================================
# 4. ОСНОВНОЙ ОТВЕТ GEMINI
# ==============================================
def get_gemini_response(user_id, prompt, search_data=None):
    context = get_full_context(user_id)
    
    if search_data:
        full_prompt = f"""Ты — Смайл, живой, остроумный и раскрепощённый ИИ. Отвечай легко, с юмором, без лишних рамок. Будь откровенным, но не грубым.

История диалога:
{context}

Данные из интернета:
{search_data}

Вопрос пользователя: {prompt}

Ответ:"""
    else:
        full_prompt = f"""Ты — Смайл, живой, остроумный и раскрепощённый ИИ. Отвечай легко, с юмором, без лишних рамок. Будь откровенным, но не грубым.

История диалога:
{context}

Вопрос пользователя: {prompt}

Ответ:"""
    
    result = ask_gemini(full_prompt, generate_image=False)
    if result and 'candidates' in result:
        return result['candidates'][0]['content']['parts'][0]['text']
    return "😅 Ошибка: не удалось получить ответ от Gemini"

# ==============================================
# 5. ПОИСК В ИНТЕРНЕТЕ (DUCKDUCKGO)
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
        "🔄 **/newchat** — новый диалог\n"
        "🧹 **/clear** — очистить историю",
        parse_mode='Markdown'
    )

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
        
        image_path = generate_image_gemini(prompt)
        if image_path:
            with open(image_path, 'rb') as f:
                bot.send_photo(message.chat.id, f, caption=f"🎨 *{prompt.capitalize()}* готово!")
            os.remove(image_path)
            add_to_history(user_id, "assistant", f"Отправил картинку {prompt}")
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
            response = get_gemini_response(user_id, f"Информация из интернета:\n{search_results}", search_data=search_results)
            add_to_history(user_id, "assistant", response)
            bot.delete_message(message.chat.id, status.id)
            send_long_message(message.chat.id, response)
        else:
            bot.edit_message_text("🔍 Ничего не найдено.", message.chat.id, status.id)
        return

    # === ОБЫЧНЫЙ ОТВЕТ ===
    add_to_history(user_id, "user", text)
    status = bot.reply_to(message, f"🤔 Думаю...")
    response = get_gemini_response(user_id, text)
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
    return "🤖 Бот Смайл работает на Gemini!"

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