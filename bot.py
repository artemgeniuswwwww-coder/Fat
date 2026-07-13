import telebot
import requests
import os
import time
import json
from googlesearch import search
import yt_dlp

# ==================== ТОКЕНЫ ====================
# ВАШИ ДАННЫЕ (уже вставлены)
TOKEN = '8719783774:AAHp4nEoQxqM23xpU8ppmEq9OeiVbpfCljU'
DEEPSEEK_KEY = 'sk-2e34591f3fbd430b8e1d4cc642955fbf'

# ==================== НАСТРОЙКА БОТА ====================
bot = telebot.TeleBot(TOKEN)

# ==================== 1. ГЕНЕРАЦИЯ КАРТИНОК ====================
def generate_image(prompt):
    try:
        url = f"https://image.pollinations.ai/prompt/{prompt.replace(' ', '%20')}?width=512&height=512"
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            with open('image.jpg', 'wb') as f:
                f.write(response.content)
            return 'image.jpg'
        return None
    except Exception as e:
        print(f"Ошибка генерации: {e}")
        return None

# ==================== 2. ПОИСК В ИНТЕРНЕТЕ ====================
def search_internet(query):
    try:
        results = []
        for url in search(query, num_results=3, advanced=True):
            results.append(f"🔗 {url.title}\n{url.description}\n{url.url}\n")
        return "\n".join(results) if results else "❌ Ничего не найдено"
    except Exception as e:
        return f"😅 Ошибка поиска: {e}"

# ==================== 3. АНАЛИЗ ВИДЕО ====================
def analyze_video(video_url):
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
        
        result = f"""
📹 **Информация о видео:**

🎬 **Название:** {info.get('title', 'Неизвестно')}
👤 **Автор:** {info.get('uploader', 'Неизвестно')}
⏱️ **Длительность:** {info.get('duration', 0) // 60} мин {info.get('duration', 0) % 60} сек
👁️ **Просмотров:** {info.get('view_count', 0):,}
"""
        # Анализ через DeepSeek
        analysis = ask_deepseek(
            f"Проанализируй это видео. Название: {info.get('title')}. Автор: {info.get('uploader')}. Напиши краткий анализ: о чём видео, какая тема."
        )
        return result + f"\n\n🤖 **Анализ от Смайла:**\n{analysis}"
    except Exception as e:
        return f"😅 Ошибка анализа: {e}"

# ==================== 4. ОТВЕТЫ ЧЕРЕЗ DEEPSEEK ====================
def ask_deepseek(prompt):
    url = "https://api.deepseek.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "Ты — Смайл 😊, дружелюбный ИИ-помощник. Отвечай кратко, с эмодзи, на русском языке."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": 800,
        "temperature": 0.7
    }
    try:
        response = requests.post(url, headers=headers, json=data, timeout=60)
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"😅 Ошибка: {e}"

# ==================== 5. ОБРАБОТКА КОМАНД ====================
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(
        message,
        "👋 Привет! Я **Смайл-Агент**! 🤖\n\n"
        "🎨 **Нарисуй** [описание] — создам картинку\n"
        "🔍 **Найди** [запрос] — поищу в интернете\n"
        "📹 **Отправь ссылку** на YouTube/TikTok — проанализирую\n"
        "💬 **Просто напиши** вопрос — я отвечу",
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
    
    # Анализ видео
    if 'youtube.com' in text_lower or 'youtu.be' in text_lower:
        status = bot.reply_to(message, "📹 Анализирую видео...")
        analysis = analyze_video(text)
        bot.edit_message_text(analysis, message.chat.id, status.id, parse_mode='Markdown')
        return
    
    # Поиск в интернете
    if 'найди' in text_lower or 'поищи' in text_lower:
        query = text.replace('найди', '').replace('поищи', '').strip()
        if not query:
            bot.reply_to(message, "📝 Напиши, что именно найти!")
            return
        status = bot.reply_to(message, f"🔍 Ищу: *{query}*...", parse_mode='Markdown')
        search_results = search_internet(query)
        response = ask_deepseek(f"Вопрос: {query}\nИнформация: {search_results}\nОтветь кратко.")
        bot.edit_message_text(response, message.chat.id, status.id, parse_mode='Markdown')
        return
    
    # Обычный ответ
    status = bot.reply_to(message, "🤔 Думаю...")
    response = ask_deepseek(text)
    bot.edit_message_text(response, message.chat.id, status.id, parse_mode='Markdown')

# ==================== ЗАПУСК ====================
if __name__ == '__main__':
    print("🤖 Бот Смайл-Агент запущен!")
    bot.polling(none_stop=True)