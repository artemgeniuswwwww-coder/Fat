import telebot
import requests
import os
import time
import random
from flask import Flask, request

TOKEN = '8926765429:AAEtCcaPz0MaolgHBv84MhOUOOH6yWYjlqk'
QWEN_KEY = 'sk-ws-H.XHIDDP.Oq2b.MEUCIQC-SAYI77dOL2V7sryEy4qqiG2EumN2Paq2ex7MDs_yZAIgKWZXLhtH4MmeV_T6b5tnXYn25qZvFaDrt7HhubJc7FE'  # ВСТАВЬ КЛЮЧ QWEN

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ==============================================
# 1. QWEN
# ==============================================
def ask_qwen(prompt):
    url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
    headers = {
        "Authorization": f"Bearer {QWEN_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "qwen-turbo",
        "input": {
            "messages": [
                {"role": "system", "content": "Ты — Смайл, дружелюбный помощник. Отвечай кратко, с эмодзи, на русском."},
                {"role": "user", "content": prompt}
            ]
        },
        "parameters": {"max_tokens": 500, "temperature": 0.7}
    }
    try:
        response = requests.post(url, headers=headers, json=data, timeout=30)
        if response.status_code == 200:
            return response.json()["output"]["text"]
        return f"❌ Ошибка Qwen: {response.status_code}"
    except Exception as e:
        return f"😅 Ошибка: {str(e)[:100]}"

# ==============================================
# 2. ГЕНЕРАЦИЯ КАРТИНОК (2 СПОСОБА)
# ==============================================
def generate_image(prompt):
    # Добавляем случайное число для разнообразия
    seed = random.randint(1, 999999)
    
    # СПОСОБ 1: Pollinations.ai (с seed)
    url1 = f"https://image.pollinations.ai/prompt/{prompt.replace(' ', '%20')}?width=512&height=512&seed={seed}"
    
    # СПОСОБ 2: Lexica.art (альтернативный бесплатный API)
    url2 = f"https://lexica.art/api/v1/search?q={prompt.replace(' ', '%20')}"
    
    try:
        # Пробуем первый способ
        response1 = requests.get(url1, timeout=30)
        if response1.status_code == 200:
            with open('image.jpg', 'wb') as f:
                f.write(response1.content)
            return 'image.jpg'
    except:
        pass
    
    try:
        # Пробуем второй способ (берём первую картинку из поиска)
        response2 = requests.get(url2, timeout=30)
        if response2.status_code == 200:
            data = response2.json()
            if data.get('images') and len(data['images']) > 0:
                img_url = data['images'][0]['src']
                img_response = requests.get(img_url, timeout=30)
                if img_response.status_code == 200:
                    with open('image.jpg', 'wb') as f:
                        f.write(img_response.content)
                    return 'image.jpg'
    except:
        pass
    
    return None

# ==============================================
# 3. КОМАНДЫ
# ==============================================
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(
        message,
        "👋 Привет! Я **Смайл** 🤖\n\n"
        "🎨 **Нарисуй** [описание] – картинка\n"
        "💬 **Просто напиши** вопрос – отвечу через Qwen\n\n"
        "⚡ 1 млн токенов в месяц!",
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

    # === ОБЫЧНЫЙ ОТВЕТ ===
    status = bot.reply_to(message, "🤔 Думаю...")
    response = ask_qwen(text)
    bot.edit_message_text(response, message.chat.id, status.id, parse_mode='Markdown')

# ==============================================
# 4. WEBHOOK
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
    return "🤖 Бот Смайл работает на Qwen!"

# ==============================================
# 5. ЗАПУСК
# ==============================================
if __name__ == '__main__':
    bot.remove_webhook()
    webhook_url = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'localhost')}/{TOKEN}"
    bot.set_webhook(url=webhook_url)
    print(f"✅ Вебхук установлен: {webhook_url}")
    
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)