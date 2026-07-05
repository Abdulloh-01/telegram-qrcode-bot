import asyncio
import qrcode
from io import BytesIO
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import CommandStart, Command

# Для работы с цветом и логотипами
from PIL import Image, ImageDraw, ImageFont

TOKEN = "8771239009:AAFPp10GU-9Zcfvle4wGDc7Z3bY2Wg3sV2Y"

router = Router()

class QRStates(StatesGroup):
    menu = State()
    # Состояния для ввода данных
    url = State()
    wifi = State()
    vcard = State()
    telegram = State()
    whatsapp = State()
    email = State()
    phone = State()
    location = State()
    text = State()
    # Новые состояния кастомизации
    choose_color = State()
    choose_icon = State()

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

def color_menu():
    keyboard = [
        [InlineKeyboardButton(text="⚫ Черный", callback_data="color_black"),
         InlineKeyboardButton(text="🔵 Синий", callback_data="color_blue")],
        [InlineKeyboardButton(text="🟢 Зеленый", callback_data="color_green"),
         InlineKeyboardButton(text="🔴 Красный", callback_data="color_red")],
        [InlineKeyboardButton(text="⬅️ Отмена", callback_data="menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def icon_menu():
    keyboard = [
        [InlineKeyboardButton(text="❌ Без значка", callback_data="icon_none")],
        [InlineKeyboardButton(text="🌐 Браузер", callback_data="icon_🌐"),
         InlineKeyboardButton(text="✈️ Telegram", callback_data="icon_✈️")],
        [InlineKeyboardButton(text="💬 WhatsApp", callback_data="icon_💬"),
         InlineKeyboardButton(text="📶 Wi-Fi", callback_data="icon_📶")],
        [InlineKeyboardButton(text="⬅️ Отмена", callback_data="menu")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def make_qr(data: str, color: str = "black", icon: str = "none") -> BufferedInputFile:
    # Генерация базового QR-кода
    qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    
    # Создаем изображение (RGB, чтобы поддерживать цвета)
    img = qr.make_image(fill_color=color, back_color="white").convert("RGB")
    
    # Если выбран значок, рисуем его по центру
    if icon != "none":
        width, height = img.size
        # Размер центральной иконки (около 20% от размера QR-кода)
        icon_size = int(width * 0.2)
        
        # Белая подложка под иконку, чтобы код под ней не сливался
        icon_bg = Image.new("RGB", (icon_size, icon_size), "white")
        draw = ImageDraw.Draw(icon_bg)
        
        # Пытаемся нарисовать эмодзи-значок по центру подложки
        try:
            # Используем стандартный шрифт, если есть. Если нет — Pillow откатится на дефолтный
            font = ImageFont.load_default()
            # Масштабируем размер текста под иконку (приблизительно)
            font = font.font_variant(size=int(icon_size * 0.7))
        except:
            font = ImageFont.load_default()
            
        # Рисуем эмодзи-иконку
        draw.text((icon_size//2, icon_size//2), icon, fill=color, anchor="mm", font=font)
        
        # Вставляем иконку ровно по центру QR-кода
        pos = ((width - icon_size) // 2, (height - icon_size) // 2)
        img.paste(icon_bg, pos)

    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return BufferedInputFile(buf.read(), filename="qr.png")

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.set_state(QRStates.menu)
    await message.answer(
        "Привет! Я бот для генерации кастомных QR-кодов 🚀\nВыбери тип QR:",
        reply_markup=main_menu()
    )

@router.callback_query(F.data == "menu")
async def back_to_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(QRStates.menu)
    await callback.message.edit_text("Выбери тип QR:", reply_markup=main_menu())
    await callback.answer()

@router.callback_query(F.data.in_(["site", "wifi", "vcard", "telegram", "whatsapp", "email", "phone", "location", "text"]))
async def choose_type(callback: CallbackQuery, state: FSMContext):
    prompts = {
        "site": "🌐 Отправь ссылку на сайт\nПример: google.com",
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
    await callback.message.edit_text(prompts[callback.data], reply_markup=back_button())
    await callback.answer()

# Промежуточный шаг сохранения данных и выбора цвета
async def proceed_to_color(message: Message, state: FSMContext, data: str):
    await state.update_data(qr_data=data)
    await state.set_state(QRStates.choose_color)
    await message.answer("Отлично! Теперь выбери цвет для QR-кода:", reply_markup=color_menu())

@router.message(QRStates.url)
async def get_url(message: Message, state: FSMContext):
    url = message.text.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    await proceed_to_color(message, state, url)

@router.message(QRStates.wifi)
async def get_wifi(message: Message, state: FSMContext):
    try:
        ssid, pwd, auth = message.text.split(";")
        data = f"WIFI:T:{auth};S:{ssid};P:{pwd};;"
        await proceed_to_color(message, state, data)
    except:
        await message.reply("Неверный формат. Нужно: SSID;PASSWORD;WPA")

@router.message(QRStates.vcard)
async def get_vcard(message: Message, state: FSMContext):
    try:
        name, phone, email = message.text.split(";")
        data = f"BEGIN:VCARD\nVERSION:3.0\nFN:{name}\nTEL:{phone}\nEMAIL:{email}\nEND:VCARD"
        await proceed_to_color(message, state, data)
    except:
        await message.reply("Неверный формат. Нужно: Имя;Телефон;Email")

@router.message(QRStates.telegram)
async def get_telegram(message: Message, state: FSMContext):
    username = message.text.strip().replace("@", "")
    data = f"https://t.me/{username}"
    await proceed_to_color(message, state, data)

@router.message(QRStates.whatsapp)
async def get_whatsapp(message: Message, state: FSMContext):
    phone = message.text.strip().replace("+", "").replace(" ", "")
    data = f"https://wa.me/{phone}"
    await proceed_to_color(message, state, data)

@router.message(QRStates.email)
async def get_email(message: Message, state: FSMContext):
    try:
        email, subject = message.text.split(";")
        data = f"mailto:{email}?subject={subject}"
        await proceed_to_color(message, state, data)
    except:
        await message.reply("Неверный формат. Нужно: email;тема")

@router.message(QRStates.phone)
async def get_phone(message: Message, state: FSMContext):
    phone = message.text.strip()
    data = f"tel:{phone}"
    await proceed_to_color(message, state, data)

@router.message(QRStates.location)
async def get_location(message: Message, state: FSMContext):
    try:
        lat, lon = message.text.split(";")
        data = f"geo:{lat},{lon}"
        await proceed_to_color(message, state, data)
    except:
        await message.reply("Неверный формат. Нужно: широта;долгота")

@router.message(QRStates.text)
async def get_text(message: Message, state: FSMContext):
    await proceed_to_color(message, state, message.text)

# Обработка выбора цвета
@router.callback_query(QRStates.choose_color, F.data.startswith("color_"))
async def get_color(callback: CallbackQuery, state: FSMContext):
    color = callback.data.split("_")[1]
    await state.update_data(qr_color=color)
    await state.set_state(QRStates.choose_icon)
    await callback.message.edit_text("Почти готово! Выбери значок для центра QR-кода:", reply_markup=icon_menu())
    await callback.answer()

# Обработка выбора иконки и финальная генерация
@router.callback_query(QRStates.choose_icon, F.data.startswith("icon_"))
async def get_icon(callback: CallbackQuery, state: FSMContext):
    icon = callback.data.split("_")[1]
    user_data = await state.get_data()
    
    qr_data = user_data.get("qr_data")
    qr_color = user_data.get("qr_color", "black")
    
    # Удаляем старое сообщение с кнопками выбора иконки, чтобы не захламлять чат
    await callback.message.delete()
    
    # Генерация кастомного QR
    qr_file = make_qr(data=qr_data, color=qr_color, icon=icon)
    
    # Отправляем фото (без parse_mode, чтобы не было ошибок парсинга строк)
    await callback.message.answer_photo(
        photo=qr_file, 
        caption=f"Готово ✅\n\nДанные: {qr_data}\nЦвет: {qr_color}\nЗначок: {icon if icon != 'none' else 'Нет'}"
    )
    
    # Возврат в меню
    await state.clear()
    await state.set_state(QRStates.menu)
    await callback.message.answer("Сгенерировать ещё?", reply_markup=main_menu())
    await callback.answer()

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