import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import database as db

# ========== НАСТРОЙКИ ==========
TOKEN = "8880226145:AAEwZutZYKMNB8VgIHiZpvaxt8A8DJGh_7s"          # Замените на токен от @BotFather
ADMIN_ID = 1546393339               # Ваш Telegram ID (узнайте у @userinfobot)
PROMASTER_ID = 987654321           # Telegram ID прораба

# ========== ИНИЦИАЛИЗАЦИЯ ==========
logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
db.init_db()

# ========== СОСТОЯНИЯ ==========
class CreateObject(StatesGroup):
    address = State()
    stages = State()

class AddIncome(StatesGroup):
    object_id = State()
    stage_name = State()
    amount = State()

class PurchaseMaterial(StatesGroup):
    name = State()
    quantity = State()
    price = State()

class MoveMaterial(StatesGroup):
    material = State()
    quantity = State()
    object_id = State()

class UseMaterial(StatesGroup):
    object_id = State()
    material = State()
    quantity = State()

class PaySalary(StatesGroup):
    object_id = State()
    work_type = State()
    amount = State()

# ========== КЛАВИАТУРЫ ==========
def admin_keyboard():
    buttons = [
        [KeyboardButton(text="📋 Объекты")],
        [KeyboardButton(text="➕ Новый объект")],
        [KeyboardButton(text="💰 Финансы")],
        [KeyboardButton(text="🧱 Склад")],
        [KeyboardButton(text="📊 Отчёт")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def promaster_keyboard():
    buttons = [
        [KeyboardButton(text="📋 Объекты")],
        [KeyboardButton(text="🧱 Расход материала")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def finance_keyboard():
    buttons = [
        [KeyboardButton(text="➕ Приход")],
        [KeyboardButton(text="🛒 Закуп материала")],
        [KeyboardButton(text="💸 ЗП рабочим")],
        [KeyboardButton(text="🔙 Назад")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def warehouse_keyboard():
    buttons = [
        [KeyboardButton(text="📦 Остатки на складе")],
        [KeyboardButton(text="🚚 Переместить на объект")],
        [KeyboardButton(text="🔙 Назад")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

# ========== ОБРАБОТЧИКИ ==========
@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("👋 Хозяин, выберите действие:", reply_markup=admin_keyboard())
    elif message.from_user.id == PROMASTER_ID:
        await message.answer("👷 Прораб, выберите действие:", reply_markup=promaster_keyboard())
    else:
        await message.answer("⛔ Доступ запрещён.")

@dp.message(lambda m: m.text == "🔙 Назад")
async def back_cmd(message: types.Message):
    if message.from_user.id == ADMIN_ID:
        await message.answer("Главное меню:", reply_markup=admin_keyboard())
    elif message.from_user.id == PROMASTER_ID:
        await message.answer("Главное меню:", reply_markup=promaster_keyboard())

# ---------- Объекты ----------
@dp.message(lambda m: m.text == "➕ Новый объект" and m.from_user.id == ADMIN_ID)
async def new_object(message: types.Message, state: FSMContext):
    await message.answer("Введите адрес объекта (например: Ленина 15, кв 5):")
    await state.set_state(CreateObject.address)

@dp.message(CreateObject.address)
async def get_address(message: types.Message, state: FSMContext):
    await state.update_data(address=message.text)
    await message.answer("Введите этапы и планы в формате:\nДемонтаж:50000\nШтукатурка:100000\n\nИли отправьте 'пропустить'")
    await state.set_state(CreateObject.stages)

@dp.message(CreateObject.stages)
async def get_stages(message: types.Message, state: FSMContext):
    data = await state.get_data()
    address = data['address']
    obj_id = db.add_object(address)
    if message.text.lower() != "пропустить":
        lines = message.text.split('\n')
        for line in lines:
            if ':' in line:
                parts = line.split(':')
                stage_name = parts[0].strip()
                try:
                    plan_amount = float(parts[1].strip())
                    db.add_stage(obj_id, stage_name, plan_amount)
                except:
                    pass
    await message.answer(f"✅ Объект '{address}' создан!")
    await state.clear()

@dp.message(lambda m: m.text == "📋 Объекты")
async def list_objects(message: types.Message):
    objects = db.get_objects()
    if not objects:
        await message.answer("Нет объектов.")
        return
    text = "📋 *Объекты:*\n\n" + "\n".join(f"🏠 {obj['address']}" for obj in objects)
    await message.answer(text, parse_mode="Markdown")
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=obj['address'], callback_data=f"view_mat_{obj['object_id']}")] for obj in objects
    ])
    await message.answer("Выберите объект для просмотра остатков материалов:", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data.startswith("view_mat_"))
async def view_materials(callback: types.CallbackQuery):
    obj_id = int(callback.data.split('_')[2])
    obj = db.get_object_by_id(obj_id)
    materials = db.get_site_materials(obj_id)
    if not materials:
        await callback.message.answer(f"На объекте '{obj['address']}' нет материалов.")
    else:
        text = f"📦 *Остатки на объекте {obj['address']}:*\n\n" + "\n".join(f"• {m['material']}: {m['quantity']} шт" for m in materials)
        await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()

# ---------- Финансы ----------
@dp.message(lambda m: m.text == "💰 Финансы" and m.from_user.id == ADMIN_ID)
async def finance_menu(message: types.Message):
    await message.answer("Финансовые операции:", reply_markup=finance_keyboard())

@dp.message(lambda m: m.text == "➕ Приход")
async def income_start(message: types.Message, state: FSMContext):
    objects = db.get_objects()
    if not objects:
        await message.answer("Нет объектов.")
        return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=obj['address'], callback_data=f"inc_{obj['object_id']}")] for obj in objects
    ])
    await message.answer("Выберите объект:", reply_markup=keyboard)
    await state.set_state(AddIncome.object_id)

@dp.callback_query(AddIncome.object_id)
async def income_object(callback: types.CallbackQuery, state: FSMContext):
    obj_id = int(callback.data.split('_')[1])
    await state.update_data(object_id=obj_id)
    await callback.message.answer("Введите название этапа (например: Демонтаж):")
    await state.set_state(AddIncome.stage_name)
    await callback.answer()

@dp.message(AddIncome.stage_name)
async def income_stage(message: types.Message, state: FSMContext):
    await state.update_data(stage_name=message.text)
    await message.answer("Введите сумму (руб):")
    await state.set_state(AddIncome.amount)

@dp.message(AddIncome.amount)
async def income_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text)
        data = await state.get_data()
        db.add_finance_record(data['object_id'], "income", amount, f"Этап: {data['stage_name']}")
        await message.answer(f"✅ Приход {amount} руб добавлен.")
        await state.clear()
    except:
        await message.answer("❌ Ошибка. Введите число.")

@dp.message(lambda m: m.text == "🛒 Закуп материала")
async def purchase_start(message: types.Message, state: FSMContext):
    await message.answer("Введите название материала:")
    await state.set_state(PurchaseMaterial.name)

@dp.message(PurchaseMaterial.name)
async def purchase_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите количество (в мешках/штуках):")
    await state.set_state(PurchaseMaterial.quantity)

@dp.message(PurchaseMaterial.quantity)
async def purchase_qty(message: types.Message, state: FSMContext):
    try:
        qty = float(message.text)
        await state.update_data(quantity=qty)
        await message.answer("Введите цену за единицу (руб):")
        await state.set_state(PurchaseMaterial.price)
    except:
        await message.answer("❌ Введите число.")

@dp.message(PurchaseMaterial.price)
async def purchase_price(message: types.Message, state: FSMContext):
    try:
        price = float(message.text)
        data = await state.get_data()
        total = data['quantity'] * price
        db.add_material_to_warehouse(data['name'], data['quantity'], price)
        db.add_finance_record(0, "expense_material", total, f"Закуп: {data['name']} {data['quantity']}шт")
        await message.answer(f"✅ Закуплен {data['name']}: {data['quantity']} шт на {total} руб")
        await state.clear()
    except:
        await message.answer("❌ Ошибка.")

@dp.message(lambda m: m.text == "💸 ЗП рабочим")
async def salary_start(message: types.Message, state: FSMContext):
    objects = db.get_objects()
    if not objects:
        await message.answer("Нет объектов.")
        return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=obj['address'], callback_data=f"sal_{obj['object_id']}")] for obj in objects
    ])
    await message.answer("Выберите объект:", reply_markup=keyboard)
    await state.set_state(PaySalary.object_id)

@dp.callback_query(PaySalary.object_id)
async def salary_object(callback: types.CallbackQuery, state: FSMContext):
    obj_id = int(callback.data.split('_')[1])
    await state.update_data(object_id=obj_id)
    work_types = db.get_salary_work_types()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=wt, callback_data=f"wt_{wt}")] for wt in work_types
    ])
    await callback.message.answer("Выберите вид работ:", reply_markup=keyboard)
    await state.set_state(PaySalary.work_type)
    await callback.answer()

@dp.callback_query(PaySalary.work_type)
async def salary_worktype(callback: types.CallbackQuery, state: FSMContext):
    work_type = callback.data.split('_')[1]
    await state.update_data(work_type=work_type)
    await callback.message.answer("Введите сумму выплаты (руб):")
    await state.set_state(PaySalary.amount)
    await callback.answer()

@dp.message(PaySalary.amount)
async def salary_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text)
        data = await state.get_data()
        db.add_finance_record(data['object_id'], "expense_salary", amount, f"Вид работ: {data['work_type']}")
        await message.answer(f"✅ Выплачена ЗП {amount} руб за {data['work_type']}")
        await state.clear()
    except:
        await message.answer("❌ Ошибка.")

# ---------- Склад ----------
@dp.message(lambda m: m.text == "🧱 Склад" and m.from_user.id == ADMIN_ID)
async def warehouse_menu(message: types.Message):
    await message.answer("Управление складом:", reply_markup=warehouse_keyboard())

@dp.message(lambda m: m.text == "📦 Остатки на складе")
async def show_warehouse(message: types.Message):
    materials = db.get_warehouse()
    if not materials:
        await message.answer("Склад пуст.")
        return
    text = "📦 *Остатки на складе:*\n\n" + "\n".join(f"• {m['material']}: {m['quantity']} шт (цена {m['price_per_unit']} руб/шт)" for m in materials)
    await message.answer(text, parse_mode="Markdown")

@dp.message(lambda m: m.text == "🚚 Переместить на объект")
async def move_start(message: types.Message, state: FSMContext):
    materials = db.get_warehouse()
    if not materials:
        await message.answer("Склад пуст.")
        return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=m['material'], callback_data=f"mv_{m['material']}")] for m in materials
    ])
    await message.answer("Выберите материал:", reply_markup=keyboard)
    await state.set_state(MoveMaterial.material)

@dp.callback_query(MoveMaterial.material)
async def move_material(callback: types.CallbackQuery, state: FSMContext):
    material = callback.data.split('_')[1]
    await state.update_data(material=material)
    await callback.message.answer("Введите количество для перемещения:")
    await state.set_state(MoveMaterial.quantity)
    await callback.answer()

@dp.message(MoveMaterial.quantity)
async def move_qty(message: types.Message, state: FSMContext):
    try:
        qty = float(message.text)
        await state.update_data(quantity=qty)
        objects = db.get_objects()
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=obj['address'], callback_data=f"mobj_{obj['object_id']}")] for obj in objects
        ])
        await message.answer("На какой объект переместить?", reply_markup=keyboard)
        await state.set_state(MoveMaterial.object_id)
    except:
        await message.answer("❌ Введите число.")

@dp.callback_query(MoveMaterial.object_id)
async def move_object(callback: types.CallbackQuery, state: FSMContext):
    obj_id = int(callback.data.split('_')[1])
    data = await state.get_data()
    success = db.remove_from_warehouse(data['material'], data['quantity'])
    if success:
        db.add_material_to_site(obj_id, data['material'], data['quantity'])
        await callback.message.answer(f"✅ Перемещено {data['quantity']} {data['material']} на объект.")
    else:
        await callback.message.answer("❌ На складе недостаточно материала.")
    await state.clear()
    await callback.answer()

# ---------- Отчёт ----------
@dp.message(lambda m: m.text == "📊 Отчёт" and m.from_user.id == ADMIN_ID)
async def report_start(message: types.Message):
    objects = db.get_objects()
    if not objects:
        await message.answer("Нет объектов.")
        return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=obj['address'], callback_data=f"rep_{obj['object_id']}")] for obj in objects
    ])
    await message.answer("Выберите объект для отчёта:", reply_markup=keyboard)

@dp.callback_query(lambda c: c.data.startswith("rep_"))
async def show_report(callback: types.CallbackQuery):
    obj_id = int(callback.data.split('_')[1])
    obj = db.get_object_by_id(obj_id)
    summary = db.get_object_finance_summary(obj_id)
    stages = db.get_stages_by_object(obj_id)
    materials = db.get_site_materials(obj_id)

    report = f"📊 *Отчёт по объекту: {obj['address']}*\n\n"
    report += f"💰 Приходы: {summary['total_income']} руб\n"
    report += f"🧱 Расход на материалы: {summary['total_expense_materials']} руб\n"
    report += f"👷 Расход на ЗП: {summary['total_expense_salary']} руб\n"
    report += f"⚖️ *Сальдо: {summary['balance']} руб*\n\n"
    if stages:
        report += "📋 *Этапы (план):*\n" + "\n".join(f"• {s['stage_name']}: {s['plan_amount']} руб" for s in stages) + "\n\n"
    if materials:
        report += "📦 *Остатки материалов:*\n" + "\n".join(f"• {m['material']}: {m['quantity']} шт" for m in materials)
    else:
        report += "📦 Материалов на объекте нет."

    await callback.message.answer(report, parse_mode="Markdown")
    await callback.answer()

# ---------- Прораб: расход материала ----------
@dp.message(lambda m: m.text == "🧱 Расход материала" and m.from_user.id == PROMASTER_ID)
async def use_start(message: types.Message, state: FSMContext):
    objects = db.get_objects()
    if not objects:
        await message.answer("Нет объектов.")
        return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=obj['address'], callback_data=f"useo_{obj['object_id']}")] for obj in objects
    ])
    await message.answer("На каком объекте израсходовали материал?", reply_markup=keyboard)
    await state.set_state(UseMaterial.object_id)

@dp.callback_query(UseMaterial.object_id)
async def use_object(callback: types.CallbackQuery, state: FSMContext):
    obj_id = int(callback.data.split('_')[1])
    await state.update_data(object_id=obj_id)
    materials = db.get_site_materials(obj_id)
    if not materials:
        await callback.message.answer("На этом объекте нет материалов для списания.")
        await state.clear()
        await callback.answer()
        return
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=m['material'], callback_data=f"usem_{m['material']}")] for m in materials
    ])
    await callback.message.answer("Какой материал израсходовали?", reply_markup=keyboard)
    await state.set_state(UseMaterial.material)
    await callback.answer()

@dp.callback_query(UseMaterial.material)
async def use_material_select(callback: types.CallbackQuery, state: FSMContext):
    material = callback.data.split('_')[1]
    await state.update_data(material=material)
    await callback.message.answer("Введите израсходованное количество:")
    await state.set_state(UseMaterial.quantity)
    await callback.answer()

@dp.message(UseMaterial.quantity)
async def use_quantity(message: types.Message, state: FSMContext):
    try:
        qty = float(message.text)
        data = await state.get_data()
        success = db.remove_material_from_site(data['object_id'], data['material'], qty)
        if success:
            await message.answer(f"✅ Списано {qty} {data['material']} с объекта.")
        else:
            await message.answer("❌ Нельзя списать больше, чем есть на объекте.")
        await state.clear()
    except:
        await message.answer("❌ Введите число.")

# ========== ЗАПУСК ==========
async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
