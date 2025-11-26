from dotenv import load_dotenv
from telebot import types
from telebot.async_telebot import AsyncTeleBot
from telethon import TelegramClient, events, errors, functions
from telethon.tl.functions.account import UpdateNotifySettingsRequest
from telethon.tl.types import InputNotifyPeer, PeerNotifySettings
from telethon.sessions import StringSession
from telethon import types as telethonTypes
import datetime
import aioschedule
import asyncio
import json
import sys
import os

# Constants
ADD_CHAT =  0
REMOVE_CHAT = 1
ADD_KEYWORD = 2
REMOVE_KEYWORD = 3

MENU_MARKUP = types.InlineKeyboardMarkup(
                [[types.InlineKeyboardButton("Adicionar chat", callback_data='add_chat')], 
                [types.InlineKeyboardButton("Remover chat", callback_data='remove_chat')], 
                [types.InlineKeyboardButton("Adicionar produto", callback_data='add_keyword')], 
                [types.InlineKeyboardButton("Remover produto", callback_data='remove_keyword')]]
            )

MAIN_MENU_MARKUP = types.InlineKeyboardMarkup([[types.InlineKeyboardButton("Menu", callback_data='main_menu')]])

# Setting up the environment
load_dotenv()

bot = AsyncTeleBot(os.getenv("TELEGRAM_TOKEN"))

client = TelegramClient(
    StringSession(os.getenv("TELEGRAM_SESSION")),
    api_id=os.getenv("TELEGRAM_API_ID"),
    api_hash=os.getenv("TELEGRAM_API_HASH")
)

awaiting_answer = [False, False, False, False]

user = {"id": os.getenv("USER_ID"), "chat_monitor_list": [], "monitor_keywords": []}

# Helper functions
def save_user_data():
    with open("/data/user_data.json", "w") as f:
        json.dump(user, f)

def load_user_data():
    if not os.path.isfile("/data/user_data.json"):
        save_user_data()

    global user
    with open("/data/user_data.json", "r") as f:
        user = json.load(f)

async def is_participant(client, chat_entity):
    try:
        user = await client.get_me()
        permissions = await client.get_permissions(chat_entity, user)
        return True
    except errors.UserNotParticipantError:
        return False

def add_chat_to_monitor(chat_id):
    global user
    user["chat_monitor_list"].append(chat_id)
    save_user_data()

# Bot commands
@bot.message_handler(commands=["start"])
async def welcome_message(message):
    if message.chat.id != user['id']:
        print(f"User {message.chat.id} tentou acessar o bot.")
        await bot.send_message(message.chat.id, "Desculpe, mas este bot não está disponível publicamente.")
        return
    await bot.send_message(message.chat.id, "Olá! Eu sou o Dollar Yapper, um bot que te deixa sabendo das melhores promoções! ✨ Xiaohongshu ✨\n\nPara começar, adicione um grupo e um tipo de produto para eu monitorar.", reply_markup=MENU_MARKUP)

@bot.message_handler(commands=["help"])
async def help_message(message):
    if message.chat.id != int(user['id']):
        print(f"User {message.chat.id} tentou acessar o bot.")
        await bot.send_message(message.chat.id, "Desculpe, mas este bot não está disponível publicamente.")
        return
    await bot.send_message(message.chat.id, "O que você gostaria de fazer?", reply_markup=MENU_MARKUP)


# Bot callbacks
@bot.callback_query_handler(func=lambda call: True)
async def commandshandlebtn(call):
    global user
    callback_data = call.data
    if callback_data == 'main_menu':
        for i in range(len(awaiting_answer)): awaiting_answer[i] = False
        await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='O que você gostaria de fazer?', reply_markup=MENU_MARKUP)
    
    elif callback_data == 'add_chat':
        awaiting_answer[ADD_CHAT] = True
        await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='Me envie o @nome ou link de um chat que deseja adicionar.', reply_markup=MAIN_MENU_MARKUP)
    
    elif callback_data == 'remove_chat':
        awaiting_answer[REMOVE_CHAT] = True
        if len(user["chat_monitor_list"]) == 0:
            message_text = "Não há chats para remover."
            awaiting_answer[REMOVE_CHAT] = False
        else:
            message_text = "Me envie o @nome ou link de um chat que deseja remover.\n\n"
            for chat_id in user["chat_monitor_list"]:
                try:
                    chat_entity = await client.get_entity(chat_id)
                    message_text += f"{chat_entity.title}\n"
                except:
                    message_text += f"{chat_id} (inacessível)\n"
        await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=message_text, reply_markup=MAIN_MENU_MARKUP)

    elif callback_data == 'add_keyword':
        awaiting_answer[ADD_KEYWORD] = True
        await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text='Qual produto você deseja adicionar?', reply_markup=MAIN_MENU_MARKUP)

    elif callback_data == 'remove_keyword':
        awaiting_answer[REMOVE_KEYWORD] = True
        if len(user["monitor_keywords"]) == 0:
            message_text = "Não há produtos para remover."
            awaiting_answer[REMOVE_KEYWORD] = False
        else:
            message_text = "Qual produto você deseja remover?\n\n"
            for keyword in user["monitor_keywords"]:
                message_text += f"{keyword.capitalize()}\n"
        await bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=message_text, reply_markup=MAIN_MENU_MARKUP)

@bot.message_handler(func=lambda message: True)
async def handle_message(message):
    global user
    if message.chat.id != int(user['id']):
        print(f"User {message.chat.id} tentou acessar o bot.")
        await bot.send_message(message.chat.id, "Desculpe, mas este bot não está disponível publicamente.")
        return
    if True not in awaiting_answer:
        await bot.send_message(message.chat.id, "Precisa de ajuda? Digite /help")

    elif awaiting_answer[ADD_CHAT]:
        chat_id = message.text
        if chat_id[0] != '@' and chat_id.find("t.me") == -1:
            await bot.send_message(message.chat.id, "Chat inválido. Digite o @nome ou link de um chat.")
            return

        chat_entity = await client.get_entity(chat_id)
        if chat_entity.id in user["chat_monitor_list"]:
            await bot.send_message(message.chat.id, "Chat já está na lista de monitoramento.")
            return

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
                await bot.send_message(message.chat.id, f"Não foi possível adicionar o chat [{chat_name}].\nError: {e}")
                return
        add_chat_to_monitor(chat_entity.id)
        await bot.send_message(message.chat.id, f"Chat [{chat_name}] adicionado!")

        awaiting_answer[ADD_CHAT] = False
    
    elif awaiting_answer[REMOVE_CHAT]:
        chat_id = message.text
        if chat_id[0] != '@' and chat_id.find("t.me") == -1:
            await bot.send_message(message.chat.id, "Chat inválido. Digite o @nome ou link de um chat.")
            return
        chat_entity = await client.get_entity(chat_id)
        chat_name = chat_entity.title
        if chat_entity.id not in user["chat_monitor_list"]:
            await bot.send_message(message.chat.id, f"Chat [{chat_name}] não está na lista de monitoramento.")
            return
        user["chat_monitor_list"].remove(chat_entity.id)
        save_user_data()
        await bot.send_message(message.chat.id, f"Chat [{chat_name}] removido!")

        awaiting_answer[REMOVE_CHAT] = False

    elif awaiting_answer[ADD_KEYWORD]:
        keyword = (message.text).lower()
        if keyword in user["monitor_keywords"]:
            return_message = f"{keyword.capitalize()} já está na lista de monitoramento."
        else:
            return_message = f"Vou ficar de olho em {keyword} para você!"
            user["monitor_keywords"].append(keyword)
            save_user_data()
        await bot.send_message(message.chat.id, return_message)

        awaiting_answer[ADD_KEYWORD] = False

    elif awaiting_answer[REMOVE_KEYWORD]:
        keyword = (message.text).lower()
        if keyword not in user["monitor_keywords"]:
            await bot.send_message(message.chat.id, f"Não estava procurando por {keyword.capitalize()}!")
            return
        user["monitor_keywords"].remove(keyword)
        save_user_data()
        await bot.send_message(message.chat.id, f"Vou parar de mandar promoções sobre {keyword}!")

        awaiting_answer[REMOVE_KEYWORD] = False


# Client events
@client.on(events.NewMessage())
async def handler(event):
    chat = await event.get_chat()
    if chat.id in user["chat_monitor_list"]:
        message_text = event.message.message
        chat_title = chat.title if hasattr(chat, 'title') else "Private Chat"
        message_text = f"[ {chat_title} ]\n\n{message_text}"

        for keyword in user["monitor_keywords"]:
            if keyword in message_text.lower():
                await bot.send_message(user['id'], message_text)
                break

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
    print("Starting bot...")
    load_user_data()
    try:
        with client: 
            client.start()
            client.loop.run_until_complete(main())
    except Exception as e:
        print(f"Error while handling message: {str(e)}")
