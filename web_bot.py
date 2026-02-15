from flask import Flask, request
import telebot
import time
import os

TOKEN = '8557626824:AAGqUCr8TbhS19kn2Kd2H2Qee1my024-k_U'
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "✅ Бот работает на Render!")
    print(f"Отправил ответ пользователю {message.chat.id}")

@app.route('/' + TOKEN, methods=['POST'])
def webhook():
    update = telebot.types.Update.de_json(request.get_data().decode('utf-8'))
    bot.process_new_updates([update])
    return 'OK', 200

@app.route('/')
def index():
    return 'Бот работает на Render!', 200

@app.route('/ping')
def ping():
    return 'pong', 200

def set_webhook():
    url = f'https://nirvanahelper.onrender.com/{TOKEN}'
    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url=url)
    print(f"Вебхук установлен на {url}")

set_webhook()

if __name__ == "__main__":
    # Render сам даёт порт через переменную окружения
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
