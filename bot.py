import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

BOT_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(f"Пошел нахуй, {message.from_user.first_name}")

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer("Иди нахуй")

@dp.message()
async def handle_messages(message: types.Message):
    if not message.text: return

    text = message.text.lower().strip()
    original_text = message.text.strip()
    command = ""
    is_private = message.chat.type == "private"

    if text.startswith("еблан"):
        command = text[5:].strip()
    elif is_private or (message.reply_to_message and message.reply_to_message.from_user.id == bot.id):
        command = text
    else:
        return

    if not command: return

    if command == "привет":
        await message.answer("Привет, иди нахуй")
    elif command == "как дела":
        await message.answer("Да иди ты нахуй")
    elif command == "что ты умеешь":
        await message.answer("Я умею ходить нахуй")
    elif command == "иди нахуй":
        await message.answer("Сам иди нахуй")
    else:
        pass

async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
