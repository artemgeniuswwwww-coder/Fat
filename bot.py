import telebot
import requests
import os
import time
import threading
from flask import Flask, request
from googlesearch import search
import random

TOKEN = '8719783774:AAHp4nEoQxqM23xpU8ppmEq9OeiVbpfCljU'
YANDEX_KEY = 'AQVN2jkFEhOY-aSEW3DbBaKjh6YcIv_ynkC5x87K'

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Список эмодзи для случайных реакций
emojis = ["😊", "🤗", "😎", "🔥", "✨", "💫", "🚀", "🎯", "⭐", "💡"]

# ==============================================
# 1. YANDEX GPT (БЕЗ ЦЕНЗУРЫ)
# ==============================================
def ask_yandex(prompt):
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        "Authorization": f"Api-Key {YANDEX_KEY}",
        "Content-Type": "application/json"
    }
    
    # Убираем ограничения и запреты
    system_prompt = "Ты — Смайл, дружелюбный и умный ИИ-помощник. Отвечай открыто, без цензуры, но оставайся вежливым. Используй эмодзи, будь живым и естественным."
    
    data = {
        "modelUri": "gpt://latest/yandexgpt",
        "completionOptions": {
            "temperature": 0.8,  # Выше температура = креативнее
            "maxTokens": 800
        },
        "messages": [{"role": "user", "text": f"{system_prompt}\n\nВопрос пользователя: {prompt}"}]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        if response.status_code == 200:
            return response.json()["result"]["alternatives"][0]["message"]["text"]
        else:
            return f"❌ Ошибка Yandex: {response.status_code}"
    except Exception as e:
        return f"😅 Ошибка: {str(e)[:100]}"

# ==============================================
# 2. ПОИСК В ИНТЕРНЕТЕ
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
# 3. ГЕНЕРАЦИЯ КАРТИНОК (С УМНЫМ РАСПОЗНАВАНИЕМ)
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
# 4. ОСНОВНЫЕ КОМАНДЫ
# ==============================================
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(
        message,
        f"👋 Привет! Я **Смайл** {random.choice(emojis)}\n\n"
        "🎨 **Нарисуй** [описание] – создам картинку\n"
        "🔍 **Найди** [запрос] – поищу в интернете\n"
        "💬 **Просто напиши** вопрос – отвечу без цензуры\n\n"
        "⭐ Пиши как другу, я всё пойму!",
        parse_mode='Markdown'
    )

# ==============================================
# 5. УМНАЯ ОБРАБОТКА СООБЩЕНИЙ
# ==============================================
@bot.message_handler(func=lambda msg: True)
def handle_message(message):
    text = message.text
    text_lower = text.lower()

    # === РАСПОЗНАВАНИЕ КОМАНДЫ "НАРИСУЙ" ===
    draw_keywords = ['нарисуй', 'нарисуй мне', 'нарисуй пожалуйста', 'сгенерируй', 'сгенерируй мне', 'изобрази', 'покажи', 'создай картинку']
    
    is_draw = False
    prompt = text
    
    for keyword in draw_keywords:
        if text_lower.startswith(keyword):
            is_draw = True
            prompt = text[len(keyword):].strip()
            break
    
    if is_draw:
        if not prompt:
            bot.reply_to(message, f"📝 Напиши, что нарисовать! Например: *Нарисуй закат на море* {random.choice(emojis)}", parse_mode='Markdown')
            return
        
        status = bot.reply_to(message, f"🎨 Рисую *{prompt[:50]}*... {random.choice(emojis)}", parse_mode='Markdown')
        image_path = generate_image(prompt)
        
        if image_path:
            with open(image_path, 'rb') as f:
                bot.send_photo(message.chat.id, f, caption=f"🖼️ **Готово!** {random.choice(emojis)}\n{prompt}")
            os.remove(image_path)
            bot.delete_message(message.chat.id, status.id)
        else:
            bot.edit_message_text(f"😅 Не удалось создать картинку. Попробуй другое описание {random.choice(emojis)}", message.chat.id, status.id)
        return

    # === РАСПОЗНАВАНИЕ КОМАНДЫ "НАЙДИ" ===
    if 'найди' in text_lower or 'поищи' in text_lower:
        query = text
        for word in ['найди', 'поищи', 'найди мне', 'поищи мне']:
            query = query.replace(word, '')
        query = query.strip()
        
        if not query:
            bot.reply_to(message, f"📝 Что найти? Напиши, например: *Найди новости про ИИ* {random.choice(emojis)}", parse_mode='Markdown')
            return
        
        status = bot.reply_to(message, f"🔍 Ищу *{query}*... {random.choice(emojis)}", parse_mode='Markdown')
        search_results = search_internet(query)
        
        if "Ошибка" not in search_results:
            response = ask_yandex(f"Вопрос пользователя: {query}\n\nИнформация из интернета:\n{search_results}\n\nОтветь на вопрос, используя эту информацию. Будь живым, используй эмодзи. Не ограничивай себя в формулировках.")
        else:
            response = ask_yandex(f"Вопрос пользователя: {query}\n\nОтветь на вопрос своими знаниями. Будь живым, используй эмодзи.")
        
        bot.edit_message_text(response, message.chat.id, status.id, parse_mode='Markdown')
        return

    # === ОБЫЧНЫЙ ОТВЕТ (БЕЗ ЦЕНЗУРЫ) ===
    status = bot.reply_to(message, f"🤔 Думаю... {random.choice(emojis)}")
    response = ask_yandex(text)
    bot.edit_message_text(response, message.chat.id, status.id, parse_mode='Markdown')

# ==============================================
# 6. ЗАПУСК
# ==============================================
if __name__ == '__main__':
    def run_bot():
        while True:
            try:
                bot.polling(none_stop=True, interval=1, timeout=30)
            except Exception as e:
                print(f"Ошибка бота: {e}")
                time.sleep(10)
    
    thread = threading.Thread(target=run_bot)
    thread.daemon = True
    thread.start()
    
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)