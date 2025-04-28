import logging
import psycopg2
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# PostgreSQL connection setup
DB_NAME = "postgres"
DB_USER = "tgbot"
DB_PASSWORD = "2303"
DB_HOST = "localhost"
DB_PORT = "5432"


def get_db_connection():
    conn = psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        host=DB_HOST,
        port=DB_PORT
    )
    return conn


# Create table if not exists
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            user_id BIGINT UNIQUE,
            first_name VARCHAR(100),
            last_name VARCHAR(100)
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()


# Initialize database
init_db()

# Bot token
BOT_TOKEN = "Token"

# Initialize bot and dispatcher
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# States
class Form(StatesGroup):
    first_name = State()
    last_name = State()


# Command handlers
@dp.message(Command("start"))
async def start_handler(message: Message, state: FSMContext):
    await message.answer("Salom! Ismingizni kiriting:")
    await state.set_state(Form.first_name)


@dp.message(Command("myinfo"))
async def myinfo_handler(message: Message):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(f"SELECT first_name, last_name FROM users WHERE user_id = {message.from_user.id}")
    user_data = cursor.fetchone()

    cursor.close()
    conn.close()

    if user_data:
        first_name, last_name = user_data
        await message.answer(f"Sizning ma'lumotlaringiz:\nIsm: {first_name}\nFamiliya: {last_name}")
    else:
        await message.answer("Siz hali ma'lumot kiritmadingiz. /start buyrug'ini bosing.")


# First name handler
@dp.message(Form.first_name)
async def process_first_name(message: Message, state: FSMContext):
    await state.update_data(first_name=message.text)
    await message.answer("Familiyangizni kiriting:")
    await state.set_state(Form.last_name)


# Last name handler
@dp.message(Form.last_name)
async def process_last_name(message: Message, state: FSMContext):
    data = await state.get_data()
    first_name = data.get("first_name", "")
    last_name = message.text

    # Save to PostgreSQL
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Check if user exists
        cursor.execute("SELECT 1 FROM users WHERE user_id = %s", (message.from_user.id,))
        exists = cursor.fetchone()

        if exists:
            # Update existing user
            cursor.execute(
                "UPDATE users SET first_name = %s, last_name = %s WHERE user_id = %s",
                (first_name, last_name, message.from_user.id)
            )
        else:
            # Create new user
            cursor.execute(
                "INSERT INTO users (user_id, first_name, last_name) VALUES (%s, %s, %s)",
                (message.from_user.id, first_name, last_name)
            )

        conn.commit()
        await message.answer(f"Rahmat! Ma'lumotlaringiz saqlandi:\nIsm: {first_name}\nFamiliya: {last_name}")

    except Exception as e:
        conn.rollback()
        await message.answer("Xatolik yuz berdi. Iltimos, qayta urinib ko'ring.")
        logging.error(f"Database error: {e}")

    finally:
        cursor.close()
        conn.close()
        await state.clear()


# Any other message handler
@dp.message()
async def any_message_handler(message: Message):
    await message.answer("Botdan foydalanish uchun /start buyrug'ini bosing.")


# Start the bot
async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())