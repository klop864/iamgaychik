import asyncio
import logging
import os
import json
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# Токен из настроек Railway
BOT_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

DB_FILE = "users.json"

# --- ФУНКЦИИ ДЛЯ РАБОТЫ С ДАННЫМИ ---
def load_users():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=4)

# --- БАЗОВЫЕ КОМАНДЫ ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(f"Пошел нахуй, {message.from_user.first_name}")

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer("Иди нахуй")

# --- ЛОГИКА ОБРАБОТКИ СООБЩЕНИЙ ---
@dp.message()
async def handle_messages(message: types.Message):
    if not message.text:
        return

    text = message.text.lower().strip()
    original_text = message.text.strip() # Сохраняем оригинальный регистр для ников
    command = ""

    # Проверяем, начинается ли с "еблан"
    if text.startswith("еблан"):
        command = text[5:].strip()
        original_command = original_text[5:].strip() # Для сохранения ников с большими буквами
    # В ЛС или в ответ на сообщение бота можно без слова "еблан"
    elif message.chat.type == "private" or (message.reply_to_message and message.reply_to_message.from_user.id == bot.id):
        command = text
        original_command = original_text
    else:
        return

    if not command:
        return

    # --- КОМАНДЫ ---
    if command == "привет":
        await message.answer("Привет, иди нахуй")
    
    elif command == "как дела":
        await message.answer("Да иди ты нахуй")
    
    elif command == "что ты умеешь":
        await message.answer("Я умею ходить нахуй")
        
    elif command == "иди нахуй":
        await message.answer("Сам иди нахуй")

    # --- ПРОФИЛЬ ---
    elif command == "профиль":
        user_id = str(message.from_user.id)
        users = load_users()
        
        # Если пользователя нет в базе, создаем ему профиль
        if user_id not in users:
            users[user_id] = {
                "nickname": message.from_user.username or message.from_user.first_name,
                "description": "",
                "balance": 0
            }
            save_users(users)
        
        user_data = users[user_id]
        
        profile_text = f"👤 Ник: {user_data['nickname']}\n"
        if user_data['description']:
            profile_text += f"📝 Описание: {user_data['description']}\n"
        profile_text += f"💰 Баланс: {user_data['balance']}$"
        
        await message.answer(profile_text)

    # --- УСТАНОВКА НИКА ---
    elif command.startswith("ник "):
        new_nick = original_command[4:].strip()
        if new_nick:
            user_id = str(message.from_user.id)
            users = load_users()
            if user_id not in users:
                users[user_id] = {"nickname": "", "description": "", "balance": 0}
            
            users[user_id]["nickname"] = new_nick
            save_users(users)
            await message.answer(f"Ник изменен на: {new_nick}")
        else:
            await message.answer("Ты забыл написать ник.")

    # --- УСТАНОВКА ОПИСАНИЯ ---
    elif command.startswith("описание "):
        new_desc = original_command[9:].strip()
        if new_desc:
            user_id = str(message.from_user.id)
            users = load_users()
            if user_id not in users:
                users[user_id] = {"nickname": message.from_user.username or message.from_user.first_name, "description": "", "balance": 0}
            
            users[user_id]["description"] = new_desc
            save_users(users)
            await message.answer(f"Описание изменено на: {new_desc}")
        else:
            await message.answer("Ты забыл написать описание.")

async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
