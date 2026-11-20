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

# --- БАЗОВЫЕ КОМАНДЫ ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(f"Пошел нахуй, {message.from_user.first_name}")

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer("Иди нахуй")

# --- ЛОГИКА ОБРАЩЕНИЯ ПО ИМЕНИ ---
@dp.message()
async def handle_messages(message: types.Message):
    if not message.text:
        return

    text = message.text.lower().strip()

    # Проверяем, начинается ли сообщение с имени "еблан"
    if text.startswith("еблан"):
        command = text[5:].strip()

        if command == "привет":
            # Убрали имя
            await message.answer("Привет, иди нахуй")
        
        elif command == "как дела":
            await message.answer("Да иди ты нахуй")
        
        elif command == "что ты умеешь":
            await message.answer("Я умею ходить нахуй")
            
        elif command == "иди нахуй":
            await message.answer("Сам иди нахуй")
            
        # На одиночное "еблан" теперь тоже молчим (убрали else if command == "")
        else:
            pass
    
    # На сообщения без имени "еблан" тоже молчим
    else:
        pass 

async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
