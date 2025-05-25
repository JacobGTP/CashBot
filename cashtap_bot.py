
import logging
import sqlite3
from aiogram import Bot, Dispatcher, types, executor
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from datetime import datetime, timedelta

# === Ustawienia ===
BOT_TOKEN = "TU_WKLEJ_TOKEN"
ADMIN_ID = 123456789  # Twoje ID telegram (do /sendtask itd.)

# === Start bota ===
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(bot)
logging.basicConfig(level=logging.INFO)

# === Baza danych ===
conn = sqlite3.connect("cashtap.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    ref_by INTEGER,
    points INTEGER DEFAULT 0
)
""")
cursor.execute("""
CREATE TABLE IF NOT EXISTS completed_tasks (
    user_id INTEGER,
    task TEXT,
    completed_at TEXT,
    ip TEXT,
    UNIQUE(user_id, task, completed_at)
)
""")
conn.commit()

# === Przyciski ===
earn_btn = KeyboardButton("🎯 Zarabiaj")
balance_btn = KeyboardButton("💰 Saldo")
ref_btn = KeyboardButton("🤝 Poleć")
kb = ReplyKeyboardMarkup(resize_keyboard=True).add(earn_btn, balance_btn).add(ref_btn)

# === /start ===
@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    uid = message.from_user.id
    args = message.get_args()

    cursor.execute("SELECT * FROM users WHERE user_id = ?", (uid,))
    user = cursor.fetchone()

    if not user:
        ref_by = int(args) if args.isdigit() else None
        cursor.execute("INSERT INTO users (user_id, ref_by) VALUES (?, ?)", (uid, ref_by))
        conn.commit()
        if ref_by:
            cursor.execute("UPDATE users SET points = points + 5 WHERE user_id = ?", (ref_by,))
            conn.commit()
        await message.answer("👋 Witaj w CashTap! Otrzymujesz konto startowe.", reply_markup=kb)
    else:
        await message.answer("👋 Witaj ponownie!", reply_markup=kb)

# === /balance lub przycisk ===
@dp.message_handler(lambda m: m.text == "💰 Saldo")
@dp.message_handler(commands=['balance'])
async def balance_cmd(message: types.Message):
    uid = message.from_user.id
    cursor.execute("SELECT points FROM users WHERE user_id = ?", (uid,))
    row = cursor.fetchone()
    points = row[0] if row else 0
    await message.answer(f"💰 Twoje saldo: {points} punktów")

# === /ref lub przycisk ===
@dp.message_handler(lambda m: m.text == "🤝 Poleć")
@dp.message_handler(commands=['ref'])
async def ref_cmd(message: types.Message):
    uid = message.from_user.id
    link = f"https://t.me/CashTapRewardsBot?start={uid}"
    await message.answer(f"🔗 Twój link polecający:
{link}
Zaproś znajomych i zgarnij 5 punktów za każdą osobę!")

# === /earn lub przycisk ===
@dp.message_handler(lambda m: m.text == "🎯 Zarabiaj")
@dp.message_handler(commands=['earn'])
async def earn_cmd(message: types.Message):
    await message.answer("🎥 Zadanie:
Obejrzyj ten film: https://youtu.be/dQw4w9WgXcQ

Napisz "gotowe" po obejrzeniu, aby zdobyć 10 punktów.")

# === odpowiedź "gotowe" ===
@dp.message_handler(lambda m: m.text.lower() == "gotowe")
async def task_done(message: types.Message):
    uid = message.from_user.id
    task_id = "task1"
    now = datetime.utcnow()
    today = now.date().isoformat()

    ip = message.from_user.id  # zastępcze IP

    cursor.execute("SELECT COUNT(*) FROM completed_tasks WHERE user_id = ? AND DATE(completed_at) = ?", (uid, today))
    daily_count = cursor.fetchone()[0]
    if daily_count >= 3:
        await message.answer("🚫 Osiągnięto dzienny limit zadań (3 na dzień). Spróbuj jutro.")
        return

    cursor.execute("SELECT 1 FROM completed_tasks WHERE user_id = ? AND task = ? AND DATE(completed_at) = ?", (uid, task_id, today))
    if cursor.fetchone():
        await message.answer("⚠️ Już wykonałeś to zadanie dziś.")
        return

    cursor.execute("SELECT 1 FROM completed_tasks WHERE ip = ? AND DATE(completed_at) = ?", (str(ip), today))
    if cursor.fetchone():
        await message.answer("⚠️ To IP już dziś wykonało zadanie.")
        return

    cursor.execute("INSERT INTO completed_tasks (user_id, task, completed_at, ip) VALUES (?, ?, ?, ?)", (uid, task_id, now.isoformat(), str(ip)))
    cursor.execute("UPDATE users SET points = points + 10 WHERE user_id = ?", (uid,))
    conn.commit()
    await message.answer("✅ Zadanie zaliczone! +10 punktów dodane do salda.")

# === Uruchomienie ===
if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
