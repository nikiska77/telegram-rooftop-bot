import os
import asyncio
from flask import Flask, request
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
import bot_logic
import requests
from threading import Thread

TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    raise RuntimeError("TOKEN не найден в Secrets")

WEBHOOK_PATH = f"/webhook/{TOKEN}"

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

bot_logic.register_handlers(dp)

app = Flask(__name__)

# Создаём постоянный event loop
loop = asyncio.new_event_loop()

def start_loop():
    """Запускаем event loop в отдельном потоке"""
    asyncio.set_event_loop(loop)
    loop.run_forever()

# Запускаем loop в фоне
thread = Thread(target=start_loop, daemon=True)
thread.start()

@app.route("/", methods=["GET"])
def index():
    return "Bot is running"

@app.route(WEBHOOK_PATH, methods=["POST"])
def telegram_webhook():
    print("📨 Получен webhook запрос")
    try:
        data = request.get_json(force=True)
        print(f"📦 Данные: {data}")

        update = types.Update(**data)
        print(f"✅ Update обработан: {update.update_id}")

        # Запускаем в постоянном loop
        asyncio.run_coroutine_threadsafe(
            dp.feed_update(bot, update),
            loop
        )

        return {"ok": True}
    except Exception as e:
        print(f"❌ Ошибка в webhook: {e}")
        import traceback
        traceback.print_exc()
        return {"ok": False}, 400

@app.route("/status", methods=["GET"])
def status():
    return {"status": "ok"}

def set_webhook_sync():
    """Устанавливает webhook синхронно"""
    repl_url = os.environ.get("REPL_URL")
    if not repl_url:
        print("⚠️ REPL_URL не задан, webhook не установлен")
        return

    webhook_url = f"{repl_url}/webhook/{TOKEN}"

    try:
        response = requests.post(
            f"https://api.telegram.org/bot{TOKEN}/setWebhook",
            data={"url": webhook_url}
        )
        result = response.json()
        if result.get("ok"):
            print(f"✅ Webhook установлен: {webhook_url}")
        else:
            print(f"❌ Ошибка webhook: {result}")
    except Exception as e:
        print(f"❌ Не удалось установить webhook: {e}")

if __name__ == "__main__":
    set_webhook_sync()

    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False)
