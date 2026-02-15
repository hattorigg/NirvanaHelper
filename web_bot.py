from flask import Flask, request
import telebot
import time
import os

TOKEN = '8557626824:AAGqUCr8TbhS19kn2Kd2H2Qee1my024-k_U'
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "✅ Бот работает!")
    print(f"Отправил ответ пользователю {message.chat.id}")

@app.route('/' + TOKEN, methods=['POST'])
def webhook():
    update = telebot.types.Update.de_json(request.get_data().decode('utf-8'))
    bot.process_new_updates([update])
    return 'OK', 200

@app.route('/')
def index():
    return 'Бот работает!', 200

def set_webhook():
    url = f'https://Hattori.pythonanywhere.com/{TOKEN}'
    bot.remove_webhook()
    time.sleep(1)
    bot.set_webhook(url=url)
    print("Вебхук установлен")

set_webhook()