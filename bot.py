import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

# Токен из настроек Railway
BOT_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- БАЗОВЫЕ КОМАНДЫ (работают везде) ---
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
    command = ""
    
    # ПРОВЕРКА 1: Личный чат (ЛС)
    if message.chat.type == "private":
        # В личке имя "еблан" не обязательно
        command = text
        
    # ПРОВЕРКА 2: Группа или супергруппа
    elif message.chat.type in ["group", "supergroup"]:
        # Вариант А: Написали с именем "еблан"
        if text.startswith("еблан"):
            command = text[5:].strip()
        
        # Вариант Б: Ответили (реплай) на сообщение бота
        elif message.reply_to_message and message.reply_to_message.from_user.id == bot.id:
            command = text

    # --- ВЫПОЛНЕНИЕ КОМАНД ---
    # Если команда так и осталась пустой, бот просто промолчит
    if not command:
        return

    if command == "привет":
        await message.answer("Привет, иди нахуй")
    
    elif command == "как дела":
        await message.answer("Да иди ты нахуй")
    
    elif command == "что ты умеешь":
        await message.answer("Я умею ходить нахуй")
        
    elif command == "иди нахуй":
        await message.answer("Сам иди нахуй")
        
    # На всё остальное (включая одиночное "еблан") бот молчит
    else:
        pass 

async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
