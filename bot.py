import asyncio
import logging
import os
import random
import json
import asyncpg
from datetime import datetime, timedelta, timezone
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
ADMIN_ID = 6185219874

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

USERS_FILE = "usernames.json"

def load_usernames():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_usernames(data):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

async def init_db():
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            nickname TEXT,
            description TEXT,
            balance BIGINT DEFAULT 10,
            warns INT DEFAULT 0,
            last_warn_time TIMESTAMP,
            awards TEXT
        )
    """)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS chat_ranks (
            chat_id BIGINT,
            user_id BIGINT,
            rank INT DEFAULT 0,
            rank_name TEXT,
            PRIMARY KEY (chat_id, user_id)
        )
    """)
    await conn.close()

async def get_user(user_id, tg_username=None):
    conn = await asyncpg.connect(DATABASE_URL)
    user = await conn.fetchrow("SELECT nickname, description, balance, warns, last_warn_time, awards FROM users WHERE user_id = $1", user_id)
    
    if not user:
        default_nick = tg_username if tg_username else "Без ника"
        await conn.execute("INSERT INTO users (user_id, nickname, description, balance, warns) VALUES ($1, $2, $3, $4, $5)", 
                           user_id, default_nick, "", 10, 0)
        await conn.close()
        return {"nickname": default_nick, "description": "", "balance": 10, "warns": 0, "last_warn_time": None, "awards": None}
    
    if user["nickname"] == "Без ника" and tg_username:
        await conn.execute("UPDATE users SET nickname = $1 WHERE user_id = $2", tg_username, user_id)
        await conn.close()
        return {"nickname": tg_username, "description": user["description"], "balance": user["balance"], "warns": user["warns"], "last_warn_time": user["last_warn_time"], "awards": user["awards"]}
        
    await conn.close()
    return dict(user)

async def update_user(user_id, field, value):
    conn = await asyncpg.connect(DATABASE_URL)
    user = await conn.fetchrow("SELECT user_id FROM users WHERE user_id = $1", user_id)
    if not user:
        await conn.execute("INSERT INTO users (user_id, nickname, description, balance, warns) VALUES ($1, $2, $3, $4, $5)", user_id, "Без ника", "", 10, 0)
    query = f"UPDATE users SET {field} = $1 WHERE user_id = $2"
    await conn.execute(query, value, user_id)
    await conn.close()

async def get_chat_rank(chat_id, user_id):
    conn = await asyncpg.connect(DATABASE_URL)
    row = await conn.fetchrow("SELECT rank FROM chat_ranks WHERE chat_id = $1 AND user_id = $2", chat_id, user_id)
    await conn.close()
    return row["rank"] if row else 0

async def set_chat_rank(chat_id, user_id, rank):
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("""
        INSERT INTO chat_ranks (chat_id, user_id, rank) VALUES ($1, $2, $3)
        ON CONFLICT (chat_id, user_id) DO UPDATE SET rank = EXCLUDED.rank
    """, chat_id, user_id, rank)
    await conn.close()

async def get_user_by_username(username):
    users = load_usernames()
    username = username.replace("@", "").lower()
    if username in users:
        return users[username]
    conn = await asyncpg.connect(DATABASE_URL)
    user = await conn.fetchrow("SELECT user_id FROM users WHERE nickname = $1", username)
    await conn.close()
    return user["user_id"] if user else None

def parse_time(time_str):
    time_str = time_str.lower()
    if time_str.endswith("с"): return int(time_str[:-1])
    elif time_str.endswith("м"): return int(time_str[:-1]) * 60
    elif time_str.endswith("ч"): return int(time_str[:-1]) * 3600
    elif time_str.endswith("д"): return int(time_str[:-1]) * 86400
    else: return int(time_str)

async def unban_task(chat_id, user_id, delay, username):
    await asyncio.sleep(delay)
    try:
        await bot.unban_chat_member(chat_id=chat_id, user_id=user_id)
        await bot.send_message(chat_id, f"Ахах разбанили лоха @{username}")
    except Exception: pass

async def unmute_task(chat_id, user_id, delay, username):
    await asyncio.sleep(delay)
    try:
        permissions = types.ChatPermissions(can_send_messages=True)
        await bot.restrict_chat_member(chat_id=chat_id, user_id=user_id, permissions=permissions)
        await bot.send_message(chat_id, f"Ахах размутили лоха @{username}")
    except Exception: pass

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    tg_username = message.from_user.username
    if tg_username:
        users = load_usernames()
        users[tg_username.lower()] = user_id
        save_usernames(users)
    await get_user(user_id, tg_username or message.from_user.first_name)
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
    chat_id = message.chat.id

    if text.startswith("еблан"):
        command = text[5:].strip()
        original_command = original_text[5:].strip()
    elif is_private or (message.reply_to_message and message.reply_to_message.from_user.id == bot.id):
        command = text
        original_command = original_text
    else:
        return

    if not command: return

    user_id = message.from_user.id
    tg_username = message.from_user.username or message.from_user.first_name
    user_data = await get_user(user_id, tg_username)
    
    user_rank = 0
    if not is_private:
        user_rank = await get_chat_rank(chat_id, user_id)
        try:
            chat_member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
            if chat_member.status == "creator":
                if user_rank < 5:
                    await set_chat_rank(chat_id, user_id, 5)
                    user_rank = 5
        except Exception:
            pass

    if command == "привет":
        await message.answer("Привет, иди нахуй")
        return
    elif command == "как дела":
        await message.answer("Да иди ты нахуй")
        return
    elif command == "что ты умеешь":
        await message.answer("Я умею ходить нахуй")
        return
    elif command == "иди нахуй":
        await message.answer("Сам иди нахуй")
        return

    if command == "админы":
        if is_private:
            await message.answer("Эта команда работает только в чатах")
            return
        conn = await asyncpg.connect(DATABASE_URL)
        admins = await conn.fetch("SELECT user_id, rank FROM chat_ranks WHERE chat_id = $1 AND rank > 0 ORDER BY rank DESC", chat_id)
        await conn.close()
        
        text_out = "Админы олухи\n"
        for r in range(5, 0, -1):
            admin_ids = [a["user_id"] for a in admins if a["rank"] == r]
            if admin_ids:
                names = []
                for a_id in admin_ids:
                    a_data = await get_user(a_id)
                    names.append(a_data["nickname"])
                text_out += f"{r} - {', '.join(names)}\n"
        
        if text_out == "Админы олухи\n":
            await message.answer("Админов нет")
        else:
            await message.answer(text_out.strip())
        return

    if user_rank == 5 or user_id == ADMIN_ID:
        parts = command.split(maxsplit=2)
        if len(parts) == 3 and parts[0] in ["1", "2", "3", "4", "5"] and parts[1] == "админ":
            r_num = int(parts[0])
            r_name = parts[2]
            conn = await asyncpg.connect(DATABASE_URL)
            await conn.execute("UPDATE chat_ranks SET rank_name = $1 WHERE chat_id = $2 AND rank = $3", r_name, chat_id, r_num)
            await conn.close()
            await message.answer("Оккккк")
            return

    if command.startswith(("назначить ", "разжаловать ")):
        if user_rank < 5 and user_id != ADMIN_ID:
            await message.answer("Ты слишком маленький для такого")
            return
        parts = original_command.split()
        action = parts[0].lower()
        target_id = None
        target_username = None
        new_rank = 0

        if message.reply_to_message:
            target_id = message.reply_to_message.from_user.id
            target_username = message.reply_to_message.from_user.username or "юзер"
            if action == "назначить" and len(parts) > 1: 
                try: new_rank = int(parts[1])
                except: pass
        elif len(parts) >= 3:
            target_username = parts[1].replace("@", "")
            target_id = await get_user_by_username(target_username)
            if action == "назначить": 
                try: new_rank = int(parts[2])
                except: pass
        
        if not target_id:
            await message.answer("Пользователь ушел нахуй")
            return

        target_rank = await get_chat_rank(chat_id, target_id)
        if user_id != ADMIN_ID and target_rank > user_rank:
            await message.answer("Ты слишком маленький для такого")
            return

        if action == "назначить":
            if not (1 <= new_rank <= 5):
                await message.answer("Там толька 1-5 можна пон")
                return
            await set_chat_rank(chat_id, target_id, new_rank)
            await message.answer(f"@{target_username} стал олухом")
        elif action == "разжаловать":
            await set_chat_rank(chat_id, target_id, 0)
            await message.answer("Ахах лох")
        return

    if command.startswith("наградить "):
        if user_rank < 1 and user_id != ADMIN_ID:
            await message.answer("Ты слишком маленький для такого")
            return
        parts = original_command.split(maxsplit=2)
        target_id = None
        target_username = None
        award_text = ""

        if message.reply_to_message:
            target_id = message.reply_to_message.from_user.id
            target_username = message.reply_to_message.from_user.username or "юзер"
            if len(parts) > 1: award_text = parts[1]
        elif len(parts) == 3:
            target_username = parts[1].replace("@", "")
            target_id = await get_user_by_username(target_username)
            award_text = parts[2]
        
        if not target_id:
            await message.answer("Пользователь ушел нахуй")
            return
        if not award_text:
            await message.answer("Напиши текст награды")
            return

        target_data = await get_user(target_id)
        target_rank = await get_chat_rank(chat_id, target_id)
        if user_id != ADMIN_ID and target_rank > user_rank:
            await message.answer("Ты слишком маленький для такого")
            return

        current_awards = target_data["awards"]
        new_awards = f"{current_awards}\n{award_text}" if current_awards else award_text
        await update_user(target_id, "awards", new_awards)
        await message.answer("Награда выдана, хозяин!~")
        return

    if command.startswith(("бан ", "мут ", "варн ", "варны ")):
        action = command.split()[0]
        req_rank = {"бан": 4, "мут": 3, "варн": 2, "варны": 2}.get(action, 0)
        
        if user_rank < req_rank and user_id != ADMIN_ID:
            await message.answer("Ты слишком маленький для такого")
            return
            
        parts = original_command.split()
        target_id = None
        target_username = None
        time_str = None

        if message.reply_to_message:
            target_id = message.reply_to_message.from_user.id
            target_username = message.reply_to_message.from_user.username or "юзер"
            if len(parts) > 1 and action in ["бан", "мут"]: time_str = parts[1]
        elif len(parts) >= 2:
            target_username = parts[1].replace("@", "")
            target_id = await get_user_by_username(target_username)
            if len(parts) > 2 and action in ["бан", "мут"]: time_str = parts[2]
        
        if not target_id:
            await message.answer("Пользователь ушел нахуй")
            return

        target_rank = await get_chat_rank(chat_id, target_id)
        if user_id != ADMIN_ID and target_rank > user_rank:
            await message.answer("Ты слишком маленький для такого")
            return

        if action == "бан":
            if not time_str:
                await message.answer("Укажи время")
                return
            try:
                delay = parse_time(time_str)
                await bot.ban_chat_member(chat_id=chat_id, user_id=target_id)
                await message.answer("Ахах забанили лоха")
                asyncio.create_task(unban_task(chat_id, target_id, delay, target_username))
            except Exception: 
                await message.answer("Я слишком маленький для такого")
        elif action == "мут":
            if not time_str:
                await message.answer("Укажи время")
                return
            try:
                delay = parse_time(time_str)
                until_date = datetime.now(timezone.utc) + timedelta(seconds=delay)
                permissions = types.ChatPermissions(can_send_messages=False)
                await bot.restrict_chat_member(chat_id=chat_id, user_id=target_id, permissions=permissions, until_date=until_date)
                await message.answer("Ахах замутили лоха")
                asyncio.create_task(unmute_task(chat_id, target_id, delay, target_username))
            except Exception: 
                await message.answer("Я слишком маленький для такого")
        elif action == "варн":
            target_data = await get_user(target_id)
            now = datetime.now(timezone.utc)
            if target_data["last_warn_time"]:
                last_warn = target_data["last_warn_time"].replace(tzinfo=timezone.utc)
                if now - last_warn > timedelta(days=10):
                    await update_user(target_id, "warns", 0)
                    target_data["warns"] = 0

            new_warns = target_data["warns"] + 1
            await update_user(target_id, "warns", new_warns)
            await update_user(target_id, "last_warn_time", now)
            
            if new_warns >= 5:
                await message.answer("Ппц лох 5/5 варнов")
                try:
                    await bot.ban_chat_member(chat_id=chat_id, user_id=target_id)
                    asyncio.create_task(unban_task(chat_id, target_id, 86400, target_username))
                    await update_user(target_id, "warns", 0)
                except Exception: pass
            else:
                await message.answer(f"Ахах заварнили лоха\nварнов {new_warns}/5")
                
        elif action == "варны":
            target_data = await get_user(target_id)
            now = datetime.now(timezone.utc)
            warns = target_data["warns"]
            if target_data["last_warn_time"] and warns > 0:
                last_warn = target_data["last_warn_time"].replace(tzinfo=timezone.utc)
                if now - last_warn > timedelta(days=10):
                    warns = 0
                    await update_user(target_id, "warns", 0)
            await message.answer(f"Ъььэь {warns}/5 варнов")
        return

    if command == "профиль":
        profile_text = f"👤 Ник: {user_data['nickname']}\n"
        if user_data["description"]: profile_text += f"📝 Описание: {user_data['description']}\n"
        profile_text += f"💰 Баланс: {user_data['balance']}$\n"
        if user_data["awards"]:
            profile_text += "🏆 Награды:\n"
            for i, award in enumerate(user_data["awards"].split("\n"), 1):
                profile_text += f"{i}. {award}\n"
        await message.answer(profile_text.strip())
    elif command.startswith("ник "):
        new_nick = original_command[4:].strip()
        if new_nick:
            await update_user(user_id, "nickname", new_nick)
            await message.answer(f"Ник изменен на: {new_nick}")
    elif command.startswith("описание "):
        new_desc = original_command[9:].strip()
        if new_desc:
            await update_user(user_id, "description", new_desc)
            await message.answer(f"Описание изменено на: {new_desc}")
    elif command.startswith("выдать ") or command == "выдать":
        if message.from_user.id != ADMIN_ID: return
        try:
            amount = int(command.split()[1])
            new_balance = user_data["balance"] + amount
            await update_user(user_id, "balance", new_balance)
            await message.answer(f"Начислено {amount}$ Твой баланс: {new_balance}$")
        except: pass
    elif command.startswith("дать "):
        parts = original_command[5:].strip().split() 
        target_id = None
        amount = 0
        if message.reply_to_message:
            target_id = message.reply_to_message.from_user.id
            try: amount = int(parts[0])
            except: await message.answer("Блин дурак напиши еблан потом дать потом короче юзернейм и потом число еще короче можно в ответ ему написать типо еблан дать 67"); return
        elif len(parts) == 2:
            target_nickname = parts[0].replace("@", "")
            try: amount = int(parts[1])
            except: await message.answer("Блин дурак напиши еблан потом дать потом короче юзернейм и потом число еще короче можно в ответ ему написать типо еблан дать 67"); return
            target_id = await get_user_by_username(target_nickname)
            if not target_id: await message.answer("Пользователь ушел нахуй"); return
        else:
            await message.answer("Блин дурак напиши еблан потом дать потом короче юзернейм и потом число еще короче можно в ответ ему написать типо еблан дать 67"); return
        if target_id == user_id: await message.answer("Себе нельзя"); return
        if amount <= 0: await message.answer("Больше нуля"); return
        if user_data["balance"] < amount: await message.answer("Ты бомж ахах"); return
        target_data = await get_user(target_id)
        await update_user(user_id, "balance", user_data["balance"] - amount)
        await update_user(target_id, "balance", target_data["balance"] + amount)
        await message.answer("Я все сделал, хозяин!~")
    elif command.startswith("казино "):
        parts = original_command[7:].strip().split()
        if len(parts) != 2: await message.answer("Блин дурак напиши еблан потом казино потом свою ставку и красное или черное это типа на какой цвет ты ставишь понял да"); return
        try: bet_amount = int(parts[0])
        except: await message.answer("Блин дурак напиши еблан потом казино потом свою ставку и красное или черное это типа на какой цвет ты ставишь понял да"); return
        color = parts[1].lower()
        if color not in ["красное", "черное", "кр", "чр"]: await message.answer("Блин дурак напиши еблан потом казино потом свою ставку и красное или черное это типа на какой цвет ты ставишь понял да"); return
        if color in ["кр"]: color = "красное"
        if color in ["чр"]: color = "черное"
        if bet_amount <= 0: await message.answer("Больше нуля"); return
        if user_data["balance"] < bet_amount: await message.answer("Ты бомж ахах"); return
        result_color = random.choice(["красное", "черное"])
        if result_color == color:
            new_balance = user_data["balance"] + bet_amount
            await update_user(user_id, "balance", new_balance)
            await message.answer(f"Выпало {result_color} ты победил блин молодец")
        else:
            new_balance = user_data["balance"] - bet_amount
            await update_user(user_id, "balance", new_balance)
            await message.answer(f"Выпало {result_color} ты проебал лузер ебаный ахаха соси")

async def main():
    print("Бот запущен...")
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
