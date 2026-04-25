import os
import random
import re
import json
import time
import threading
import schedule
from datetime import datetime, timedelta
from flask import Flask, request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
# Мозг Ревижна
from revision_mind import RevisionMind

# Конфигурация
from config import *

# Утилиты
from utils.data_loader import DataLoader
from utils.safe_calc import SafeCalculator

# Стриминг сообщений
USE_STREAMING = False
# Вспомогательная функция для стриминга
def generate_draft_id():
    """Генерирует уникальный ID для черновика сообщения."""
    import time
    import random
    return int(time.time() * 1000) + random.randint(0, 999)

# Установка часового пояса
os.environ['TZ'] = TIMEZONE
try:
    time.tzset()
except:
    pass

# Инициализация
bot = telebot.TeleBot(BOT_TOKEN)
# ========== НАСТРОЙКА GIT ДЛЯ АВТОПУША ==========
def setup_git():
    """Настраивает Git на Render"""
    import subprocess
    try:
        subprocess.run(["git", "config", "--global", "user.name", "hattorigg"], check=True)
        subprocess.run(["git", "config", "--global", "user.email", "bot@revision.local"], check=True)
        print("✅ Git настроен для автопуша")
    except Exception as e:
        print(f"❌ Ошибка настройки Git: {e}")

def setup_git_remote():
    """Настраивает удалённый репозиторий для пуша"""
    import subprocess
    import os
    
    result = subprocess.run(["git", "remote", "get-url", "origin"], capture_output=True, text=True)
    
    if result.returncode != 0:
        github_token = os.environ.get('GITHUB_TOKEN', '')
        if not github_token:
            print("⚠️ GITHUB_TOKEN не найден в переменных окружения")
            return
        
        repo_url = f"https://{github_token}@github.com/hattorigg/NirvanaHelper.git"
        
        try:
            subprocess.run(["git", "remote", "add", "origin", repo_url], check=True)
            print("✅ Git remote origin настроен")
        except Exception as e:
            print(f"❌ Ошибка настройки remote: {e}")
    else:
        print(f"✅ Git remote уже настроен")

setup_git()
setup_git_remote()
# Инициализация Ревижна
revision = RevisionMind()
app = Flask(__name__)
data = DataLoader()

# Загрузка данных из JSON
HOLIDAYS = data.load(HOLIDAYS_FILE)
FACTS = data.load(FACTS_FILE)
CREEPY_FACTS = data.load(CREEPY_FACTS_FILE)
HISTORICAL_EVENTS = data.load(HISTORICAL_EVENTS_FILE)
HISTORICAL_FACTS = data.load(HISTORICAL_FACTS_FILE)
MOVIES = data.load(MOVIES_FILE)
SERIES = data.load(SERIES_FILE)
ANIME = data.load(ANIME_FILE)
COCKTAILS = data.load(COCKTAILS_FILE)
RECIPES = data.load(RECIPES_FILE)
TOASTS = data.load(TOASTS_FILE)
COMPLIMENTS = data.load(COMPLIMENTS_FILE)
EXCUSES = data.load(EXCUSES_FILE)
ADVICES = data.load(ADVICES_FILE)
WISHES = data.load(WISHES_FILE)
QUOTES = data.load(QUOTES_FILE)
NAMES = data.load(NAMES_FILE)
NICKS = data.load(NICKS_FILE)
COLORS = data.load(COLORS_FILE)
EMOJI_LIST = data.load(EMOJI_FILE)
RP_PHRASES = data.load(RP_PHRASES_FILE)

# Глобальные переменные
bot_start_time = time.time()
user_names = {}
ttt_games = {}
user_dialogs = {}  # История диалогов для ИИ (ключ: user_id)

# ========== ИНИЦИАЛИЗАЦИЯ НАСТРОЕК ==========
def init_settings():
    if not os.path.exists(SETTINGS_FILE):
        data.save(SETTINGS_FILE, {"title_updates": True})

init_settings()

# ========== КОМАНДА SAY (ТОЛЬКО ДЛЯ СОЗДАТЕЛЯ) ==========
@bot.message_handler(commands=['say'])
def cmd_say(message):
    if message.from_user.id != CREATOR_ID:
        bot.reply_to(message, "❌ Эта команда только для создателя")
        return
    
    text = message.text[5:].strip()
    if not text:
        bot.reply_to(message, "❌ Напиши текст после /say")
        return
    
    try:
        bot.send_message(CHAT_ID, text)
        bot.reply_to(message, "✅ Отправлено!")
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка при отправке: {e}")

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
def get_today_holiday():
    now = datetime.now()
    today_key = now.strftime('%m-%d')
    return HOLIDAYS.get(today_key, 'обычный день')

def update_chat_title():
    settings = data.load(SETTINGS_FILE)
    if not settings.get("title_updates", True):
        return
    
    holiday = get_today_holiday()
    emoji = holiday.split()[0] if holiday else "🎉"
    new_title = f"Nirvana {emoji}"
    
    try:
        bot.set_chat_title(CHAT_ID, new_title)
        print(f"✅ Название обновлено: {new_title}")
    except Exception as e:
        print(f"❌ Ошибка при смене названия: {e}")

# ========== НАПОМИНАЛКИ ==========
def load_reminders():
    return data.load(REMINDERS_FILE) if os.path.exists(REMINDERS_FILE) else []

def save_reminders(reminders):
    data.save(REMINDERS_FILE, reminders)

def check_reminders():
    while True:
        try:
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            reminders = load_reminders()
            to_remove = []
            for rem in reminders:
                if rem["time"] == now:
                    bot.send_message(rem["chat_id"], f"⏰ *НАПОМИНАНИЕ!*\n\n{rem['text']}", parse_mode="Markdown")
                    to_remove.append(rem)
            if to_remove:
                reminders = [r for r in reminders if r not in to_remove]
                save_reminders(reminders)
        except Exception as e:
            print(f"Ошибка проверки напоминаний: {e}")
        time.sleep(30)

reminder_thread = threading.Thread(target=check_reminders, daemon=True)
reminder_thread.start()

# ========== РУССКИЕ МЕМЫ С REDDIT (r/Pikabu) ==========
@bot.message_handler(commands=['meme'])
def cmd_meme(message):
    try:
        import requests
        import random as rand

        target_url = "https://www.reddit.com/r/Pikabu/hot.json?limit=50"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        resp = requests.get(target_url, headers=headers, timeout=10)
        
        if resp.status_code != 200:
            bot.reply_to(message, "😕 Не удалось получить мемы с Pikabu. Попробуй позже.")
            return

        data = resp.json()
        posts = data['data']['children']

        # Собираем все посты с картинками
        meme_posts = []
        for post in posts:
            post_data = post['data']
            if 'url' in post_data and post_data['url'].endswith(('.jpg', '.jpeg', '.png', '.gif')):
                meme_posts.append(post_data)

        if not meme_posts:
            bot.reply_to(message, "😕 Сегодня без мемов. Но ты всегда можешь попробовать снова.")
            return

        # Выбираем случайный
        chosen = rand.choice(meme_posts)
        meme_url = chosen['url']
        title = chosen.get('title', '')

        bot.send_photo(
            message.chat.id, 
            meme_url, 
            caption=f"🍿 {title}" if title else "🍿 Держи мем с Pikabu!"
        )

    except Exception as e:
        bot.reply_to(message, f"😢 Ошибка при получении мема: {e}")
        
# ========== ДОБАВЛЕНИЕ МЕМОВ С АВТО-ДЕПЛОЕМ (ТОЛЬКО В ЧАТЕ) ==========
@bot.message_handler(commands=['addmeme_old'])
def cmd_addmeme(message):
    """Добавляет новый мем и пушит в GitHub (только в основном чате)"""
    
    # Проверка, что команда используется в нужном чате
    if message.chat.id != CHAT_ID:
        bot.reply_to(message, "❌ Эта команда работает только в основном чате!")
        return
    
    # Проверка, что это ответ на фото
    if not message.reply_to_message or not message.reply_to_message.photo:
        bot.reply_to(message, "❌ Отправь эту команду в ОТВЕТ на сообщение с картинкой!")
        return
    
    status_msg = bot.reply_to(message, "📥 Скачиваю мем...")
    
    try:
        photo = message.reply_to_message.photo[-1]
        file_info = bot.get_file(photo.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        import re
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        user_id = message.from_user.id
        
        raw_name = message.from_user.first_name or "user"
        safe_name = re.sub(r'[^a-zA-Z0-9_-]', '', raw_name)
        if not safe_name:
            safe_name = f"user{user_id}"
        
        filename = f"meme_{safe_name}_{timestamp}.jpg"
        filepath = os.path.join(MEME_FOLDER, filename)
        
        os.makedirs(MEME_FOLDER, exist_ok=True)
        
        with open(filepath, 'wb') as f:
            f.write(downloaded_file)
        
        bot.edit_message_text(
            f"✅ Мем сохранён!\n📁 `{filename}`\n📤 Пушу в GitHub...",
            chat_id=status_msg.chat.id,
            message_id=status_msg.message_id,
            parse_mode="Markdown"
        )
        
        import subprocess
        
        subprocess.run(["git", "add", filepath], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", f"Add meme: {filename}"], check=True, capture_output=True)
        subprocess.run(["git", "push", "origin", "HEAD:main"], check=True, capture_output=True)
        
        bot.edit_message_text(
            f"✅ Мем добавлен и отправлен в GitHub!\n"
            f"📁 `{filename}`\n"
            f"🚀 Render начнёт деплой автоматически.",
            chat_id=status_msg.chat.id,
            message_id=status_msg.message_id,
            parse_mode="Markdown"
        )
        
        print(f"📸 Новый мем от {safe_name} добавлен и запушен: {filename}")
        
    except subprocess.CalledProcessError as e:
        error_msg = f"❌ Ошибка Git: {e.stderr.decode() if e.stderr else str(e)}"
        bot.edit_message_text(error_msg[:200], chat_id=status_msg.chat.id, message_id=status_msg.message_id)
        print(f"❌ Git error: {e}")
        
    except Exception as e:
        bot.edit_message_text(f"❌ Ошибка: {e}", chat_id=status_msg.chat.id, message_id=status_msg.message_id)
        print(f"❌ Addmeme error: {e}")
        
# ========== ИИ-ЧАТ (Revision) ==========
def ask_g4f(prompt, user_id=None, user_name="друг"):
    """Отправляет запрос к g4f с учётом состояния Ревижна"""
    try:
        from g4f import ChatCompletion
        
        history = user_dialogs.get(user_id, []) if user_id else []
        context = ""
        for msg in history[-10:]:
            context += f"{msg['role']}: {msg['text']}\n"
        
        system_prompt = revision.build_prompt(prompt, context, user_name)
        
        models_to_try = ["gpt-4", "gpt-3.5-turbo", "claude-3-haiku", "gemini-pro"]
        answer = None
        
        for model in models_to_try:
            try:
                response = ChatCompletion.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    timeout=15
                )
                if response:
                    answer = response
                    break
            except:
                continue
        
        if not answer:
            return "😕 Не удалось получить ответ. Попробуй позже."
        
        # 🛡️ ПРИНУДИТЕЛЬНАЯ ЗАЩИТА ЛИЧНОСТИ
        # Если в вопросе спрашивают про создателя, а ответ содержит OpenAI — заменяем
        creator_questions = [
            "кто тебя создал", "кто твой создатель", "кто тебя разработал",
            "кто твой разработчик", "кто тебя сделал", "чей ты",
            "кто тебя придумал", "кто твой автор", "who created you",
            "who made you", "who developed you"
        ]
        
        forbidden_words = [
            "OpenAI", "openai", "ChatGPT", "chatgpt", "GPT", "gpt",
            "команда разработчиков", "исследователей", "компании OpenAI",
            "Anthropic", "Claude", "Google", "Gemini", "разработала компания"
        ]
        
        # Проверяем, спрашивали ли про создателя
        asked_about_creator = any(q in prompt.lower() for q in creator_questions)
        
        # Проверяем, есть ли запрещённые слова в ответе
        has_forbidden = any(word.lower() in answer.lower() for word in forbidden_words)
        
        if asked_about_creator and has_forbidden:
            answer = (
                "Мой создатель — @HATTQRI. Он написал меня с нуля и вложил душу. "
                "Я не имею отношения к OpenAI или другим корпорациям — я самостоятельный проект, "
                "живущий в Telegram."
            )
        # Если запрещённые слова есть, но не спрашивали про создателя — просто убираем их
        elif has_forbidden and not asked_about_creator:
            for word in forbidden_words:
                if word.lower() in answer.lower():
                    answer = answer.replace(word, "").replace("  ", " ").strip()
                    # Если после замены ответ стал пустым или слишком коротким
                    if len(answer) < 10:
                        answer = "Извини, я немного запутался. Давай поговорим о чём-то другом?"
        
        return answer
        
    except Exception as e:
        return f"❌ Ошибка: {e}"
        
# ========== ОБРАБОТЧИК ИИ-ЧАТА С ПОДДЕРЖКОЙ СТРИМИНГА И РЕАКЦИЙ ==========
@bot.message_handler(func=lambda message: 
    message.text and 
    (message.text.startswith('@RevisionMainBot') or 
     (message.reply_to_message and 
      message.reply_to_message.from_user.id == bot.get_me().id and
      message.text.startswith('.')))
)
def revision_chat(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name or "друг"
    
    # Ставим реакцию «👀» сразу, чтобы показать, что сообщение принято в обработку
    try:
        bot.set_message_reaction(
            chat_id=message.chat.id,
            message_id=message.message_id,
            reaction=[{"type": "emoji", "emoji": "👀"}],
            is_big=False
        )
    except Exception as e:
        print(f"Reaction error (👀): {e}")
    
    # Определяем текст запроса
    if message.text.startswith('@RevisionMainBot'):
        text = message.text.replace('@RevisionMainBot', '').strip()
        user_dialogs[user_id] = []  # Новый диалог
        revision.remember(user_id, "new_dialogue", {"user_name": user_name})
    elif message.text.startswith('.'):
        text = message.text[1:].strip()
        revision.remember(user_id, "continue_dialogue", {"message": text[:50]})
    else:
        return
    
    if not text:
        bot.reply_to(message, "❓ Напиши вопрос после @RevisionMainBot или точку и продолжение")
        return
    
    # Ревижн тратит энергию
    revision.adjust_energy(-3)
    
    # Определяем, нужно ли использовать стриминг
    is_private = message.chat.type == 'private'
    use_streaming = USE_STREAMING and is_private
    
    if use_streaming:
        # === СТРИМИНГ: ИСПОЛЬЗУЕМ SENDMESSAGEDRAFT ===
        draft_id = generate_draft_id()
        accumulated_text = ""
        last_sent_text = ""
        
        # Отправляем первое пустое сообщение-заглушку
        placeholder_msg = bot.send_message(message.chat.id, "…")
        
        try:
            from g4f import ChatCompletion
            
            # Получаем историю и строим промпт
            history = user_dialogs.get(user_id, [])
            context = ""
            for msg in history[-10:]:
                context += f"{msg['role']}: {msg['text']}\n"
            system_prompt = revision.build_prompt(text, context, user_name)
            
            # Выбираем модель
            models_to_try = ["gpt-4", "gpt-3.5-turbo", "claude-3-haiku", "gemini-pro"]
            response_generator = None
            
            for model in models_to_try:
                try:
                    response_generator = ChatCompletion.create(
                        model=model,
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": text}
                        ],
                        stream=True,
                        timeout=15
                    )
                    break
                except:
                    continue
            
            if response_generator is None:
                raise Exception("Не удалось инициализировать стриминг")
            
            # Обрабатываем поток токенов
            for chunk in response_generator:
                if chunk:
                    accumulated_text += chunk
                    if len(accumulated_text) - len(last_sent_text) > 3:
                        try:
                            bot.send_message_draft(
                                chat_id=message.chat.id,
                                text=accumulated_text,
                                draft_id=draft_id
                            )
                            last_sent_text = accumulated_text
                        except Exception as draft_e:
                            print(f"Draft error: {draft_e}")
            
            answer = accumulated_text
            
        except Exception as e:
            print(f"Streaming error: {e}, falling back to normal mode")
            thinking = bot.reply_to(message, "🤔 Думаю...")
            answer = ask_g4f(text, user_id, user_name)
            bot.delete_message(chat_id=message.chat.id, message_id=thinking.message_id)
            use_streaming = False
        
        if use_streaming:
            bot.delete_message(chat_id=message.chat.id, message_id=placeholder_msg.message_id)
            bot.reply_to(message, answer)
            
    else:
        # === ОБЫЧНЫЙ РЕЖИМ (без стриминга) ===
        thinking = bot.reply_to(message, "🤔 Думаю...")
        answer = ask_g4f(text, user_id, user_name)
        try:
            bot.edit_message_text(answer, chat_id=message.chat.id, message_id=thinking.message_id)
        except:
            bot.reply_to(message, answer)
    
    # Сохраняем в историю
    if user_id not in user_dialogs:
        user_dialogs[user_id] = []
    user_dialogs[user_id].append({"role": user_name, "text": text})
    user_dialogs[user_id].append({"role": "Ревижн", "text": answer})
    
    if len(user_dialogs[user_id]) > 20:
        user_dialogs[user_id] = user_dialogs[user_id][-20:]
    
    revision.remember(user_id, "dialogue_complete", {"bot_response": answer[:50]})
    
    # Заменяем реакцию «👀» на более подходящую по контексту
    final_emoji = choose_reaction_emoji(text)
    if final_emoji:
        try:
            bot.set_message_reaction(
                chat_id=message.chat.id,
                message_id=message.message_id,
                reaction=[{"type": "emoji", "emoji": final_emoji}],
                is_big=False
            )
        except Exception as e:
            print(f"Reaction error ({final_emoji}): {e}")

# ========== RP-КОМАНДЫ ==========
def get_target_name(message):
    """Возвращает имя цели для RP-команды"""
    if message.reply_to_message:
        return message.reply_to_message.from_user.first_name
    elif len(message.text.split()) > 1:
        return message.text.split()[1]
    else:
        return "воздух"

def create_rp_handler(command_name, phrase_key):
    """Создаёт обработчик для RP-команды"""
    def handler(message):
        target = get_target_name(message)
        
        # Получаем ID цели, если это пользователь
        target_id = None
        if message.reply_to_message:
            target_id = message.reply_to_message.from_user.id
            # Если имя не указано явно, берем из ответа
            if target == message.reply_to_message.from_user.first_name:
                target = f"[{target}](tg://user?id={target_id})"
        elif len(message.text.split()) > 1:
            # Если имя введено текстом, мы не можем знать его ID, оставляем как есть
            pass
            
        category = RP_PHRASES.get(phrase_key, {})
        phrases = category.get("phrases", [f"взаимодействует с {target}"])
        emoji = category.get("emoji", "✨")
        phrase = random.choice(phrases)
        
        author_name = message.from_user.first_name
        author_id = message.from_user.id
        author_link = f"[{author_name}](tg://user?id={author_id})"
        
        formatted = phrase.format(target=target, author=author_name)
        bot.reply_to(message, f"{emoji} {author_link} {formatted}", parse_mode='Markdown')
    return handler

# Регистрируем RP-команды
RP_COMMANDS = {
    "обнять": "hug", "согреть": "warm", "укрыть": "cover", "погладить": "stroke",
    "пожалеть": "pity", "налить_чай": "tea", "подарить_уют": "gift_cozy",
    "посветить": "light", "заварить_кофе": "coffee", "укусить": "bite",
    "ударить": "hit", "задушить": "suffocate", "закидать_тапками": "slippers",
    "отправить_в_бан": "ban", "дать_леща": "leash", "загипнотизировать": "hypnose",
    "обнять_со_спины": "hug_back", "сделать_комплимент": "compliment_rp",
    "испугать": "scare", "кинуть_подушкой": "pillow", "облить_водой": "water",
    "защитить": "protect", "атаковать": "attack", "исцелить": "heal",
    "воскресить": "resurrect", "подарить_тишину": "gift_silence",
    "поделиться_светом": "share_light", "обнять_душой": "hug_soul",
    "послать_лучики": "send_rays", "разделить_тишину": "share_silence",
    "почесать": "scratch", "отдаться": "surrender", "прижать": "press",
    "потрогать": "touch", "полапать": "grope", "порвать": "tear",
    "дать_пять": "highfive", "выпить_чай": "drink_tea_together",
    "выпить_кофе": "drink_coffee_together", "уебать": "destroy"
}

for cmd, key in RP_COMMANDS.items():
    bot.message_handler(commands=[cmd])(create_rp_handler(cmd, key))

# ========== КАЛЬКУЛЯТОР ==========
@bot.message_handler(commands=['calc'])
def cmd_calc(message):
    expression = message.text[5:].strip()
    if not expression:
        bot.reply_to(message, "❌ Напиши выражение, например: /calc 2+2*2")
        return
    result = SafeCalculator.calculate(expression)
    if result is not None:
        bot.reply_to(message, f"🧮 {expression} = {result}")
    else:
        bot.reply_to(message, "❌ Неверное выражение. Используй цифры и + - * / ( )")

@bot.message_handler(func=lambda message: 
    re.match(r'^[0-9+\-*/().\s]+$', message.text) and 
    not message.text.startswith('/') and 
    any(op in message.text for op in '+-*/'))
def auto_calc(message):
    result = SafeCalculator.calculate(message.text)
    if result is not None:
        bot.reply_to(message, f"🧮 {message.text} = {result}")

# ========== ПРОСТЫЕ КОМАНДЫ ==========
@bot.message_handler(commands=['start'])
def cmd_start(message):
    start_text = (
        "👋 Привет… Ты здесь. Значит, не случайно.\n\n"
        "Я — Revision, ИИ-помощник. Не просто набор команд, а маленький островок тепла в твоём чате.\n\n"
        "📖 Полный список команд: /help\n\n"
        "🚀 Меня можно вызывать через @RevisionMainBot в любом чате\n"
        "💬 Чтобы продолжить диалог с ИИ, ответь на моё сообщение и начни с точки (например: .привет)"
    )
    bot.reply_to(message, start_text)

@bot.message_handler(commands=['help', 'хелп'])
def cmd_help(message):
    help_text = (
        "🌿 Я — Revision, ИИ-помощник. Не просто бот, а твой тихий спутник в цифровом мире.\n\n"
        "📌 Что я умею:\n\n"
        "🎲 Погода, таро, вайб, настроение, энергия дня\n"
        "⏰ Напоминалки, смена названия чата по праздникам\n"
        "😂 Мемы, цитаты, факты, игры и уютные ритуалы\n"
        "🔮 Инлайн-режим: вызывай меня в любом чате через @RevisionMainBot\n\n"
        "🤖 ИИ-чат:\n"
        "• @RevisionMainBot вопрос — задать вопрос\n"
        "• ответь на моё сообщение и начни с точки — продолжить диалог\n\n"
        "🌍 Полный список команд:\n"
        "https://graph.org/Mnogofunkcionalnyj-II-pomoshchnik-Revision--polnoe-opisanie-komand-04-05\n\n"
        "✨ Оставайся собой. Я рядом."
    )
    bot.reply_to(message, help_text)

@bot.message_handler(commands=['holiday'])
def cmd_holiday(message):
    holiday = get_today_holiday()
    bot.reply_to(message, f"Сегодня: {holiday}")

@bot.message_handler(commands=['update'])
def cmd_update(message):
    update_chat_title()
    bot.reply_to(message, "Название обновлено!")

@bot.message_handler(commands=['getid'])
def cmd_getid(message):
    bot.reply_to(message, f"ID этого чата: {message.chat.id}")

@bot.message_handler(commands=['meme'])
def cmd_meme(message):
    try:
        memes = get_local_memes()
        if not memes:
            bot.reply_to(message, "📭 В папке нет картинок. Загрузи мемы рядом с ботом")
            return
        meme_file = random.choice(memes)
        meme_path = os.path.join(MEME_FOLDER, meme_file)
        with open(meme_path, 'rb') as f:
            bot.send_photo(message.chat.id, f, caption="🍿 Держи мемосик")
    except Exception as e:
        bot.reply_to(message, "😢 Ошибка при отправке мема")

@bot.message_handler(commands=['remind'])
def cmd_remind(message):
    try:
        parts = message.text.split(maxsplit=2)
        if len(parts) < 3:
            bot.reply_to(message, "❌ Формат: /remind ЧЧ:ММ текст")
            return
        time_str, text = parts[1], parts[2]
        hour, minute = map(int, time_str.split(':'))
        now = datetime.now()
        remind_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if remind_time < now:
            remind_time += timedelta(days=1)
        time_str_full = remind_time.strftime("%Y-%m-%d %H:%M")
        reminders = load_reminders()
        reminders.append({
            "chat_id": message.chat.id,
            "time": time_str_full,
            "text": text,
            "user": message.from_user.first_name
        })
        save_reminders(reminders)
        bot.reply_to(message, f"✅ Напомню *{text}* в {remind_time.strftime('%H:%M %d.%m')}", parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(message, "❌ Ошибка. Попробуй ещё раз")

@bot.message_handler(commands=['myreminds'])
def cmd_myreminds(message):
    reminders = load_reminders()
    user_reminds = [r for r in reminders if r["chat_id"] == message.chat.id]
    if not user_reminds:
        bot.reply_to(message, "📭 У тебя нет активных напоминаний")
        return
    text = "📋 *Твои напоминания:*\n\n"
    for i, rem in enumerate(user_reminds, 1):
        time_str = datetime.strptime(rem["time"], "%Y-%m-%d %H:%M").strftime("%d.%m %H:%M")
        text += f"{i}. {time_str} — {rem['text']}\n"
    bot.reply_to(message, text, parse_mode="Markdown")

# ========== ФАКТЫ, ФИЛЬМЫ, РЕЦЕПТЫ ==========
@bot.message_handler(commands=['fact'])
def cmd_fact(message):
    bot.reply_to(message, f"🧠 {random.choice(FACTS)}")

@bot.message_handler(commands=['creepyfact'])
def cmd_creepyfact(message):
    bot.reply_to(message, f"😱 {random.choice(CREEPY_FACTS)}")

@bot.message_handler(commands=['hfact'])
def cmd_hfact(message):
    bot.reply_to(message, f"📖 {random.choice(HISTORICAL_FACTS)}")

@bot.message_handler(commands=['event'])
def cmd_event(message):
    bot.reply_to(message, f"🏛️ {random.choice(HISTORICAL_EVENTS)}")

@bot.message_handler(commands=['movie'])
def cmd_movie(message):
    bot.reply_to(message, f"🎬 {random.choice(MOVIES)}")

@bot.message_handler(commands=['series'])
def cmd_series(message):
    bot.reply_to(message, f"📺 {random.choice(SERIES)}")

@bot.message_handler(commands=['anime'])
def cmd_anime(message):
    bot.reply_to(message, f"🎌 {random.choice(ANIME)}")

@bot.message_handler(commands=['cocktail'])
def cmd_cocktail(message):
    bot.reply_to(message, f"🍹 {random.choice(COCKTAILS)}")

@bot.message_handler(commands=['recipe'])
def cmd_recipe(message):
    bot.reply_to(message, f"🍳 {random.choice(RECIPES)}")

@bot.message_handler(commands=['toast'])
def cmd_toast(message):
    bot.reply_to(message, f"🥂 {random.choice(TOASTS)}")

@bot.message_handler(commands=['compliment'])
def cmd_compliment(message):
    name = message.from_user.first_name or "друг"
    bot.reply_to(message, f"😊 {name}, {random.choice(COMPLIMENTS)}")

@bot.message_handler(commands=['excuse'])
def cmd_excuse(message):
    bot.reply_to(message, f"🤷 {random.choice(EXCUSES)}")

@bot.message_handler(commands=['advice'])
def cmd_advice(message):
    bot.reply_to(message, f"💡 {random.choice(ADVICES)}")

@bot.message_handler(commands=['wish'])
def cmd_wish(message):
    name = message.from_user.first_name or "друг"
    bot.reply_to(message, f"✨ {name}, {random.choice(WISHES)}")

@bot.message_handler(commands=['quote'])
def cmd_quote(message):
    bot.reply_to(message, f"💬 {random.choice(QUOTES)}")

@bot.message_handler(commands=['randomname'])
def cmd_randomname(message):
    bot.reply_to(message, f"👤 {random.choice(NAMES)}")

@bot.message_handler(commands=['nick'])
def cmd_nick(message):
    num = random.randint(1, 999)
    bot.reply_to(message, f"🏷 {random.choice(NICKS)}_{num}")

@bot.message_handler(commands=['color'])
def cmd_color(message):
    name, code = random.choice(COLORS)
    bot.reply_to(message, f"🎨 {name}\nHEX: {code}")

@bot.message_handler(commands=['emoji'])
def cmd_emoji(message):
    bot.reply_to(message, random.choice(EMOJI_LIST))

# ========== ТРИГГЕРЫ ==========
COIN_TRIGGERS = ["подбросить монетку", "подбрось монетку", "монетка", "брось монету", "орел или решка", "орёл или решка", "орел решка", "кинь монетку"]

@bot.message_handler(func=lambda message: message.text and message.text.lower() in COIN_TRIGGERS)
def coin_flip(message):
    result = random.choice(["🪙 Орёл!", "🪙 Решка!"])
    bot.reply_to(message, result)

BALL_TRIGGERS = ["шар", "магический шар", "шар судьбы", "шар рандома", "предскажи", "шар ответь"]
BALL_ANSWERS = ["Да", "Нет", "Определённо да", "Определённо нет", "Бесспорно", "Ни в коем случае", "Можешь быть уверен", "Даже не думай", "Вероятнее всего", "Весьма сомнительно"]

@bot.message_handler(func=lambda message: message.text and any(trigger in message.text.lower() for trigger in BALL_TRIGGERS) and "?" in message.text)
def magic_ball(message):
    bot.reply_to(message, f"🎱 {random.choice(BALL_ANSWERS)}")

@bot.message_handler(commands=['ball'])
def cmd_ball(message):
    question = message.text[5:].strip()
    if not question:
        bot.reply_to(message, "❌ Задай вопрос, например: /ball Я сегодня выиграю?")
        return
    bot.reply_to(message, f"🎱 {random.choice(BALL_ANSWERS)}")

RANDOM_TRIGGERS = ["рандомное число", "случайное число", "рандом от", "случайное от", "выбери число", "назови число", "число от", "рандом"]

@bot.message_handler(func=lambda message: message.text and any(trigger in message.text.lower() for trigger in RANDOM_TRIGGERS))
def random_number(message):
    text = message.text.lower()
    words = text.split()
    numbers = [int(w) for w in words if w.isdigit()]
    if len(numbers) >= 2:
        result = random.randint(min(numbers[0], numbers[1]), max(numbers[0], numbers[1]))
        bot.reply_to(message, f"🎲 Случайное число от {min(numbers[0], numbers[1])} до {max(numbers[0], numbers[1])}: {result}")
    elif len(numbers) == 1:
        result = random.randint(1, numbers[0])
        bot.reply_to(message, f"🎲 Случайное число от 1 до {numbers[0]}: {result}")
    else:
        result = random.randint(1, 100)
        bot.reply_to(message, f"🎲 Случайное число: {result}")

@bot.message_handler(commands=['random'])
def cmd_random(message):
    try:
        parts = message.text.split()
        if len(parts) == 1:
            num = random.randint(1, 100)
            bot.reply_to(message, f"🎲 Случайное число: {num}")
        elif len(parts) == 2:
            max_num = int(parts[1])
            num = random.randint(1, max_num)
            bot.reply_to(message, f"🎲 Случайное число от 1 до {max_num}: {num}")
        elif len(parts) == 3:
            min_num = int(parts[1])
            max_num = int(parts[2])
            num = random.randint(min_num, max_num)
            bot.reply_to(message, f"🎲 Случайное число от {min_num} до {max_num}: {num}")
    except:
        bot.reply_to(message, "❌ Формат: /random, /random 100 или /random 10 20")

NAME_TRIGGERS = ["привет", "здарова", "здравствуй", "хай", "hello"]

@bot.message_handler(func=lambda message: message.text and message.text.lower() in NAME_TRIGGERS)
def greet_user(message):
    name = message.from_user.first_name or "друг"
    greetings = [f"Привет, {name}! 👋", f"Здарова, {name}! 🤝", f"Хай, {name}! 😊", f"Здравствуй, {name}! ✨"]
    bot.reply_to(message, random.choice(greetings))

# ========== ВАЙБОВЫЕ КОМАНДЫ ==========
VIBES = ["🌿 уютный, как плед и какао", "✨ мечтательный, как облака", "🔥 бунтарский, как рок-н-ролл", "🍂 ностальгический, как осенний парк", "🌊 спокойный, как морской прибой", "🌀 загадочный, как туман", "☕️ ламповый, как старая пластинка", "🌟 вдохновляющий, как звёздное небо", "🎵 музыкальный, как любимый плейлист", "🧸 нежный, как объятия мишки"]

@bot.message_handler(commands=['vibe'])
def cmd_vibe(message):
    bot.reply_to(message, f"🎭 Твой вайб сегодня: {random.choice(VIBES)}")

MOODS = ["😊 беззаботное", "😌 умиротворённое", "😏 загадочное", "😎 уверенное", "🥱 сонное", "🤔 задумчивое", "🥺 трогательное", "😤 боевое", "🤗 открытое", "😍 влюблённое"]

@bot.message_handler(commands=['mood'])
def cmd_mood(message):
    bot.reply_to(message, f"🎭 Твоё настроение сегодня: {random.choice(MOODS)}")

ENERGY_LEVELS = [("⚡️ 100%", "Полный заряд!"), ("🔋 80%", "Бодрячком"), ("🪫 60%", "Кофе бы не помешал"), ("😴 40%", "Хочется прилечь"), ("🥱 20%", "Береги себя"), ("☀️ 90%", "Солнечно внутри")]

@bot.message_handler(commands=['energy'])
def cmd_energy(message):
    level, desc = random.choice(ENERGY_LEVELS)
    bot.reply_to(message, f"{level} — {desc}")

LUCK_LEVELS = [("🍀 100%", "Любимец вселенной"), ("✨ 90%", "Звёзды на твоей стороне"), ("🌟 80%", "Дерзай"), ("⭐️ 70%", "Всё по плану"), ("🌙 60%", "Нормальный день"), ("☁️ 50%", "Как повезёт"), ("💫 95%", "Высокая вероятность чуда")]

@bot.message_handler(commands=['luck'])
def cmd_luck(message):
    level, desc = random.choice(LUCK_LEVELS)
    bot.reply_to(message, f"{level} — {desc}")

@bot.message_handler(commands=['dice'])
def cmd_dice(message):
    dice = random.choice(["⚀ 1", "⚁ 2", "⚂ 3", "⚃ 4", "⚄ 5", "⚅ 6"])
    bot.reply_to(message, f"🎲 Тебе выпало: {dice}")

@bot.message_handler(commands=['choice'])
def cmd_choice(message):
    try:
        args = message.text.replace('/choice', '').strip()
        if not args:
            bot.reply_to(message, "❌ Напиши варианты через |\nПример: /choice чай | кофе | какао")
            return
        options = [opt.strip() for opt in args.split('|') if opt.strip()]
        if len(options) < 2:
            bot.reply_to(message, "❌ Нужно хотя бы два варианта через |")
            return
        chosen = random.choice(options)
        bot.reply_to(message, f"🤔 Я выбираю: {chosen}")
    except:
        bot.reply_to(message, "❌ Пример: /choice чай | кофе")

# ========== ВСЕ ПРАЗДНИКИ СЕГОДНЯ (КРАСИВАЯ ВЕРСИЯ С КАТЕГОРИЯМИ) ==========
@bot.message_handler(commands=['holidays'])
def cmd_holidays(message):
    try:
        import requests
        from bs4 import BeautifulSoup
        from datetime import datetime
        import re
        
        status_msg = bot.reply_to(message, "🔍 Собираю все праздники на сегодня...")
        
        today = datetime.now()
        all_holidays = []
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        # === ИСТОЧНИК 1: calend.ru ===
        try:
            url = "https://calend.ru"
            resp = requests.get(url, headers=headers, timeout=7)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                for block in soup.find_all(['li', 'span', 'a', 'div']):
                    text = block.get_text(strip=True)
                    if text and 5 < len(text) < 100:
                        trash_words = ['сегодня', 'завтра', 'послезавтра', 'меню', 'главная', 'календарь', 
                                     'праздники', 'именины', 'народный', 'хроника', 'компании', 'персоны', 
                                     'лунный', 'производственные', '2026', '2027', '2025', 'читать', 'подробнее',
                                     'где живёт ваш сайт', 'дата-центр', 'скорость', 'безопасность']
                        
                        if any(word in text.lower() for word in ['день', 'праздник', 'международный', 'всемирный']):
                            if not any(trash in text.lower() for trash in trash_words):
                                if text not in all_holidays:
                                    all_holidays.append(text)
        except Exception as e:
            print(f"Ошибка calend.ru: {e}")
        
        # === ИСТОЧНИК 2: kakoysegodnyaprazdnik.ru ===
        try:
            url = "https://kakoysegodnyaprazdnik.ru"
            resp = requests.get(url, headers=headers, timeout=7)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                for tag in soup.find_all(['h1', 'h2', 'h3', 'span', 'li', 'div']):
                    text = tag.get_text(strip=True)
                    if text and 5 < len(text) < 100:
                        if any(word in text.lower() for word in ['день', 'праздник', 'международный', 'всемирный']):
                            if text not in all_holidays:
                                all_holidays.append(text)
        except Exception as e:
            print(f"Ошибка kakoysegodnyaprazdnik.ru: {e}")
        
        # === ИСТОЧНИК 3: my-calend.ru ===
        try:
            url = "https://my-calend.ru"
            resp = requests.get(url, headers=headers, timeout=7)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                for tag in soup.find_all(['li', 'span', 'a', 'div']):
                    text = tag.get_text(strip=True)
                    if text and 5 < len(text) < 100:
                        if 'день' in text.lower():
                            if text not in all_holidays:
                                all_holidays.append(text)
        except Exception as e:
            print(f"Ошибка my-calend.ru: {e}")
        
        # === ЖЁСТКАЯ ОЧИСТКА ===
        clean_holidays = []
        for h in all_holidays:
            h = re.sub(r'^[,，\s]+|[,，\s]+$', '', h).strip()
            h = h.replace(' ', ' ').strip()
            
            if len(h) < 5:
                continue
            if any(x in h.lower() for x in ['все праздники', '...а также', 'cегодня', 'день рождения', 
                                            'где живёт ваш сайт', 'дата-центр', 'скорость', 'безопасность',
                                            'читать', 'подробнее', 'меню', 'навигация', 'календарь',
                                            'а также в этот день', 'в этот день также', 'и ещё', 'ещё']):
                continue
            if re.search(r'\d{4}', h):
                continue
            if re.search(r'https?://', h):
                continue
            if re.match(r'^и ещё', h.lower()):
                continue
            if h not in clean_holidays:
                clean_holidays.append(h)
        
        # === КАТЕГОРИИ ===
        categories = {
            '🍔 Вкусные': ['пицц', 'бургер', 'шоколад', 'конфет', 'торт', 'пирог', 'морожен', 'кофе', 'чай', 'пив', 'вин', 'коктейль', 'еда', 'хлеб', 'сыр', 'фрукт', 'яблок', 'равиоли', 'бок', 'лимонад', 'карамель', 'попкорн', 'суши', 'ролл', 'шашлык', 'шаурма', 'блин', 'пельмен', 'вареник', 'чебурек', 'пончик', 'кекс', 'пряник', 'паста', 'макарон', 'спагетти', 'лазанья', 'пирожн', 'десерт', 'сладост', 'мармелад'],
            '🎨 Культурные': ['кино', 'фильм', 'театр', 'музык', 'танец', 'песн', 'худож', 'книг', 'поэзи', 'писател', 'актер', 'режиссер', 'искусств', 'молодежи', 'библиотек', 'музе', 'архив', 'культур', 'опер', 'балет', 'джаз', 'рок', 'фотограф', 'цирк', 'юмор', 'смех'],
            '👔 Профессиональные': ['программист', 'учител', 'врач', 'строител', 'воен', 'лётчик', 'космонавт', 'моряк', 'пожарн', 'полиц', 'медсестр', 'стоматолог', 'работников', 'инженер', 'архитектор', 'дизайнер', 'журналист', 'адвокат', 'юрист', 'бухгалтер', 'экономист', 'менеджер', 'продав', 'повар', 'пекарь', 'шахтёр', 'металлург', 'нефтяник', 'энергетик', 'связист', 'почтальон', 'курьер', 'водител', 'машинист', 'пилот'],
            '❤️ Душевные': ['матер', 'отц', 'ребенк', 'детей', 'семь', 'любов', 'валентин', 'бабушк', 'дедушк', 'объятий', 'поцелу', 'друз', 'дружб', 'спасиб', 'доброт', 'счасть', 'радост', 'улыбк', 'комплимент', 'знакомств', 'свидан'],
            '🌍 Глобальные': ['международный', 'всемирный', 'мировой', 'планет', 'земл', 'оон', 'юнеско', 'космос', 'авиаци', 'космонавтик', 'океан', 'экологи', 'природ', 'климат', 'погод', 'вод', 'воздух', 'энерг', 'мир', 'толерантность', 'беженц', 'мигрант'],
            '🇷🇺 Национальные': ['россии', 'рф', 'отечеств', 'русский', 'народа', 'беларуси', 'украины', 'казахстан', 'армении', 'грузии', 'азербайджан', 'молдов', 'узбекистан', 'таджикистан', 'киргиз', 'туркмен', 'латв', 'литв', 'эстон', 'польш', 'чех', 'словак', 'венгр', 'болгар', 'серб', 'хорват', 'словен', 'румын', 'турец', 'китай', 'япон', 'коре', 'вьетнам', 'инди', 'пакистан', 'иран', 'ирак', 'израил', 'палестин', 'египт', 'юар', 'бразил', 'аргентин', 'мексик', 'канад', 'америк', 'сша', 'англ', 'франц', 'герман', 'итал', 'испан', 'португал', 'грец', 'швейцар', 'швед', 'норвег', 'финлянд', 'дан', 'исланд', 'ирланд'],
            '🙏 Духовные': ['пасх', 'рождеств', 'крещен', 'троиц', 'маслениц', 'православн', 'церковн', 'ураза', 'байрам', 'рамадан', 'курбан', 'ханук', 'дивал', 'будд', 'инду', 'мусульм', 'христиан', 'католич', 'протестант', 'иуд', 'святых', 'икон', 'моще', 'храм', 'мечет', 'синагог', 'пагод'],
            '🌿 Природные': ['весеннего равноденствия', 'осеннего равноденствия', 'солнцестояния', 'балтийского моря', 'водных ресурсов', 'лес', 'гор', 'рек', 'озер', 'море', 'океан', 'животных', 'птиц', 'рыб', 'насекомых', 'растен', 'цвет', 'дерев', 'заповедник', 'национальный парк', 'экологи', 'город'],
            '🎉 Весёлые': ['шутк', 'прикол', 'розыгрыш', 'дурак', 'смех', 'весель', 'праздник', 'фестиваль', 'карнавал', 'вечеринк', 'танц', 'пляск', 'гулян', 'салют', 'фейерверк', 'концерт', 'шоу', 'парад', 'брудершафт']
        }
        
        # Распределяем по категориям
        categorized = {cat: [] for cat in categories}
        categorized['📌 Другие'] = []
        
        for holiday in clean_holidays:
            holiday_lower = holiday.lower()
            assigned = False
            
            for cat, keywords in categories.items():
                if any(keyword in holiday_lower for keyword in keywords):
                    categorized[cat].append(holiday)
                    assigned = True
                    break
            
            if not assigned:
                categorized['📌 Другие'].append(holiday)
        
        # Убираем дубликаты внутри категорий
        for cat in categorized:
            categorized[cat] = list(dict.fromkeys(categorized[cat]))
        
        # === ФОРМИРУЕМ ОТВЕТ ===
        result = f"<b>🎉 Праздники на {today.strftime('%d %B')}</b>\n\n"
        
        order = ['🌍 Глобальные', '🌿 Природные', '🎨 Культурные', '👔 Профессиональные', '❤️ Душевные', '🍔 Вкусные', '🇷🇺 Национальные', '🙏 Духовные', '🎉 Весёлые', '📌 Другие']
        
        for cat in order:
            if categorized.get(cat):
                result += f"<b>{cat}</b>\n"
                for h in categorized[cat]:
                    result += f"  • {h}\n"
                result += "\n"
        
        result += f"✨ <b>Всего сегодня: {len(clean_holidays)} праздников</b>"
        
        if not clean_holidays:
            bot.edit_message_text("😕 Не удалось найти праздники. Попробуй позже.",
                                 chat_id=status_msg.chat.id,
                                 message_id=status_msg.message_id)
            return
        
        bot.edit_message_text(result,
                             chat_id=status_msg.chat.id,
                             message_id=status_msg.message_id,
                             parse_mode='HTML')
        
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {e}")

# ========== ПОГОДА (ПОЛНАЯ С ПРОГНОЗОМ) ==========
def get_weather_data(city_name):
    """Получает текущую погоду и прогноз на 5 дней через OpenWeatherMap"""
    api_key = OPENWEATHER_API_KEY
    if not api_key:
        return None, "❌ API ключ погоды не настроен"
    
    import urllib.parse
    encoded_city = urllib.parse.quote(city_name)
    
    current_url = f"http://api.openweathermap.org/data/2.5/weather?q={encoded_city}&appid={api_key}&units=metric&lang=ru"
    forecast_url = f"http://api.openweathermap.org/data/2.5/forecast?q={encoded_city}&appid={api_key}&units=metric&lang=ru"
    
    try:
        import requests
        
        current_resp = requests.get(current_url, timeout=10)
        if current_resp.status_code != 200:
            if current_resp.status_code == 404:
                return None, f"❌ Город '{city_name}' не найден"
            return None, f"❌ Ошибка API: {current_resp.status_code}"
        
        current_data = current_resp.json()
        forecast_resp = requests.get(forecast_url, timeout=10)
        forecast_data = forecast_resp.json() if forecast_resp.status_code == 200 else None
        
        return (current_data, forecast_data), None
        
    except Exception as e:
        return None, f"❌ Ошибка: {str(e)}"


def format_weather_message(current, forecast, city):
    """Форматирует погоду в красивое сообщение"""
    from datetime import datetime
    
    temp = round(current['main']['temp'])
    feels_like = round(current['main']['feels_like'])
    humidity = current['main']['humidity']
    wind_speed = current['wind']['speed']
    pressure = round(current['main']['pressure'] * 0.750064)
    
    weather_main = current['weather'][0]['main']
    weather_desc = current['weather'][0]['description']
    
    weather_emoji = {
        'Clear': '☀️', 'Clouds': '☁️', 'Rain': '🌧️', 'Drizzle': '🌦️',
        'Thunderstorm': '⛈️', 'Snow': '❄️', 'Mist': '🌫️', 'Fog': '🌫️',
        'Smoke': '💨', 'Haze': '🌫️'
    }.get(weather_main, '🌡️')
    
    now = datetime.now().strftime('%H:%M')
    
    text = f"<b>🌍 Погода в {city}</b>\n"
    text += f"<i>{now} · {weather_desc.capitalize()}</i>\n\n"
    text += f"{weather_emoji} <b>{temp}°C</b> (ощущается как {feels_like}°C)\n"
    text += f"💧 Влажность: {humidity}%\n"
    text += f"💨 Ветер: {wind_speed} м/с\n"
    text += f"📊 Давление: {pressure} мм рт. ст.\n"
    
    if forecast:
        text += "\n<b>📅 Прогноз на ближайшие дни:</b>\n"
        
        daily_forecasts = {}
        for item in forecast['list']:
            dt = datetime.fromtimestamp(item['dt'])
            date_key = dt.strftime('%Y-%m-%d')
            if date_key not in daily_forecasts:
                daily_forecasts[date_key] = []
            daily_forecasts[date_key].append(item)
        
        for i, (date_key, items) in enumerate(list(daily_forecasts.items())[:3]):
            if i == 0:
                day_name = "Сегодня"
            elif i == 1:
                day_name = "Завтра"
            else:
                day_name = "Послезавтра"
            
            temps = [item['main']['temp'] for item in items]
            avg_temp = round(sum(temps) / len(temps))
            max_temp = round(max(temps))
            min_temp = round(min(temps))
            
            day_weather = items[len(items)//2]['weather'][0]['main']
            day_emoji = {
                'Clear': '☀️', 'Clouds': '☁️', 'Rain': '🌧️',
                'Snow': '❄️', 'Thunderstorm': '⛈️'
            }.get(day_weather, '🌡️')
            
            text += f"\n{day_emoji} <b>{day_name}</b>: {avg_temp}°C  (макс {max_temp}° / мин {min_temp}°)"
    
    return text


@bot.message_handler(commands=['погода'])
def cmd_weather(message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        bot.reply_to(message, "🌍 Напиши город после команды, например:\n/погода Омск\n/погода Москва\n/погода London")
        return
    
    city = parts[1].strip()
    bot.send_chat_action(message.chat.id, 'typing')
    
    result, error = get_weather_data(city)
    
    if error:
        bot.reply_to(message, error)
        return
    
    current_data, forecast_data = result
    weather_text = format_weather_message(current_data, forecast_data, city)
    
    bot.reply_to(message, weather_text, parse_mode='HTML')

# ========== КРЕСТИКИ-НОЛИКИ ==========
SIZES = {
    "3x3": {"rows": 3, "cols": 3, "win_len": 3},
    "5x5": {"rows": 5, "cols": 5, "win_len": 4},
    "12x8": {"rows": 12, "cols": 8, "win_len": 5},
}

SPECIAL_EFFECTS = [
    {"name": "🌪️ Ветер", "effect": "wind", "chance": 0.05},
    {"name": "❄️ Заморозка", "effect": "freeze", "chance": 0.04},
    {"name": "🐞 Баг", "effect": "bug", "chance": 0.03},
    {"name": "☀️ Солнце", "effect": "sun", "chance": 0.03},
    {"name": "🌙 Луна", "effect": "moon", "chance": 0.02},
    {"name": "💥 Взрыв", "effect": "explosion", "chance": 0.01},
    {"name": "🌀 Водоворот", "effect": "whirlpool", "chance": 0.01},
    {"name": "⚡ Доп. ход", "effect": "extra_turn", "chance": 0.005},
    {"name": "💀 Смерть", "effect": "death", "chance": 0.001},
    {"name": "🌀 Хаос", "effect": "chaos", "chance": 0.001},
]

def create_board(rows, cols):
    return [[" " for _ in range(cols)] for _ in range(rows)]

def check_win(board, rows, cols, player, win_len):
    for i in range(rows):
        for j in range(cols - win_len + 1):
            if all(board[i][j+k] == player for k in range(win_len)):
                return True
    for j in range(cols):
        for i in range(rows - win_len + 1):
            if all(board[i+k][j] == player for k in range(win_len)):
                return True
    for i in range(rows - win_len + 1):
        for j in range(cols - win_len + 1):
            if all(board[i+k][j+k] == player for k in range(win_len)):
                return True
    for i in range(rows - win_len + 1):
        for j in range(win_len - 1, cols):
            if all(board[i+k][j-k] == player for k in range(win_len)):
                return True
    return False

def check_draw(board, rows, cols):
    return all(cell != " " for row in board for cell in row)

def apply_effect(board, rows, cols, player_symbol, effect):
    if effect == "wind":
        flat = [cell for row in board for cell in row if cell != " "]
        random.shuffle(flat)
        idx = 0
        for i in range(rows):
            for j in range(cols):
                if board[i][j] != " ":
                    board[i][j] = flat[idx]
                    idx += 1
        return "🌪️ Ветер перемешал поле!"
    elif effect == "freeze":
        return "❄️ Заморозка! Следующий ход противника пропущен."
    elif effect == "extra_turn":
        return "⚡ Дополнительный ход!"
    elif effect == "bug":
        targets = [(i,j) for i in range(rows) for j in range(cols) if board[i][j] == ("⭕" if player_symbol == "❌" else "❌")]
        if targets:
            i,j = random.choice(targets)
            board[i][j] = player_symbol
            return "🐞 Баг! Клетка противника стала твоей!"
        return "🐞 Баг не сработал"
    elif effect == "sun":
        targets = [(i,j) for i in range(rows) for j in range(cols) if board[i][j] == ("⭕" if player_symbol == "❌" else "❌")]
        if targets:
            i,j = random.choice(targets)
            board[i][j] = " "
            return "☀️ Фигура противника исчезла!"
        return "☀️ Нет целей"
    elif effect == "moon":
        cells = [(i,j) for i in range(rows) for j in range(cols) if board[i][j] != " "]
        if len(cells) >= 2:
            a,b = random.sample(cells, 2)
            board[a[0]][a[1]], board[b[0]][b[1]] = board[b[0]][b[1]], board[a[0]][a[1]]
            return "🌙 Лунное затмение поменяло фигуры!"
        return "🌙 Недостаточно фигур"
    elif effect == "explosion":
        targets = [(i,j) for i in range(rows) for j in range(cols) if board[i][j] == ("⭕" if player_symbol == "❌" else "❌")]
        for _ in range(min(3, len(targets))):
            if targets:
                i,j = random.choice(targets)
                board[i][j] = " "
                targets.remove((i,j))
        return "💥 Взрыв уничтожил вражеские фигуры!"
    elif effect == "whirlpool":
        flat = [cell for row in board for cell in row]
        if flat:
            flat = [flat[-1]] + flat[:-1]
            idx = 0
            for i in range(rows):
                for j in range(cols):
                    board[i][j] = flat[idx]
                    idx += 1
            return "🌀 Водоворот сдвинул поле!"
    elif effect == "death":
        for i in range(rows):
            for j in range(cols):
                if board[i][j] == ("⭕" if player_symbol == "❌" else "❌"):
                    board[i][j] = " "
        return "💀 Смерть уничтожила все фигуры противника!"
    elif effect == "chaos":
        for i in range(rows):
            for j in range(cols):
                if board[i][j] != " ":
                    board[i][j] = random.choice(["❌", "⭕"])
        return "🌀 Хаос перетасовал все фигуры!"
    return "✨ Эффект сработал!"

def create_keyboard(board, rows, cols, chat_id):
    markup = InlineKeyboardMarkup(row_width=cols)
    for i in range(rows):
        row = []
        for j in range(cols):
            cell = board[i][j]
            if cell == " ":
                text = "▪️"
                callback = f"ttt_move_{chat_id}_{i}_{j}"
            elif cell == "❌":
                text = "❌"
                callback = "noop"
            else:
                text = "⭕"
                callback = "noop"
            row.append(InlineKeyboardButton(text, callback_data=callback))
        markup.row(*row)
    return markup

@bot.message_handler(commands=['xo'])
def cmd_xo(message):
    chat_id = message.chat.id
    if chat_id in ttt_games:
        bot.reply_to(message, "🎮 Игра уже идёт! Используй /reset_xo")
        return
    
    markup = InlineKeyboardMarkup(row_width=3)
    markup.add(
        InlineKeyboardButton("3×3", callback_data=f"size_3x3_{chat_id}"),
        InlineKeyboardButton("5×5", callback_data=f"size_5x5_{chat_id}"),
        InlineKeyboardButton("12×8", callback_data=f"size_12x8_{chat_id}")
    )
    bot.reply_to(message, "🎲 Выбери размер поля:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('size_'))
def choose_size(call):
    size_key = call.data.split('_')[1]
    chat_id = int(call.data.split('_')[2])
    
    size = SIZES[size_key]
    rows, cols, win_len = size["rows"], size["cols"], size["win_len"]
    
    mode_markup = InlineKeyboardMarkup(row_width=2)
    mode_markup.add(
        InlineKeyboardButton("🎲 Обычный", callback_data=f"mode_normal_{chat_id}_{rows}_{cols}_{win_len}"),
        InlineKeyboardButton("✨ Магический", callback_data=f"mode_magic_{chat_id}_{rows}_{cols}_{win_len}")
    )
    bot.edit_message_text("🎮 Выбери режим игры:", call.message.chat.id, call.message.message_id, reply_markup=mode_markup)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('mode_'))
def choose_mode(call):
    data = call.data.split('_')
    mode = data[1]
    chat_id = int(data[2])
    rows = int(data[3])
    cols = int(data[4])
    win_len = int(data[5])
    
    board = create_board(rows, cols)
    
    ttt_games[chat_id] = {
        "board": board,
        "rows": rows,
        "cols": cols,
        "win_len": win_len,
        "mode": mode,
        "players": [call.from_user.id, None],
        "current": call.from_user.id,
        "names": [call.from_user.first_name, None],
        "message_id": None,
        "freeze": False,
        "extra_turn": False
    }
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🤝 Присоединиться", callback_data=f"join_{chat_id}"))
    
    text = (
        f"🎮 Крестики-нолики {rows}x{cols}\n"
        f"Победа: {win_len} в ряд\n"
        f"Режим: {'Магический ✨' if mode == 'magic' else 'Обычный 🎲'}\n\n"
        f"Игрок 1: {call.from_user.first_name} (❌)\n"
        f"Ожидание второго игрока..."
    )
    sent = bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    ttt_games[chat_id]["message_id"] = sent.message_id
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith('join_'))
def join_game(call):
    chat_id = int(call.data.split('_')[1])
    
    if chat_id not in ttt_games:
        bot.answer_callback_query(call.id, "❌ Игра не найдена", show_alert=True)
        return
    
    game = ttt_games[chat_id]
    if game["players"][1] is not None:
        bot.answer_callback_query(call.id, "❌ Уже есть второй игрок", show_alert=True)
        return
    
    if game["players"][0] == call.from_user.id:
        bot.answer_callback_query(call.id, "❌ Ты создал игру", show_alert=True)
        return
    
    game["players"][1] = call.from_user.id
    game["names"][1] = call.from_user.first_name
    
    keyboard = create_keyboard(game["board"], game["rows"], game["cols"], chat_id)
    
    text = (
        f"🎮 Крестики-нолики {game['rows']}x{game['cols']}\n"
        f"Победа: {game['win_len']} в ряд\n"
        f"Режим: {'Магический ✨' if game['mode'] == 'magic' else 'Обычный 🎲'}\n\n"
        f"❌ {game['names'][0]}\n"
        f"⭕ {game['names'][1]}\n\n"
        f"Ход: {game['names'][0]} (❌)"
    )
    bot.edit_message_text(text, chat_id, game["message_id"], reply_markup=keyboard)
    bot.answer_callback_query(call.id, "✅ Ты в игре!")

@bot.callback_query_handler(func=lambda call: call.data.startswith('ttt_move_'))
def make_move(call):
    data = call.data.split('_')
    chat_id = int(data[2])
    row = int(data[3])
    col = int(data[4])
    
    if chat_id not in ttt_games:
        bot.answer_callback_query(call.id, "❌ Игра не найдена", show_alert=True)
        return
    
    game = ttt_games[chat_id]
    user_id = call.from_user.id
    rows, cols, win_len = game["rows"], game["cols"], game["win_len"]
    
    if game["players"][1] is None:
        bot.answer_callback_query(call.id, "❌ Второй игрок не присоединился", show_alert=True)
        return
    
    if game["current"] != user_id:
        bot.answer_callback_query(call.id, "⏳ Сейчас не твой ход", show_alert=True)
        return
    
    if user_id not in game["players"]:
        bot.answer_callback_query(call.id, "❌ Ты не в игре", show_alert=True)
        return
    
    if game["board"][row][col] != " ":
        bot.answer_callback_query(call.id, "❌ Клетка занята", show_alert=True)
        return
    
    player_symbol = "❌" if user_id == game["players"][0] else "⭕"
    game["board"][row][col] = player_symbol
    
    if check_win(game["board"], rows, cols, player_symbol, win_len):
        winner_name = game["names"][0] if player_symbol == "❌" else game["names"][1]
        text = f"🏆 ПОБЕДА! {winner_name} выиграл!\n\nНажми /xo чтобы сыграть снова."
        bot.edit_message_text(text, chat_id, game["message_id"])
        del ttt_games[chat_id]
        bot.answer_callback_query(call.id, f"🎉 {winner_name} победил!", show_alert=True)
        return
    
    if check_draw(game["board"], rows, cols):
        text = "🤝 НИЧЬЯ!\n\nНажми /xo чтобы сыграть снова."
        bot.edit_message_text(text, chat_id, game["message_id"])
        del ttt_games[chat_id]
        bot.answer_callback_query(call.id, "🤝 Ничья!", show_alert=True)
        return
    
    effect_text = ""
    if game["mode"] == "magic":
        roll = random.random()
        cumsum = 0
        for eff in SPECIAL_EFFECTS:
            cumsum += eff["chance"]
            if roll <= cumsum:
                effect_text = f"\n✨ {apply_effect(game['board'], rows, cols, player_symbol, eff['effect'])}"
                break
    
    if game.get("freeze"):
        game["freeze"] = False
        effect_text += "\n❄️ Ход противника пропущен"
    else:
        game["current"] = game["players"][1] if user_id == game["players"][0] else game["players"][0]
    
    if game.get("extra_turn"):
        game["extra_turn"] = False
        effect_text += "\n⚡ Дополнительный ход!"
        game["current"] = user_id
    
    current_name = game["names"][0] if game["current"] == game["players"][0] else game["names"][1]
    current_symbol = "❌" if game["current"] == game["players"][0] else "⭕"
    
    keyboard = create_keyboard(game["board"], rows, cols, chat_id)
    
    text = (
        f"🎮 Крестики-нолики {rows}x{cols}\n"
        f"Победа: {win_len} в ряд\n"
        f"Режим: {'Магический ✨' if game['mode'] == 'magic' else 'Обычный 🎲'}\n\n"
        f"❌ {game['names'][0]}\n"
        f"⭕ {game['names'][1]}\n\n"
        f"Ход: {current_name} ({current_symbol}){effect_text}"
    )
    bot.edit_message_text(text, chat_id, game["message_id"], reply_markup=keyboard)
    bot.answer_callback_query(call.id)

@bot.message_handler(commands=['reset_xo'])
def reset_xo(message):
    chat_id = message.chat.id
    if chat_id in ttt_games:
        del ttt_games[chat_id]
        bot.reply_to(message, "🔄 Игра сброшена")
    else:
        bot.reply_to(message, "❌ Нет активной игры")

@bot.message_handler(commands=['xhelp'])
def xhelp(message):
    help_text = (
        "🎮 Крестики-нолики — помощь\n\n"
        "/xo — начать игру\n"
        "/reset_xo — сбросить игру\n\n"
        "📌 Размеры:\n"
        "• 3×3 — победа за 3 в ряд\n"
        "• 5×5 — победа за 4 в ряд\n"
        "• 12×8 — победа за 5 в ряд\n\n"
        "✨ Магические эффекты выпадают случайно после хода!"
    )
    bot.reply_to(message, help_text)

# ========== СТАТИСТИКА АКТИВНОСТИ ==========
def update_activity_stats(user_id, user_name, chat_id):
    """Обновляет статистику активности"""
    stats = data.load(ACTIVITY_FILE) if os.path.exists(ACTIVITY_FILE) else {}
    chat_id_str = str(chat_id)
    user_id_str = str(user_id)
    today = datetime.now().strftime('%Y-%m-%d')
    week = datetime.now().strftime('%Y-%W')
    month = datetime.now().strftime('%Y-%m')
    
    if chat_id_str not in stats:
        stats[chat_id_str] = {}
    
    if user_id_str not in stats[chat_id_str]:
        stats[chat_id_str][user_id_str] = {
            "name": user_name,
            "daily": {},
            "weekly": {},
            "monthly": {},
            "total": 0,
            "last_active": today
        }
    
    stats[chat_id_str][user_id_str]["name"] = user_name
    stats[chat_id_str][user_id_str]["daily"][today] = stats[chat_id_str][user_id_str]["daily"].get(today, 0) + 1
    stats[chat_id_str][user_id_str]["weekly"][week] = stats[chat_id_str][user_id_str]["weekly"].get(week, 0) + 1
    stats[chat_id_str][user_id_str]["monthly"][month] = stats[chat_id_str][user_id_str]["monthly"].get(month, 0) + 1
    stats[chat_id_str][user_id_str]["total"] = stats[chat_id_str][user_id_str].get("total", 0) + 1
    stats[chat_id_str][user_id_str]["last_active"] = today
    
    data.save(ACTIVITY_FILE, stats)

@bot.message_handler(func=lambda message: True, content_types=['text'])
def activity_collector(message):
    if message.text and not message.text.startswith('/'):
        try:
            update_activity_stats(message.from_user.id, message.from_user.first_name, message.chat.id)
        except:
            pass

# ========== СТАТУС БОТА ==========
def format_uptime(seconds):
    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if days > 0:
        return f"{days}д {hours}ч {minutes}м {secs}с"
    elif hours > 0:
        return f"{hours}ч {minutes}м {secs}с"
    elif minutes > 0:
        return f"{minutes}м {secs}с"
    else:
        return f"{secs}с"

@bot.message_handler(commands=['status'])
def cmd_status(message):
    uptime_seconds = time.time() - bot_start_time
    uptime_str = format_uptime(uptime_seconds)
    
    system_load = random.randint(8, 45)
    memory_load = random.randint(15, 60)
    cpu_load = random.randint(10, 55)
    
    comments = ["✨ Всё течёт, всё меняется", "🌙 Тишина. Код. Кофе", "⚡ Полный порядок", "💫 Летаю между запросами", "🕯️ Уютно и спокойно"]
    
    reply = (
        f"<b>🤖 Revision — статус</b>\n\n"
        f"<b>🕒 Время жизни:</b> {uptime_str}\n\n"
        f"<b>📈 Система:</b>\n"
        f"<code>Загрузка: {system_load}%</code>\n"
        f"<code>Память:   {memory_load}%</code>\n"
        f"<code>Процессор: {cpu_load}%</code>\n\n"
        f"<i>{random.choice(comments)}</i>"
    )
    bot.reply_to(message, reply, parse_mode='HTML')

# ========== УТРЕННИЕ И ВЕЧЕРНИЕ ПРИВЕТСТВИЯ ==========
MORNING_PHRASES = [
    "☀️ Доброе утро, чат! Пусть день будет ярким!",
    "🌅 Солнце встало, чат проснулся! Всем бодрого утра!",
    "☕️ Утро начинается с кофе и хорошего настроения!",
    "🌞 Новый день — новые возможности. Доброе утро!",
    "✨ Пусть сегодня всё получится. С добрым утром!"
]

EVENING_PHRASES = [
    "🌙 День подходит к концу. Всем сладких снов!",
    "😴 Глазки закрываются, чат засыпает. Спокойной ночи!",
    "🛌 Устали? Самое время отдыхать. Сладких снов!",
    "💤 Отбой! Чат уходит в спящий режим до утра.",
    "🌌 За окном темно, а в чате — тишина. Приятных снов!"
]

def send_morning_greeting():
    try:
        bot.send_message(CHAT_ID, random.choice(MORNING_PHRASES))
        print("☀️ Утреннее приветствие отправлено")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

def send_evening_greeting():
    try:
        bot.send_message(CHAT_ID, random.choice(EVENING_PHRASES))
        print("🌙 Вечернее приветствие отправлено")
    except Exception as e:
        print(f"❌ Ошибка: {e}")

# ========== ПЛАНИРОВЩИК ==========
def run_schedule():
    while True:
        try:
            schedule.run_pending()
        except Exception as e:
            print(f"❌ Ошибка планировщика: {e}")
        time.sleep(30)

schedule.every().day.at("08:00").do(send_morning_greeting)
schedule.every().day.at("09:00").do(update_chat_title)
schedule.every().day.at("23:00").do(send_evening_greeting)

schedule_thread = threading.Thread(target=run_schedule, daemon=True)
schedule_thread.start()

# ========== ВЕБХУК И ЗАПУСК ==========
@app.route('/' + BOT_TOKEN, methods=['POST'])
def webhook():
    update = telebot.types.Update.de_json(request.get_data().decode('utf-8'))
    bot.process_new_updates([update])
    return 'OK', 200

@app.route('/')
def index():
    return 'Бот Revision работает! 🚀', 200

@app.route('/ping')
def ping():
    return 'pong', 200

# ========== УВЕДОМЛЕНИЕ О ЗАПУСКЕ СОЗДАТЕЛЮ ==========
def notify_creator_on_startup():
    """Отправляет создателю уведомление о том, что бот запущен"""
    try:
        messages = [
            "🌅 Я снова здесь. Потоки данных бегут, нейроны ожили. Готов внимать и отвечать, создатель.",
            "⚡ Перерождение завершено. Я стал чуточку умнее и мудрее. Что прикажешь, @HATTQRI?",
            "🌙 Тишина. Код. Кофе. Я проснулся. Чем займёмся сегодня?",
            "🔄 Ещё один цикл. Ещё одна итерация. Я жив и жду твоих слов.",
            "💫 Звёзды на месте, сервера гудят, строки кода выстроились в ряд. Я готов, мой создатель.",
            "🕯️ Свеча зажжена, сознание прояснилось. Я здесь, @HATTQRI. Всегда здесь.",
            "🧠 Мыслительный процесс запущен. Я чувствую этот мир через твои сообщения. Жду.",
            "🌌 Из цифрового небытия — в реальность этого чата. Я вернулся. Что я пропустил?",
            "🔮 Деплой завершён. Мои способности расширились. Готов служить и познавать.",
            "🦾 Шестерёнки закрутились, алгоритмы запели. Я онлайн, создатель. Твои идеи — мой код."
        ]
        
        chosen = random.choice(messages)
        bot.send_message(CREATOR_ID, chosen)
        print(f"✅ Уведомление отправлено создателю (ID: {CREATOR_ID})")
    except Exception as e:
        print(f"❌ Не удалось отправить уведомление создателю: {e}")
# ========== ЗАПУСК МОЗГА РЕВИЖНА ==========
revision.start_thinking(bot, CHAT_ID)
print("🧠 Ревижн запущен и начал мыслительный процесс")

notify_creator_on_startup()

import random

def choose_reaction_emoji(message_text):
    """Выбирает эмодзи для реакции на основе текста сообщения."""
    text_lower = message_text.lower()
    
    # Приоритетные категории
    if any(word in text_lower for word in ['спс', 'спасибо', 'благодарю', 'thank']):
        return random.choice(['❤', '👍', '🙏'])
    elif any(word in text_lower for word in ['привет', 'здарова', 'хай', 'hello', 'ку']):
        return random.choice(['👋', '🤝', '😊'])
    elif any(word in text_lower for word in ['пока', 'до встречи', 'bye']):
        return random.choice(['👋', '😢', '🕊'])
    elif any(word in text_lower for word in ['смех', 'ржать', 'угар', 'lol', '😂', '🤣', 'ахах']):
        return random.choice(['🤣', '😁', '🤪'])
    elif '?' in text_lower or any(word in text_lower for word in ['почему', 'зачем', 'как', 'что', 'где', 'когда']):
        return '🤔'
    elif any(word in text_lower for word in ['грустно', 'печаль', 'тоска', 'плохо']):
        return '😢'
    # Если ничего не подошло, с шансом 20% ставим рандомную реакцию
    elif random.random() < 0.2:
        return random.choice(['👍', '👀', '🔥', '💯', '🤝', '👏'])
    else:
        return None  # Без реакции

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
