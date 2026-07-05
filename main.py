import asyncio
import qrcode
from io import BytesIO
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import CommandStart, Command
from dotenv import load_dotenv
import os

load_dotenv()

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID"))


router = Router()

class QRStates(StatesGroup):
    menu = State()
    url = State()
    wifi = State()
    vcard = State()
    telegram = State()
    whatsapp = State()
    email = State()
    phone = State()
    location = State()
    text = State()

def main_menu():
    keyboard = [
        [InlineKeyboardButton(text="🌐 Сайт", callback_data="site"),
         InlineKeyboardButton(text="📶 Wi-Fi", callback_data="wifi")],
        [InlineKeyboardButton(text="👤 Контакт vCard", callback_data="vcard"),
         InlineKeyboardButton(text="✈️ Telegram", callback_data="telegram")],
        [InlineKeyboardButton(text="💬 WhatsApp", callback_data="whatsapp"),
         InlineKeyboardButton(text="📧 Email", callback_data="email")],
        [InlineKeyboardButton(text="📞 Телефон", callback_data="phone"),
         InlineKeyboardButton(text="📍 Геолокация", callback_data="location")],
        [InlineKeyboardButton(text="📝 Текст", callback_data="text")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def back_button():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="menu")]
    ])

def make_qr(data: str) -> BufferedInputFile:
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")

    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return BufferedInputFile(buf.read(), filename="qr.png")

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.set_state(QRStates.menu)
    await message.answer(
        "Привет! Я бот для генерации QR-кодов 🚀\nВыбери тип QR:",
        reply_markup=main_menu()
    )

@router.callback_query(F.data == "menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    await state.set_state(QRStates.menu)
    await callback.message.edit_text("Выбери тип QR:", reply_markup=main_menu())
    await callback.answer()

@router.callback_query(F.data.in_(["site", "wifi", "vcard", "telegram", "whatsapp", "email", "phone", "location", "text"]))
async def choose_type(callback: CallbackQuery, state: FSMContext):
    prompts = {
        "site": "🌐 Отправь ссылку на сайт\nПример: https://google.com",
        "wifi": "📶 Отправь данные Wi-Fi в формате:\nSSID;PASSWORD;WPA\nПример: MyWiFi;12345678;WPA",
        "vcard": "👤 Отправь контакт в формате:\nИмя;Телефон;Email\nПример: Иван Иванов;+79991234567;ivan@mail.ru",
        "telegram": "✈️ Отправь username Telegram без @\nПример: durov",
        "whatsapp": "💬 Отправь номер WhatsApp с кодом страны\nПример: +79991234567",
        "email": "📧 Отправь email и тему через ;\nПример: test@mail.ru;Привет",
        "phone": "📞 Отправь номер телефона\nПример: +79991234567",
        "location": "📍 Отправь координаты через ;\nПример: 55.7558;37.6176",
        "text": "📝 Отправь любой текст"
    }

    state_map = {
        "site": QRStates.url, "wifi": QRStates.wifi, "vcard": QRStates.vcard,
        "telegram": QRStates.telegram, "whatsapp": QRStates.whatsapp, "email": QRStates.email,
        "phone": QRStates.phone, "location": QRStates.location, "text": QRStates.text
    }

    await state.set_state(state_map[callback.data])
    await callback.message.edit_text(prompts[callback.data], reply_markup=back_button(), parse_mode="Markdown")
    await callback.answer()

async def send_qr_and_back(message: Message, state: FSMContext, data: str):
    qr_file = make_qr(data)
    await message.answer_photo(qr_file, caption=f"Готово ✅\n\nДанные: {data}", parse_mode="Markdown")
    await state.set_state(QRStates.menu)
    await message.answer("Сгенерировать ещё?", reply_markup=main_menu())

@router.message(QRStates.url)
async def get_url(message: Message, state: FSMContext):
    url = message.text.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    await send_qr_and_back(message, state, url)

@router.message(QRStates.wifi)
async def get_wifi(message: Message, state: FSMContext):
    try:
        ssid, pwd, auth = message.text.split(";")
        data = f"WIFI:T:{auth};S:{ssid};P:{pwd};;"
        await send_qr_and_back(message, state, data)
    except:
        await message.reply("Неверный формат. Нужно: SSID;PASSWORD;WPA", parse_mode="Markdown")

@router.message(QRStates.vcard)
async def get_vcard(message: Message, state: FSMContext):
    try:
        name, phone, email = message.text.split(";")
        data = f"BEGIN:VCARD\nVERSION:3.0\nFN:{name}\nTEL:{phone}\nEMAIL:{email}\nEND:VCARD"
        await send_qr_and_back(message, state, data)
    except:
        await message.reply("Неверный формат. Нужно: Имя;Телефон;Email", parse_mode="Markdown")

@router.message(QRStates.telegram)
async def get_telegram(message: Message, state: FSMContext):
    username = message.text.strip().replace("@", "")
    data = f"https://t.me/{username}"
    await send_qr_and_back(message, state, username)

@router.message(QRStates.whatsapp)
async def get_whatsapp(message: Message, state: FSMContext):
    phone = message.text.strip().replace("+", "")
    data = f"https://wa.me/{phone}"
    await send_qr_and_back(message, state, data)

@router.message(QRStates.email)
async def get_email(message: Message, state: FSMContext):
    try:
        email, subject = message.text.split(";")
        data = f"mailto:{email}?subject={subject}"
        await send_qr_and_back(message, state, data)
    except:
        await message.reply("Неверный формат. Нужно: email;тема", parse_mode="Markdown")

@router.message(QRStates.phone)
async def get_phone(message: Message, state: FSMContext):
    phone = message.text.strip()
    data = f"tel:{phone}"
    await send_qr_and_back(message, state, data)

@router.message(QRStates.location)
async def get_location(message: Message, state: FSMContext):
    try:
        lat, lon = message.text.split(";")
        data = f"geo:{lat},{lon}"
        await send_qr_and_back(message, state, data)
    except:
        await message.reply("Неверный формат. Нужно: широта;долгота", parse_mode="Markdown")

@router.message(QRStates.text)
async def get_text(message: Message, state: FSMContext):
    await send_qr_and_back(message, state, message.text)

@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Отменено. /start чтобы начать заново")

async def main():
    bot = Bot(token=TOKEN)
    dp = Dispatcher()
    dp.include_router(router)
    print("Бот запущен на aiogram 3...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())