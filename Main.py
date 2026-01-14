import logging
import sqlite3
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import ChatJoinRequest
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

# --- НАСТРОЙКИ ---
TOKEN = "8581071819:AAH4cPMOhWS7a_qG23j9XFVtBJsUcXRZ3z8"
ADMIN_IDS = [7697867470, 7702419270] 

bot = Bot(token=TOKEN)
dp = Dispatcher()

class AdminStates(StatesGroup):
    waiting_for_broadcast = State()

# --- БАЗА ДАННЫХ ---
def init_db():
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
    conn.commit()
    conn.close()

def add_user(user_id):
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

# --- ОБРАБОТЧИКИ ---

@dp.message(Command("start"))
async def start(msg: types.Message):
    add_user(msg.from_user.id)
    await msg.answer("Привет! Я помогу тебе вступить в канал после проверки на робота.")

@dp.message(Command("admin"), F.from_user.id.in_(ADMIN_IDS))
async def admin_panel(msg: types.Message):
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="📢 Рассылка", callback_data="broadcast"))
    await msg.answer("🛠 Админ-панель:", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "broadcast", F.from_user.id.in_(ADMIN_IDS))
async def start_broadcast(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("Введите текст сообщения для рассылки всем пользователям:")
    await state.set_state(AdminStates.waiting_for_broadcast)

@dp.message(AdminStates.waiting_for_broadcast)
async def do_broadcast(msg: types.Message, state: FSMContext):
    conn = sqlite3.connect("database.db")
    users = conn.execute("SELECT user_id FROM users").fetchall()
    conn.close()
    
    count = 0
    for user in users:
        try:
            await bot.send_message(user[0], msg.text)
            count += 1
            await asyncio.sleep(0.05) # Защита от спам-фильтра Telegram
        except:
            continue
    
    await msg.answer(f"✅ Рассылка завершена!\nСообщение получили: {count} человек.")
    await state.clear()

@dp.chat_join_request()
async def join_req(req: ChatJoinRequest):
    add_user(req.from_user.id)
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="Я НЕ РОБОТ 🤖", callback_data=f"ok_{req.chat.id}"))
    
    try:
        await bot.send_message(
            req.from_user.id, 
            f"Привет! Чтобы вступить в канал **{req.chat.title}**, подтверди, что ты не робот.", 
            reply_markup=kb.as_markup()
        )
    except:
        # Если у пользователя закрыта личка
        for admin in ADMIN_IDS:
            await bot.send_message(admin, f"⚠️ Не могу написать пользователю с ID {req.from_user.id}. Пусть сначала напишет боту /start")

@dp.callback_query(F.data.startswith("ok_"))
async def approve(call: types.CallbackQuery):
    chat_id = int(call.data.split("_")[1])
    try:
        await bot.approve_chat_join_request(chat_id, call.from_user.id)
        await call.message.edit_text("✅ Проверка пройдена! Вы приняты в канал.")
    except Exception as e:
        await call.answer("Ошибка! Проверь, что бот — админ канала.", show_alert=True)

async def main():
    init_db()
    logging.info("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
  
