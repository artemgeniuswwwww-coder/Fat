import telebot
import requests
import os
import time
import random
from flask import Flask, request
from googlesearch import search

TOKEN = '8926765429:AAEtCcaPz0MaolgHBv84MhOUOOH6yWYjlqk'
HF_TOKEN = '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'  # ВСТАВЬ СЮДА НОВЫЙ ТОКЕН

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ==============================================
# 1. HUGGING FACE С НОВЫМ ТОКЕНОМ
# ==============================================
def ask_huggingface(prompt):
    # Используем лёгкую модель
    url = "https://api-inference.huggingface.co/models/microsoft/DialoGPT-medium"
    
    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json"
    }
    
    data = {
        "inputs": f"User: {prompt}\nBot:",
        "parameters": {
            "max_length": 100,
            "temperature": 0.8,
            "top_p": 0.9
        }
    }
    
    try:
        # Добавляем задержку, чтобы не перегружать
        time.sleep(1)
        
        response = requests.post(url, headers=headers, json=data, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0:
                answer = result[0].get("generated_text", "")
                # Очищаем ответ
                if "Bot:" in answer:
                    answer = answer.split("Bot:")[-1].strip()
                elif "User:" in answer:
                    answer = answer.split("User:")[0].strip()
                return answer if answer else "😊 Понял! А что ещё?"
            return "😊 Я тут!"
        else:
            return f"⏳ Много запросов, попробуй через 10 секунд. (Код: {response.status_code})"
    except Exception as e:
        return f"😅 Ошибка: {str(e)[:100]}"

# ==============================================
# 2. ГЕНЕРАЦИЯ КАРТИНОК
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
# 3. ПОИСК В ИНТЕРНЕТЕ
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
# 4. КОМАНДЫ БОТА
# ==============================================
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(
        message,
        "👋 Привет! Я **Смайл** 🤖\n\n"
        "🎨 **Нарисуй** [описание] – картинка\n"
        "🔍 **Найди** [запрос] – поиск в интернете\n"
        "💬 **Просто напиши** вопрос – отвечу через Hugging Face\n\n"
        "⚡ Бесплатно, без лимитов!",
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
            response = ask_huggingface(f"Вопрос: {query}\nИнформация: {search_results}\nОтветь кратко.")
        else:
            response = ask_huggingface(f"Вопрос: {query}")
        
        bot.edit_message_text(response, message.chat.id, status.id, parse_mode='Markdown')
        return

    # === ОБЫЧНЫЙ ОТВЕТ ===
    status = bot.reply_to(message, "🤔 Думаю...")
    response = ask_huggingface(text)
    bot.edit_message_text(response, message.chat.id, status.id, parse_mode='Markdown')

# ==============================================
# 5. WEBHOOK
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
# 6. ЗАПУСК
# ==============================================
if __name__ == '__main__':
    bot.remove_webhook()
    webhook_url = f"https://{os.environ.get('RENDER_EXTERNAL_HOSTNAME', 'localhost')}/{TOKEN}"
    bot.set_webhook(url=webhook_url)
    print(f"✅ Вебхук установлен: {webhook_url}")
    
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)