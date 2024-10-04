from dotenv import load_dotenv
from telebot import types
from telebot.async_telebot import AsyncTeleBot
from telethon import TelegramClient, events, errors, functions
from telethon.tl.functions.account import UpdateNotifySettingsRequest
from telethon.tl.types import InputNotifyPeer, PeerNotifySettings
from telethon import types as telethonTypes
import datetime
import maritalk
import aioschedule
import asyncio
import json
import os

# Constants
NEW_CHAT =  0


# Helper functions
async def is_participant(client, chat_entity):
    try:
        user = await client.get_me()
        permissions = await client.get_permissions(chat_entity, user)
        return True
    except errors.UserNotParticipantError:
        return False

def save_user_data(user_data):
    with open("user_data.json", "w") as f:
        json.dump(user_data, f)

def load_user_data():
    if not os.path.isfile("user_data.json"):
        with open("user_data.json", "w") as f:
            json.dump({
                "main_chat_id": None,
                "chat_monitor_list": []
            }, f)

    with open("user_data.json", "r") as f:
        return json.load(f)

def set_main_chat_id(chat_id):
    user_data["main_chat_id"] = chat_id
    save_user_data(user_data)

def add_chat_to_monitor(chat_id):
    user_data["chat_monitor_list"].append(chat_id)
    save_user_data(user_data)

# Setting up the environment
load_dotenv()

model = maritalk.MariTalk(
    key=os.getenv("MARITACA_KEY"),
    model="sabia-3"
)

bot = AsyncTeleBot(os.getenv("TELEGRAM_TOKEN"))

client = TelegramClient(
    "dollar_yapper",
    api_id=os.getenv("TELEGRAM_API_ID"),
    api_hash=os.getenv("TELEGRAM_API_HASH")
)

awaiting_answer = [False]

user_data = load_user_data()


# Bot commands
@bot.message_handler(commands=["start"])
async def welcome_message(message):
    set_main_chat_id(message.chat.id)
    print(f"Main chat id: {user_data['main_chat_id']}")
    keyboard = [[types.InlineKeyboardButton("Adicionar chat", callback_data='new_chat')]]
    markup = types.InlineKeyboardMarkup(keyboard)
    await bot.send_message(user_data['main_chat_id'], "Olá! Eu sou o Yap Dollar, um bot que fala sobre economia.", reply_markup=markup)

@bot.message_handler(commands=["help"])
async def help_message(message):
    keyboard = [[types.InlineKeyboardButton("Adicionar chat", callback_data='new_chat')]]
    markup = types.InlineKeyboardMarkup(keyboard)
    await bot.send_message(message.chat.id, "O que você gostaria de fazer?", reply_markup=markup)


# Bot callbacks
@bot.callback_query_handler(func=lambda call: True)
async def commandshandlebtn(call):
    callback_data = call.data
    if callback_data == 'main_menu':
        for i in range(len(awaiting_answer)): awaiting_answer[i] = False

        keyboard = [[types.InlineKeyboardButton("Adicionar chat", callback_data='new_chat')]]
        markup = types.InlineKeyboardMarkup(keyboard)
        await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='O que você gostaria de fazer?', reply_markup=markup)
    elif callback_data == 'new_chat':
        awaiting_answer[NEW_CHAT] = True

        keyboard = [[types.InlineKeyboardButton("Menu", callback_data='main_menu')]]
        markup = types.InlineKeyboardMarkup(keyboard)
        await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='Me envie o @nome ou link de um chat que deseja adicionar.', reply_markup=markup)

@bot.message_handler(func=lambda message: True)
async def handle_message(message):
    if True not in awaiting_answer:
        await bot.send_message(message.chat.id, "Precisa de ajuda? Digite /help")

    elif awaiting_answer[NEW_CHAT]:
        chat_id = message.text
        if chat_id[0] != '@' and chat_id.find("t.me") == -1:
            await bot.send_message(message.chat.id, "Chat inválido. Digite o @nome ou link de um chat.")
            return
        chat_entity = await client.get_entity(chat_id)
        chat_name = chat_entity.title
        if not await is_participant(client, chat_entity):
            try:
                await client(functions.channels.JoinChannelRequest(chat_entity))
                if not await is_participant(client, chat_entity): raise Exception
                await client(UpdateNotifySettingsRequest(peer=InputNotifyPeer(chat_id), 
                                                         settings=telethonTypes.InputPeerNotifySettings(
                                                            show_previews=False,
                                                            mute_until=datetime.datetime.now() + datetime.timedelta(days=365),
                                                            sound=telethonTypes.NotificationSoundDefault(),
                                                            stories_muted=False,
                                                            stories_hide_sender=False,
                                                            stories_sound=telethonTypes.NotificationSoundDefault())))
            except Exception as e:
                await bot.send_message(message.chat.id, f"Não foi possível adicionar o chat [{chat_name}]. Error: {e}")
                return
        add_chat_to_monitor(chat_entity.id)
        await bot.send_message(message.chat.id, f"Chat [{chat_name}] adicionado!")
            
        awaiting_answer[NEW_CHAT] = False


# Client events
@client.on(events.NewMessage())
async def handler(event):
    chat = await event.get_chat()
    if chat.id in user_data["chat_monitor_list"]:
        sender = await event.get_sender()
        sender_name = sender.first_name if sender else "Unknown"
        message_text = event.message.message
        chat_title = chat.title if event.is_group else "Private Chat"
        message_text = f"Chat: {chat_title}\n{message_text}"
        await bot.send_message(user_data['main_chat_id'], message_text)


# Main functions
async def scheduler():
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)

async def main():
    try:
        await asyncio.gather(bot.infinity_polling(), scheduler())
    except Exception as e:
        print(f"Error while handling message: {str(e)}")

if __name__ == "__main__":
    try:
        with client:
            client.start(phone=os.getenv("PHONE_NUMBER"))
            client.loop.run_until_complete(main())
    except Exception as e:
        print(f"Error while handling message: {str(e)}")