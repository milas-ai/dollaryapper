from dotenv import load_dotenv
from telethon import TelegramClient, events, errors, functions
from telebot.async_telebot import AsyncTeleBot
from telebot import types
import maritalk
import aioschedule
import asyncio
import os

async def is_participant(client, chat_entity):
    try:
        user = await client.get_me()
        permissions = await client.get_permissions(chat_entity, user)
        return True
    except errors.UserNotParticipantError:
        return False

load_dotenv()

# Setting up objects
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

NEW_CHAT =  0
awaiting_answer = [False]


# List of chats that the bot will listen to
chat_list = []


# Bot commands
@bot.message_handler(commands=["start"])
async def welcome_message(message):
    keyboard = [[types.InlineKeyboardButton("Adicionar chat", callback_data='new_chat')]]
    markup = types.InlineKeyboardMarkup(keyboard)
    await bot.send_message(message.chat.id, "Olá! Eu sou o Yap Dollar, um bot que fala sobre economia.", reply_markup=markup)

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
                await client(functions.account.UpdateNotifySettings(peer=chat_entity, settings=types.InputPeerNotifySettings(mute_until=0, show_previews=False))
            except:
                await bot.send_message(message.chat.id, f"Não foi possível adicionar o chat [{chat_name}].")
                return
        chat_list.append(chat_entity.id)
        await bot.send_message(message.chat.id, f"Chat [{chat_name}] adicionado!")
            
        awaiting_answer[NEW_CHAT] = False

# Client events
@client.on(events.NewMessage())
async def handler(event):
    chat = await event.get_chat()
    if str(chat.id) in chat_list:
        sender = await event.get_sender()
        sender_name = sender.first_name if sender else "Unknown"
        message_text = event.message.message
        chat_title = chat.title if event.is_group else "Private Chat"

        print(f"Message from {sender_name} in {chat_title}: {message_text}")

async def scheduler():
    while True:
        await aioschedule.run_pending()
        await asyncio.sleep(1)

async def main():
    await asyncio.gather(bot.infinity_polling(), scheduler())

if __name__ == "__main__":
    # asyncio.run(main())
    with client:
        client.start(phone=os.getenv("PHONE_NUMBER"))
        client.loop.run_until_complete(main())