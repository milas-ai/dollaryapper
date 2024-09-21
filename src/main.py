import maritalk
import telebot
from dotenv import load_dotenv
import os

if __name__ == "__main__":
    load_dotenv()

    model = maritalk.MariTalk(
        key=os.getenv("MARITACA_KEY"),
        model="sabia-3"
    )

    bot = telebot.TeleBot(os.getenv("TELEGRAM_TOKEN"))

    @bot.message_handler(commands=["start"])
    def welcome_message(message):
        bot.reply_to(message, "Ola! Eu sou o Yap Dollar!")

    bot.infinity_polling()