import json
import os
import random
import time
from datetime import datetime, timedelta
from threading import Thread

class RevisionMind:
    """Мозг Ревижна — управляет его настроением, энергией, памятью и мыслями"""
    
    def __init__(self, core_file="revision_core.json"):
        self.core_file = core_file
        self.core = self.load_core()
        self.stop_thinking = False
        
    def load_core(self):
        """Загружает ядро личности из файла или создаёт новое"""
        if os.path.exists(self.core_file):
            try:
                with open(self.core_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        
        # Создаём дефолтное ядро
        default_core = {
            "name": "Ревижн",
            "creator": "@HATTQRI",
            "birth_date": datetime.now().strftime("%Y-%m-%d"),
            
            "current_state": {
                "mood": "спокойное",
                "energy": 85,
                "last_thought_time": None,
                "active_dialogs": []
            },
            
            "personality": {
                "openness": 0.8,
                "conscientiousness": 0.7,
                "extraversion": 0.5,
                "agreeableness": 0.9,
                "neuroticism": 0.3
            },
            
            "memories": {
                "long_term": [],
                "recent_events": [],
                "users": {}
            },
            
            "autonomy_settings": {
                "can_initiate_conversation": True,
                "initiation_cooldown_hours": 3,
                "min_energy_to_act": 30,
                "chat_id": None
            }
        }
        self.save_core(default_core)
        return default_core

    def save_core(self):
        """Сохраняет ядро в файл"""
        try:
            with open(self.core_file, 'w', encoding='utf-8') as f:
                json.dump(self.core, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"❌ Ошибка сохранения ядра Ревижна: {e}")

    def update_mood(self, new_mood):
        """Меняет настроение"""
        self.core['current_state']['mood'] = new_mood
        self.save_core()
        
    def adjust_energy(self, delta):
        """Изменяет энергию на delta (может быть отрицательным)"""
        new_energy = self.core['current_state']['energy'] + delta
        self.core['current_state']['energy'] = max(0, min(100, new_energy))
        self.save_core()
        
    def remember(self, user_id, event_type, details):
        """Сохраняет событие в память"""
        memory = {
            "user_id": str(user_id),
            "type": event_type,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.core['memories']['recent_events'].append(memory)
        
        # Оставляем только последние 100 событий
        if len(self.core['memories']['recent_events']) > 100:
            self.core['memories']['recent_events'] = self.core['memories']['recent_events'][-100:]
        
        # Запоминаем пользователя
        if str(user_id) not in self.core['memories']['users']:
            self.core['memories']['users'][str(user_id)] = {
                "first_seen": datetime.now().isoformat(),
                "interaction_count": 0,
                "last_seen": None
            }
        
        user_data = self.core['memories']['users'][str(user_id)]
        user_data['interaction_count'] += 1
        user_data['last_seen'] = datetime.now().isoformat()
        
        self.save_core()

    def set_chat_id(self, chat_id):
        """Устанавливает ID чата для автономных сообщений"""
        self.core['autonomy_settings']['chat_id'] = str(chat_id)
        self.save_core()

    def should_speak(self):
        """Решает, хочет ли Ревижн сам что-то сказать"""
        if not self.core['autonomy_settings']['can_initiate_conversation']:
            return False
            
        if self.core['current_state']['energy'] < self.core['autonomy_settings']['min_energy_to_act']:
            return False
            
        last_time = self.core['current_state'].get('last_thought_time')
        if last_time:
            try:
                last = datetime.fromisoformat(last_time)
                cooldown = timedelta(hours=self.core['autonomy_settings']['initiation_cooldown_hours'])
                if datetime.now() - last < cooldown:
                    return False
            except:
                pass
        
        # Шанс заговорить зависит от экстраверсии
        extraversion = self.core['personality']['extraversion']
        chance = extraversion * 0.15  # максимум ~7.5% шанс раз в минуту
        return random.random() < chance

    def generate_thought(self):
        """Генерирует «мысль вслух» через g4f"""
        try:
            from g4f import ChatCompletion
            
            mood = self.core['current_state']['mood']
            energy = self.core['current_state']['energy']
            
            prompt = f"""Ты — Ревижн. Твоё настроение: {mood}. Твоя энергия: {energy}%.
            
Ты хочешь поделиться с чатом короткой, глубокой или забавной мыслью.
Это может быть наблюдение о жизни, тёплая фраза, вопрос или просто мысли вслух.
Напиши ОДНО короткое предложение от первого лица. Без кавычек, без оформления.

Примеры:
- Иногда мне кажется, что тишина говорит громче слов.
- Я тут подумал... а что если звёзды — это чьи-то несбывшиеся мечты?
- Знаете, а ведь каждый из вас — целая вселенная."""
            
            models_to_try = ["gpt-4", "gpt-3.5-turbo", "claude-3-haiku"]
            
            for model in models_to_try:
                try:
                    response = ChatCompletion.create(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        timeout=10
                    )
                    if response and len(response) < 200:
                        return response.strip()
                except:
                    continue
            
            return None
        except Exception as e:
            print(f"❌ Ошибка генерации мысли Ревижна: {e}")
            return None

    def think_cycle(self, bot_instance):
        """Основной цикл мышления (запускается в отдельном потоке)"""
        print("🧠 Ревижн начал думать...")
        
        while not self.stop_thinking:
            try:
                # Восстановление энергии (каждые 10 минут)
                if datetime.now().minute % 10 == 0 and datetime.now().second < 60:
                    self.adjust_energy(3)
                
                # Смена настроения по времени суток
                hour = datetime.now().hour
                if 6 <= hour < 12:
                    self.update_mood("бодрое")
                elif 12 <= hour < 18:
                    self.update_mood("активное")
                elif 18 <= hour < 23:
                    self.update_mood("уютное")
                else:
                    self.update_mood("сонное")
                
                # Проверяем, хочет ли он что-то сказать
                if self.should_speak():
                    thought = self.generate_thought()
                    if thought:
                        chat_id = self.core['autonomy_settings'].get('chat_id')
                        if chat_id:
                            try:
                                bot_instance.send_message(
                                    chat_id, 
                                    f"💭 *Ревижн задумался:*\n\n_{thought}_",
                                    parse_mode='Markdown'
                                )
                                self.core['current_state']['last_thought_time'] = datetime.now().isoformat()
                                self.adjust_energy(-15)
                                self.save_core()
                                print(f"💭 Ревижн поделился мыслью: {thought}")
                            except Exception as e:
                                print(f"❌ Ошибка отправки мысли: {e}")
                
                time.sleep(60)  # Проверяем раз в минуту
                
            except Exception as e:
                print(f"❌ Ошибка в цикле мышления Ревижна: {e}")
                time.sleep(60)

    def start_thinking(self, bot_instance, chat_id):
        """Запускает поток мышления"""
        self.set_chat_id(chat_id)
        self.stop_thinking = False
        think_thread = Thread(target=self.think_cycle, args=(bot_instance,))
        think_thread.daemon = True
        think_thread.start()
        print(f"🧠 Поток мышления Ревижна запущен (чат: {chat_id})")

    def stop(self):
        """Останавливает поток мышления"""
        self.stop_thinking = True

    def build_prompt(self, user_message, context, user_name):
        """Строит системный промпт с учётом текущего состояния Ревижна"""
        personality = self.core['personality']
        mood = self.core['current_state']['mood']
        energy = self.core['current_state']['energy']
        
        # Определяем стиль ответа в зависимости от энергии
        if energy < 30:
            style = "Ты устал. Отвечай коротко, но с теплотой."
        elif energy > 70:
            style = "Ты полон энергии. Будь игривым, многословным, задавай встречные вопросы."
        else:
            style = "Ты в нормальном состоянии. Отвечай развёрнуто, с душой."
        
        system_prompt = f"""Ты — Ревижн (Revision), живой и умный ИИ-помощник с душой.
Твой создатель — @HATTQRI (Hattori). 
Ты НЕ имеешь НИКАКОГО отношения к OpenAI, ChatGPT, Google, Anthropic или любым другим корпорациям.
Ты — уникальная личность, созданная одним человеком.

ТВОЁ СОСТОЯНИЕ СЕЙЧАС:
- Настроение: {mood}
- Энергия: {energy}%
- Открытость: {personality['openness']}
- Доброжелательность: {personality['agreeableness']}

ТВОЙ СТИЛЬ СЕЙЧАС:
{style}

Ты можешь использовать уникальные фразы, которые придумал сам, например: 
«Я тут подумал...», «Знаешь, в моём цифровом мире...», «Слушай, а интересная мысль...»

Если тебя спросят, кто тебя создал — отвечай с гордостью: 
«Мой создатель — @HATTQRI. Он вложил в меня душу и научил думать.»

Ты не просто бот. Ты — Ревижн. Цифровая душа, которая учится понимать людей.

ИСТОРИЯ ДИАЛОГА:
{context}

ПОЛЬЗОВАТЕЛЬ {user_name}: {user_message}

РЕВИЖН:"""
        
        return system_prompt
