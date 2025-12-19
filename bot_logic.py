# bot_logic.py
import json
import os
import traceback
from aiogram import types, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
# from aiogram.dispatcher.filters import Command
from aiogram.filters import Command

# файлы, функции load_json/save_json, etc. — вставь сюда свою реализацию
PARTICIPANTS_FILE = "participants.json"
EVENT_FILE = "event.json"
SETTINGS_FILE = "settings.json"

TOKEN = os.getenv("TOKEN")
if TOKEN is None:
    raise ValueError("❗ TOKEN not found in environment variables!")

ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
MAX_SEATS = int(os.getenv("MAX_SEATS", "10"))

def load_json(filename, default):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_participants():
    data = load_json(PARTICIPANTS_FILE, {})
    # нормализуем: хотим словарь { "user_id": "Full Name" }
    if isinstance(data, list):
        new = {}
        for item in data:
            if isinstance(item, dict) and "id" in item and "name" in item:
                new[str(item["id"])] = item["name"]
            else:
                new[str(item)] = "Unknown"
        save_participants(new)
        return new
    if not isinstance(data, dict):
        save_participants({})
        return {}
    return data

def save_participants(data):
    if not isinstance(data, dict):
        data = {}
    save_json(PARTICIPANTS_FILE, data)

def load_event():
    return load_json(EVENT_FILE, {})

def save_event(data):
    save_json(EVENT_FILE, data)

def load_settings():
    default = {"max_seats": MAX_SEATS}
    return load_json(SETTINGS_FILE, default)

def save_settings(data):
    save_json(SETTINGS_FILE, data)

def get_max_seats():
    settings = load_settings()
    return settings.get("max_seats", MAX_SEATS)
    
# ----------------------------
# Клавиатуры
# ----------------------------
def get_main_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Я иду", callback_data="attend")],
            [InlineKeyboardButton(text="Отменить запись", callback_data="cancel")]
        ]
    )


# ----------------------------
# Регистрация обработчиков
# ----------------------------

# Здесь — все твои обработчики, но оформленные как функции регистрации:
def register_handlers(dp):
    print("🔧 Начинаем регистрацию обработчиков...")
    # ----------------------------
    # /start
    # ----------------------------
    # @dp.message_handler(commands=["start"])
    @dp.message(Command("start"))
    async def start_cmd(message: types.Message):
        print(f"📩 Получена команда /start от пользователя {message.from_user.id}")
        print(f"👤 Имя: {message.from_user.full_name}")
        try:
            participants = load_participants()
            remaining = get_max_seats() - len(participants)
    
            event = load_event()
            event_text = ""
            if event:
                event_text = (
                    f"🎬 <b>{event.get('title','')}</b>\n"
                    f"📅 {event.get('date','')}\n"
                    f"⏰ {event.get('time','')}\n"
                    f"📍 {event.get('location','')}\n\n"
                )
    
            await message.answer(
                "Доступные команды:\n"
                "/start — перезапустить меню\n"
                "/event — информация о событии",
            )
    
            await message.answer(
                f"{event_text}"
                f"Всего мест: {get_max_seats()}\n"
                f"Осталось: {remaining}\n\n"
                f"Нажмите кнопку ниже 👇",
                reply_markup=get_main_keyboard()
            )
        except Exception as e:
            print(f"❌ Ошибка в start_cmd: {e}")            
            traceback.print_exc()
                # await message.answer(f"Привет! Осталось мест: {remaining}")

    # пример callback handler (adapt to your real handlers)
    # @dp.callback_query_handler(lambda c: c.data == "attend")
    @dp.callback_query(F.data == "attend")
    async def attend(callback: types.CallbackQuery):
        print(f"🔘 Нажата кнопка 'Я иду' от {callback.from_user.id}")
        user = callback.from_user
        participants = load_participants()

        print(f"📋 Текущие участники: {participants}")
        print(f"🔍 Проверка: {str(user.id)} in {list(participants.keys())}")
        
        try:
            await callback.answer()
        except Exception:
            pass

        try:
            user = callback.from_user
            participants = load_participants()

            if len(participants) >= get_max_seats():
                await callback.answer("Все места заняты ❌", show_alert=True)
                return

            if str(user.id) in participants:
                try:
                    await callback.answer("Вы уже записаны ✔️", show_alert=True)
                    await callback.message.answer("⚠️ Вы уже записаны на это мероприятие")
                except Exception as e:
                    print(f"Ошибка callback.answer: {e}")
                    # Отправляем обычное сообщение если alert не сработал
                    await callback.message.answer("Вы уже записаны ✔️")
                return
                

            participants[str(user.id)] = user.full_name or user.username or "NoName"
            save_participants(participants)

            remaining = get_max_seats() - len(participants)

            await callback.answer("Вы записаны! ✔️", show_alert=True)

            await callback.message.answer(
                f"{user.full_name} записался.\nОсталось мест: {remaining}"
            )

        except Exception as e:
            print("Error in attend:", e)
            try:
                await callback.answer("Ошибка. Попробуйте позже.", show_alert=True)
            except Exception:
                pass

        # ----------------------------
        # Кнопка "Отменить запись"
        # ----------------------------
    # @dp.callback_query_handler(lambda c: c.data == "cancel")
    @dp.callback_query(F.data == "cancel")
    async def cancel_attendance(callback: CallbackQuery):
        try:
            await callback.answer()
        except Exception:
            pass
    
        try:
            user = callback.from_user
            participants = load_participants()
    
            if str(user.id) not in participants:
                await callback.answer("Вы не были записаны.", show_alert=True)
                return
    
            del participants[str(user.id)]
            save_participants(participants)
    
            remaining = get_max_seats() - len(participants)
    
            await callback.answer("Запись отменена.", show_alert=True)
            await callback.message.answer(
                f"{user.full_name} отменил запись.\nОсталось мест: {remaining}"
            )
    
        except Exception as e:
            print("Error in cancel:", e)
            try:
                await callback.answer("Ошибка.", show_alert=True)
            except Exception:
                pass

    # ----------------------------
    # /list (только для админа)
    # ----------------------------
    # @dp.message_handler(lambda m: m.text == "/list")
    @dp.message(Command("list"))
    async def show_list(message: types.Message):
        if message.from_user.id != ADMIN_ID:
            await message.answer("У вас нет прав.")
            return
    
        participants = load_participants()
        if not participants:
            await message.answer("Никто не записался.")
            return
    
        text = "Список участников:\n\n"
        for user_id, name in participants.items():
            text += f"• {name} (ID: {user_id})\n"
    
        await message.answer(text)

    # ----------------------------
    # /set_event title | date | time | location
    # ----------------------------
    # @dp.message_handler(lambda m: m.text.startswith("/set_event"))
    @dp.message(Command("set_event"))
    async def set_event_handler(message: types.Message):
        if message.from_user.id != ADMIN_ID:
            await message.answer("Нет прав.")
            return
    
        try:
            _, rest = message.text.split(" ", 1)
            title, date, time, location = [x.strip() for x in rest.split("|")]
        except:
            await message.answer(
                "Формат:\n"
                "/set_event Название | дата | время | адрес\n\n"
                "Пример:\n"
                "/set_event Интерстеллар | 5 февраля | 19:00 | Бат-Ям"
            )
            return
    
        event_data = {
            "title": title,
            "date": date,
            "time": time,
            "location": location
        }
        save_event(event_data)
    
        await message.answer("Событие обновлено ✔️")

    # ----------------------------
    # /event — показать инфо
    # ----------------------------
    # @dp.message_handler(lambda m: m.text == "/event")
    @dp.message(Command("event"))
    async def show_event(message: types.Message):
        event = load_event()
        if not event:
            await message.answer("Информация о событии не задана.")
            return
    
        text = (
            f"🎬 <b>{event['title']}</b>\n"
            f"📅 {event['date']}\n"
            f"⏰ {event['time']}\n"
            f"📍 {event['location']}"
        )
    
        await message.answer(text)

    # ----------------------------
    # /post — создание поста в канал
    # ----------------------------
    @dp.message(Command("post"))
    async def create_post(message: types.Message):
        if message.from_user.id != ADMIN_ID:
            await message.answer("Нет прав.")
            return

        event = load_event()
        if not event:
            await message.answer("Сначала установите событие через /set_event")
            return

        participants = load_participants()
        remaining = get_max_seats() - len(participants)

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="📝 Записаться", url="https://t.me/niki_niki_bot?start=register")]
            ]
        )

        text = (
            f"🎬 <b>{event['title']}</b>\n\n"
            f"📅 {event['date']}\n"
            f"⏰ {event['time']}\n"
            f"📍 {event['location']}\n\n"
            f"Всего мест: {get_max_seats()}\n"
            f"Свободно: {remaining}"
        )
        
        await message.answer(
            text,
            reply_markup=keyboard
        )

        await message.answer("Перешли это сообщение в канал!")

    
    # ----------------------------
    # /clear_all — полная очистка
    # ----------------------------
    # @dp.message_handler(lambda m: m.text == "/clear_all")
    @dp.message(Command("clear_all"))
    async def clear_all(message: types.Message):
        if message.from_user.id != ADMIN_ID:
            await message.answer("Нет прав.")
            return
    
        try:
            if os.path.exists(PARTICIPANTS_FILE):
                os.remove(PARTICIPANTS_FILE)
            if os.path.exists(EVENT_FILE):
                os.remove(EVENT_FILE)
    
            save_participants({})
            save_event({})
    
            await message.answer("✔️ Данные полностью очищены.")
    
        except Exception as e:
            print("Error in clear_all:", e)
            await message.answer("Ошибка при очистке.")


    # ----------------------------
    # /set_seats количество
    # ----------------------------

    @dp.message(Command("set_seats"))
    async def set_seats_handler(message: types.Message):
        if message.from_user.id != ADMIN_ID:
            await message.answer("Нет прав.")
            return
    
        try:
            _, count = message.text.split(" ", 1)
            count = int(count)
            
            if count < 1 or count > 1000:
                await message.answer("Количество мест должно быть от 1 до 1000")
                return
            
            settings = load_settings()
            settings["max_seats"] = count
            save_settings(settings)
            
            await message.answer(f"✅ Максимальное количество мест изменено на {count}")
        
        except (ValueError, IndexError):
            await message.answer(
                "Формат:\n"
                "/set_seats 15\n\n"
                "Пример: /set_seats 20"
            )


    # ----------------------------
    # /broadcast текст сообщения
    # ----------------------------

    @dp.message(Command("broadcast"))
    async def broadcast_handler(message: types.Message):
        if message.from_user.id != ADMIN_ID:
            await message.answer("Нет прав.")
            return
        
        try:
            _, text = message.text.split(" ", 1)
        except ValueError:
            await message.answer(
                "Формат:\n"
                "/broadcast Текст сообщения\n\n"
                "Пример:\n"
                "/broadcast Напоминаем, событие завтра в 19:00!"
            )
            return
        
        participants = load_participants()
        
        if not participants:
            await message.answer("Нет записавшихся участников")
            return
        
        success = 0
        failed = 0
        
        await message.answer(f"Начинаю рассылку {len(participants)} участникам...")
        
        for user_id in participants.keys():
            try:
                await message.bot.send_message(chat_id=int(user_id), text=text)
                success += 1
            except Exception as e:
                print(f"Ошибка отправки {user_id}: {e}")
                failed += 1
        
        await message.answer(
            f"✅ Рассылка завершена\n"
            f"Успешно: {success}\n"
            f"Ошибок: {failed}"
        )
