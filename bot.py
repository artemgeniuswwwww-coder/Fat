import telebot
import requests
import os
import time
from googlesearch import search

# ===================================================
# ТВОЙ НОВЫЙ ТОКЕН (УЖЕ ВСТАВЛЕН)
# ===================================================
TOKEN = '8926765429:AAEtCcaPz0MaolgHBv84MhOUOOH6yWYjlqk'
YANDEX_KEY = 'AQVN2jkFEhOY-aSEW3DbBaKjh6YcIv_ynkC5x87K'

bot = telebot.TeleBot(TOKEN)

# ===================================================
# 1. ОСНОВНОЙ ИИ — YANDEX GPT
# ===================================================
def ask_yandex(prompt):
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        "Authorization": f"Api-Key {YANDEX_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "modelUri": "gpt://latest/yandexgpt",
        "completionOptions": {
            "temperature": 0.8,
            "maxTokens": 800
        },
        "messages": [{
            "role": "user",
            "text": f"Ты — Смайл 😊, дружелюбный помощник. Отвечай кратко, с эмодзи, на русском. Вопрос: {prompt}"
        }]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        if response.status_code == 200:
            return response.json()["result"]["alternatives"][0]["message"]["text"]
        return f"❌ Ошибка Yandex: {response.status_code}"
    except Exception as e:
        return f"😅 Ошибка: {str(e)[:100]}"

# ===================================================
# 2. ГЕНЕРАЦИЯ КАРТИНКИ
# ===================================================
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

# ===================================================
# 3. ПОИСК В ИНТЕРНЕТЕ
# ===================================================
def search_internet(query):
    try:
        results = []
        for url in search(query, num_results=3):
            results.append(f"🔗 {url}")
        return "\n".join(results) if results else "❌ Ничего не найдено"
    except Exception as e:
        return f"😅 Ошибка поиска: {e}"

# ===================================================
# 4. КОМАНДЫ БОТА
# ===================================================
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

# ===================================================
# 5. ЗАПУСК
# ===================================================
if __name__ == "__main__":
    print("🚀 Бот Смайл запущен!")
    bot.polling(none_stop=True)