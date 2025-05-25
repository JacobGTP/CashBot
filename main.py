from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.utils import executor

import sqlite3
import asyncio
import os

BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)

# Połączenie z bazą danych SQLite
conn = sqlite3.connect("users.db")
cursor = conn.cursor()

# Tworzenie tabeli użytkowników
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    ref_by INTEGER,
    rewarded INTEGER DEFAULT 0
)
''')
conn.commit()

@dp.message_handler(commands=['start'])
async def start_handler(message: Message):
    args = message.get_args()
    user_id = message.from_user.id

    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if cursor.fetchone() is None:
        ref_by = int(args) if args.isdigit() and int(args) != user_id else None
        cursor.execute("INSERT INTO users (user_id, ref_by) VALUES (?, ?)", (user_id, ref_by))
        conn.commit()

        if ref_by:
            cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (ref_by,))
            if cursor.fetchone():
                await bot.send_message(ref_by, f"🎉 Ktoś dołączył z Twojego linku!")

    await message.answer("👋 Witaj w CashTap!
Zarabiaj za oglądanie TikToków i zapraszanie znajomych!")

@dp.message_handler(commands=['done'])
async def watched_handler(message: Message):
    user_id = message.from_user.id
    cursor.execute("SELECT ref_by, rewarded FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()

    if row and not row[1]:
        ref_by = row[0]
        if ref_by:
            cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (ref_by,))
            if cursor.fetchone():
                await bot.send_message(ref_by, f"🎁 Otrzymujesz +0.50 zł za zaproszenie użytkownika {user_id}!")
                cursor.execute("UPDATE users SET rewarded = 1 WHERE user_id = ?", (user_id,))
                conn.commit()

    await message.answer("✅ Zadanie wykonane!")

@dp.message_handler(commands=['ref'])
async def ref_link(message: Message):
    user_id = message.from_user.id
    link = f"https://t.me/CashTapBot?start={user_id}"
    await message.answer(f"📢 Twój link polecający:
{link}
Zaproś znajomych i zarabiaj!")

@dp.message_handler(commands=['ranking'])
async def ranking_handler(message: Message):
    cursor.execute('''
        SELECT ref_by, COUNT(*) as invites FROM users
        WHERE ref_by IS NOT NULL
        GROUP BY ref_by
        ORDER BY invites DESC
        LIMIT 10
    ''')
    ranking = cursor.fetchall()

    if not ranking:
        await message.answer("🔻 Brak zaproszeń w rankingu.")
        return

    text = "🏆 Ranking zapraszających:
"
    for i, (user_id, count) in enumerate(ranking, start=1):
        kwota = count * 0.5
        text += f"{i}. ID {user_id} — {count} zaproszeń (💸 {kwota:.2f} zł)
"

    await message.answer(text)

@dp.message_handler(commands=['zarobki'])
async def zarobki_handler(message: Message):
    cursor.execute('''
        SELECT ref_by, COUNT(*) * 0.5 as total_earned FROM users
        WHERE rewarded = 1 AND ref_by IS NOT NULL
        GROUP BY ref_by
        ORDER BY total_earned DESC
        LIMIT 10
    ''')
    ranking = cursor.fetchall()

    if not ranking:
        await message.answer("💤 Brak zarobków do wyświetlenia.")
        return

    text = "💰 Ranking zarobków:
"
    for i, (user_id, amount) in enumerate(ranking, start=1):
        text += f"{i}. ID {user_id} — {amount:.2f} zł
"

    await message.answer(text)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
