import telebot
import requests
import os
import time
import threading
from flask import Flask, request

TOKEN = '8719783774:AAHp4nEoQxqM23xpU8ppmEq9OeiVbpfCljU'
YANDEX_KEY = 'AQVN2jkFEhOY-aSEW3DbBaKjh6YcIv_ynkC5x87K'
HF_TOKEN = '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'

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# Счётчик запросов к Яндексу
yandex_count = 0
YANDEX_LIMIT = 1000

# ==============================================
# 1. YANDEX GPT
# ==============================================
def ask_yandex(prompt):
    global yandex_count
    
    if yandex_count >= YANDEX_LIMIT:
        return None
    
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {
        "Authorization": f"Api-Key {YANDEX_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "modelUri": "gpt://latest/yandexgpt",
        "completionOptions": {
            "temperature": 0.6,
            "maxTokens": 500
        },
        "messages": [{"role": "user", "text": f"Ты — Смайл 😊, дружелюбный помощник. Отвечай кратко, с эмодзи. Вопрос: {prompt}"}]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        if response.status_code == 200:
            yandex_count += 1
            return response.json()["result"]["alternatives"][0]["message"]["text"]
        return None
    except:
        return None

# ==============================================
# 2. HUGGING FACE
# ==============================================
def ask_huggingface(prompt):
    url = "https://api-inference.huggingface.co/models/google/flan-t5-large"
    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json"
    }
    
    data = {
        "inputs": f"Ответь на русском языке кратко и дружелюбно: {prompt}",
        "parameters": {
            "max_length": 200,
            "temperature": 0.7
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=60)
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                return result[0].get("generated_text", "😅 Не удалось получить ответ")
            return str(result)
        return f"❌ Ошибка HF: {response.status_code}"
    except:
        return "😅 Ошибка соединения с Hugging Face"

# ==============================================
# 3. УНИВЕРСАЛЬНЫЙ ВЫЗОВ
# ==============================================
def ask_ai(prompt):
    # Сначала пробуем Yandex
    answer = ask_yandex(prompt)
    if answer:
        return answer
    
    # Если Yandex не ответил — Hugging Face
    return ask_huggingface(prompt)

# ==============================================
# 4. ГЕНЕРАЦИЯ КАРТИНОК
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
# 5. КОМАНДЫ БОТА
# ==============================================
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(
        message,
        "👋 Привет! Я **Смайл** 🤖\n\n"
        "🎨 **Нарисуй** [описание] – создам картинку\n"
        "💬 **Просто напиши** вопрос – отвечу через Yandex или Hugging Face\n\n"
        f"⚡ Осталось запросов к Yandex: {YANDEX_LIMIT - yandex_count}",
        parse_mode='Markdown'
    )

@bot.message_handler(commands=['stats'])
def stats(message):
    bot.reply_to(
        message,
        f"📊 **Статистика:**\n\n"
        f"✅ Yandex использовано: {yandex_count} / {YANDEX_LIMIT}\n"
        f"🔄 После лимита включится Hugging Face",
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
            bot.reply_to(message, "📝 Напиши, что нарисовать!")
            return
        
        status = bot.reply_to(message, f"🎨 Рисую: *{prompt[:50]}*...", parse_mode='Markdown')
        image_path = generate_image(prompt)
        
        if image_path:
            with open(image_path, 'rb') as f:
                bot.send_photo(message.chat.id, f, caption=f"🖼️ {prompt}")
            os.remove(image_path)
            bot.delete_message(message.chat.id, status.id)
        else:
            bot.edit_message_text("😅 Не удалось создать картинку.", message.chat.id, status.id)
        return

    # === ОБЫЧНЫЙ ОТВЕТ ===
    status = bot.reply_to(message, "🤔 Думаю...")
    response = ask_ai(text)
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