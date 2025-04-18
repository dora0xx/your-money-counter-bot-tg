import json
import os
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import FSInputFile
from aiogram.types import ReplyKeyboardRemove
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
import matplotlib.pyplot as plt
from datetime import datetime
import asyncio

API_TOKEN = '7722288298:AAGHA-_cFfY9_sifkhy0NNUP9vjCtTsy42k'  # токен

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# Категории доходов и расходов
INCOME_CATEGORIES = ['Зарплата', 'Подарок', 'Другое']
EXPENSE_CATEGORIES = ['Еда', 'Спорт', 'Развлечения', 'Дом', 'Здоровье', 'Образование', 'Транспорт', 'Вредные привычки', 'Другое']

# Состояния FSM
class Transaction(StatesGroup):
    waiting_for_amount = State()
    waiting_for_category = State()

# Путь к папке с данными
DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)

# Обработчик /start
@dp.message(F.text == '/start')
async def start(message: Message):
    await message.answer("Привет! Используй /dohod, /rashod для ввода или /stats для статистики.")

# Обработчик доходов
@dp.message(F.text == '/dohod')
async def dohod(message: Message, state: FSMContext):
    await state.set_state(Transaction.waiting_for_amount)
    await state.update_data(type='income')
    await message.answer("Введи сумму дохода:")

# Обработчик расходов
@dp.message(F.text == '/rashod')
async def rashod(message: Message, state: FSMContext):
    await state.set_state(Transaction.waiting_for_amount)
    await state.update_data(type='expense')
    await message.answer("Введи сумму расхода:")

# Обработка суммы
@dp.message(Transaction.waiting_for_amount)
async def process_amount(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Пожалуйста, введи число.")
        return
    await state.update_data(amount=int(message.text))
    data = await state.get_data()
    if data['type'] == 'income':
        categories = INCOME_CATEGORIES
    else:
        categories = EXPENSE_CATEGORIES

    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=cat)] for cat in categories],
        resize_keyboard=True
    )
    await state.set_state(Transaction.waiting_for_category)
    await message.answer("Выбери категорию:", reply_markup=kb)

# Обработка категории и сохранение данных
@dp.message(Transaction.waiting_for_category)
async def process_category(message: Message, state: FSMContext):
    data = await state.get_data()
    amount = data['amount']
    trans_type = data['type']
    category = message.text
    user_id = str(message.from_user.id)
    now = datetime.now()
    month_key = now.strftime("%Y-%m")
    sign = 1 if trans_type == 'income' else -1
    final_amount = amount * sign

    filepath = os.path.join(DATA_DIR, f"{user_id}.json")

    # Загрузка данных
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            user_data = json.load(f)
    else:
        user_data = {}

    # Обновление данных
    if month_key not in user_data:
        user_data[month_key] = {"income": {}, "expense": {}}

    if category not in user_data[month_key][trans_type]:
        user_data[month_key][trans_type][category] = 0

    user_data[month_key][trans_type][category] += amount

    # Сохранение
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(user_data, f, ensure_ascii=False, indent=2)

    await message.answer(f"{'Доход' if sign > 0 else 'Расход'} сохранён!", reply_markup=ReplyKeyboardRemove())
    await state.clear()

# Команда /stats
@dp.message(F.text == '/stats')
async def stats(message: Message):
    await message.answer("Введи месяц в формате ГГГГ-ММ (например: 2025-04):")
@dp.message()
async def get_month(msg: Message):
        month = msg.text
        user_id = str(msg.from_user.id)
        filepath = os.path.join(DATA_DIR, f"{user_id}.json")

        if not os.path.exists(filepath):
            await msg.answer("Нет данных.")
            return

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        if month not in data:
            await msg.answer("Нет данных за этот месяц.")
            return

        for trans_type in ['income', 'expense']:
            stats = data[month].get(trans_type, {})
            if not stats:
                continue

            labels = list(stats.keys())
            values = list(stats.values())

            plt.figure(figsize=(6, 6))
            plt.pie(values, labels=[f"{l} ({v})" for l, v in zip(labels, values)], autopct='%1.1f%%')
            plt.title("Доходы" if trans_type == "income" else "Расходы")

            chart_path = os.path.join(DATA_DIR, f"{user_id}_{trans_type}.png")
            plt.savefig(chart_path)
            plt.close()

            photo = FSInputFile(chart_path)
            await msg.answer_photo(photo)

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())