import asyncio
import logging
import os
import random
import asyncpg
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
ADMIN_ID = 6185219874

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def init_db():
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            nickname TEXT,
            description TEXT,
            balance BIGINT DEFAULT 10
        )
    """)
    await conn.close()

async def get_user(user_id, tg_username=None):
    conn = await asyncpg.connect(DATABASE_URL)
    user = await conn.fetchrow("SELECT nickname, description, balance FROM users WHERE user_id = $1", user_id)
    
    if not user:
        default_nick = tg_username if tg_username else "Без ника"
        await conn.execute("INSERT INTO users (user_id, nickname, description, balance) VALUES ($1, $2, $3, $4)", 
                           user_id, default_nick, "", 10)
        await conn.close()
        return {"nickname": default_nick, "description": "", "balance": 10}
    
    if user["nickname"] == "Без ника" and tg_username:
        await conn.execute("UPDATE users SET nickname = $1 WHERE user_id = $2", tg_username, user_id)
        await conn.close()
        return {"nickname": tg_username, "description": user["description"], "balance": user["balance"]}
        
    await conn.close()
    return dict(user)

async def update_user(user_id, field, value):
    conn = await asyncpg.connect(DATABASE_URL)
    user = await conn.fetchrow("SELECT user_id FROM users WHERE user_id = $1", user_id)
    if not user:
        await conn.execute("INSERT INTO users (user_id, nickname, description, balance) VALUES ($1, $2, $3, $4)", user_id, "Без ника", "", 10)
    query = f"UPDATE users SET {field} = $1 WHERE user_id = $2"
    await conn.execute(query, value, user_id)
    await conn.close()

async def get_user_by_username(username):
    conn = await asyncpg.connect(DATABASE_URL)
    user = await conn.fetchrow("SELECT user_id FROM users WHERE nickname = $1", username)
    await conn.close()
    return user["user_id"] if user else None

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(f"Пошел нахуй, {message.from_user.first_name}")

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.answer("Иди нахуй")

@dp.message()
async def handle_messages(message: types.Message):
    if not message.text:
        return

    # Передача сообщений работает только в ЛС
    if message.chat.type == "private":
        text_to_check = message.text.strip()
        if text_to_check.lower().startswith("еблан передай "):
            text_to_check = text_to_check[13:].strip()
        elif text_to_check.lower().startswith("передай "):
            text_to_check = text_to_check[7:].strip()
        else:
            text_to_check = None

        if text_to_check:
            parts = text_to_check.split(maxsplit=1)
            if len(parts) == 2:
                target_username = parts[0].replace("@", "")
                msg_text = parts[1]
                try:
                    # Отправляем просто текст без приставок
                    await bot.send_message(chat_id=f"@{target_username}", text=msg_text)
                    await message.answer("Сообщение передано")
                except TelegramBadRequest:
                    await message.answer("Я не нашел такого пользователя или он не запускал бота")
                except TelegramForbiddenError:
                    await message.answer("Этот пользователь заблокировал бота")
                return
            else:
                await message.answer("Напиши так: еблан передай @юзернейм [текст сообщения]")
                return

    text = message.text.lower().strip()
    original_text = message.text.strip()
    command = ""

    if text.startswith("еблан"):
        command = text[5:].strip()
        original_command = original_text[5:].strip()
    elif message.chat.type == "private" or (message.reply_to_message and message.reply_to_message.from_user.id == bot.id):
        command = text
        original_command = original_text
    else:
        return

    if not command:
        return

    user_id = message.from_user.id
    tg_username = message.from_user.username or message.from_user.first_name

    if command == "привет":
        await message.answer("Привет, иди нахуй")
    elif command == "как дела":
        await message.answer("Да иди ты нахуй")
    elif command == "что ты умеешь":
        await message.answer("Я умею ходить нахуй")
    elif command == "иди нахуй":
        await message.answer("Сам иди нахуй")
    
    elif command == "профиль":
        user_data = await get_user(user_id, tg_username)
        profile_text = f"👤 Ник: {user_data['nickname']}\n"
        if user_data["description"]:
            profile_text += f"📝 Описание: {user_data['description']}\n"
        profile_text += f"💰 Баланс: {user_data['balance']}$"
        await message.answer(profile_text)
    
    elif command.startswith("ник "):
        new_nick = original_command[4:].strip()
        if new_nick:
            await update_user(user_id, "nickname", new_nick)
            await message.answer(f"Ник изменен на: {new_nick}")
        else:
            await message.answer("Ты забыл написать ник")
    
    elif command.startswith("описание "):
        new_desc = original_command[9:].strip()
        if new_desc:
            await update_user(user_id, "description", new_desc)
            await message.answer(f"Описание изменено на: {new_desc}")
        else:
            await message.answer("Ты забыл написать описание")
    
    elif command.startswith("выдать ") or command == "выдать":
        if message.from_user.id != ADMIN_ID:
            return
        try:
            amount = int(command.split()[1])
            user_data = await get_user(user_id, tg_username)
            new_balance = user_data["balance"] + amount
            await update_user(user_id, "balance", new_balance)
            await message.answer(f"Успешно начислено {amount}$. Твой баланс: {new_balance}$")
        except (IndexError, ValueError):
            await message.answer("Напиши сумму. Например: еблан выдать 676767")
    
    elif command.startswith("дать "):
        parts = original_command[5:].strip().split() 
        target_id = None
        amount = 0
        if message.reply_to_message:
            target_id = message.reply_to_message.from_user.id
            try:
                amount = int(parts[0])
            except (IndexError, ValueError):
                await message.answer("Блин дурак напиши еблан потом дать потом короче юзернейм и потом число еще короче можно в ответ ему написать типо еблан дать 67")
                return
        elif len(parts) == 2:
            target_nickname = parts[0].replace("@", "")
            try:
                amount = int(parts[1])
            except ValueError:
                await message.answer("Блин дурак напиши еблан потом дать потом короче юзернейм и потом число еще короче можно в ответ ему написать типо еблан дать 67")
                return
            target_id = await get_user_by_username(target_nickname)
            if not target_id:
                await message.answer("Я не нашел такого пользователя")
                return
        else:
            await message.answer("Блин дурак напиши еблан потом дать потом короче юзернейм и потом число еще короче можно в ответ ему написать типо еблан дать 67")
            return

        if target_id == user_id:
            await message.answer("Ты не можешь перевести деньги самому себе")
            return
        if amount <= 0:
            await message.answer("Сумма должна быть больше нуля")
            return

        sender_data = await get_user(user_id, tg_username)
        if sender_data["balance"] < amount:
            await message.answer("ты бомж ахах")
            return

        target_data = await get_user(target_id)
        await update_user(user_id, "balance", sender_data["balance"] - amount)
        await update_user(target_id, "balance", target_data["balance"] + amount)
        
        await message.answer(f"Успешно переведено {amount}$ пользователю {target_data['nickname']}")

        send_notification = False
        if message.chat.type == "private":
            send_notification = True
        else:
            try:
                member = await bot.get_chat_member(chat_id=message.chat.id, user_id=target_id)
                if member.status in ["left", "kicked"]:
                    send_notification = True
            except TelegramBadRequest:
                send_notification = True

        if send_notification:
            try:
                await bot.send_message(target_id, f"вам прислали {amount}")
            except (TelegramForbiddenError, TelegramBadRequest):
                pass

    elif command.startswith("казино "):
        parts = original_command[7:].strip().split()
        if len(parts) != 2:
            await message.answer("Блин дурак напиши еблан потом казино потом свою ставку и красное или черное это типа на какой цвет ты ставишь понял да")
            return
        try:
            bet_amount = int(parts[0])
        except ValueError:
            await message.answer("Блин дурак напиши еблан потом казино потом свою ставку и красное или черное это типа на какой цвет ты ставишь понял да")
            return
        color = parts[1].lower()
        if color not in ["красное", "черное", "кр", "чр"]:
            await message.answer("Блин дурак напиши еблан потом казино потом свою ставку и красное или черное это типа на какой цвет ты ставишь понял да")
            return
        if color in ["кр"]: color = "красное"
        if color in ["чр"]: color = "черное"
        if bet_amount <= 0:
            await message.answer("Сумма должна быть больше нуля")
            return
        
        user_data = await get_user(user_id, tg_username)
        if user_data["balance"] < bet_amount:
            await message.answer("ты бомж ахах")
            return

        result_color = random.choice(["красное", "черное"])

        if result_color == color:
            new_balance = user_data["balance"] + bet_amount
            await update_user(user_id, "balance", new_balance)
            await message.answer(f"Выпало {result_color}. Ты победил блин молодец")
        else:
            new_balance = user_data["balance"] - bet_amount
            await update_user(user_id, "balance", new_balance)
            await message.answer(f"Выпало {result_color}. Ты проебал лузер ебаный ахаха соси")

async def main():
    print("Бот запущен...")
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
