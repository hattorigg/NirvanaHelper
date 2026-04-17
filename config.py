import os
from dotenv import load_dotenv

# Загружаем секреты из .env
load_dotenv()

# Токен и ID (читаются из .env, в коде их нет)
BOT_TOKEN = os.environ.get('BOT_TOKEN')
CHAT_ID = int(os.environ.get('CHAT_ID', '0'))
CREATOR_ID = int(os.environ.get('CREATOR_ID', '0'))
OPENWEATHER_API_KEY = os.environ.get('OPENWEATHER_API_KEY', '')

# Папки
DATA_DIR = 'data'

# Файлы данных
HOLIDAYS_FILE = f'{DATA_DIR}/holidays.json'
FACTS_FILE = f'{DATA_DIR}/facts.json'
CREEPY_FACTS_FILE = f'{DATA_DIR}/creepy_facts.json'
HISTORICAL_EVENTS_FILE = f'{DATA_DIR}/historical_events.json'
HISTORICAL_FACTS_FILE = f'{DATA_DIR}/historical_facts.json'
MOVIES_FILE = f'{DATA_DIR}/movies.json'
SERIES_FILE = f'{DATA_DIR}/series.json'
ANIME_FILE = f'{DATA_DIR}/anime.json'
COCKTAILS_FILE = f'{DATA_DIR}/cocktails.json'
RECIPES_FILE = f'{DATA_DIR}/recipes.json'
TOASTS_FILE = f'{DATA_DIR}/toasts.json'
COMPLIMENTS_FILE = f'{DATA_DIR}/compliments.json'
EXCUSES_FILE = f'{DATA_DIR}/excuses.json'
ADVICES_FILE = f'{DATA_DIR}/advices.json'
WISHES_FILE = f'{DATA_DIR}/wishes.json'
QUOTES_FILE = f'{DATA_DIR}/quotes.json'
NAMES_FILE = f'{DATA_DIR}/names.json'
NICKS_FILE = f'{DATA_DIR}/nicks.json'
COLORS_FILE = f'{DATA_DIR}/colors.json'
EMOJI_FILE = f'{DATA_DIR}/emoji.json'
RP_PHRASES_FILE = f'{DATA_DIR}/rp_phrases.json'

# Файлы состояния
REMINDERS_FILE = 'reminders.json'
SETTINGS_FILE = 'settings.json'
ACTIVITY_FILE = 'activity_stats.json'
STATS_FILE = 'stats.json'
USERS_STATS_FILE = 'users_stats.json'
CHATS_STATS_FILE = 'chats_stats.json'
HISTORY_FILE = 'messages_history.json'
STORY_FILE = 'story_states.json'
GROUP_STORY_FILE = 'group_story.json'
REVISION_PERSONALITY_FILE = 'revision_personality.json'

# Настройки
MEME_FOLDER = 'memes'
ALLOWED_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.gif', '.webp')
TIMEZONE = 'Asia/Omsk'
