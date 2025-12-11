import os
from flask import Flask, request
from aiogram import Bot, Dispatcher, types
import bot_logic
import requests

TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    raise RuntimeError("TOKEN не найден в Secrets")

WEBHOOK_PATH = f"/webhook/{TOKEN}"

try:
    from aiogram.client.default import DefaultBotProperties
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
except ImportError:
    bot = Bot(token=TOKEN, parse_mode="HTML")

dp = Dispatcher()

print("🔧 Начинаем регистрацию обработчиков...")
bot_logic.register_handlers(dp)
print("🔧 Обработчики зарегистрированы")

app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    return "Bot is running"

@app.route(WEBHOOK_PATH, methods=["POST"])
async def telegram_webhook():
    print("📨 Получен webhook запрос")
    try:
        data = request.get_json(force=True)
        print(f"📦 Данные: {data}")
        
        update = types.Update(**data)
        print(f"✅ Update обработан: {update.update_id}")
        
        # Обрабатываем напрямую async
        await dp.feed_update(bot, update)
        
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
    repl_url = os.environ.get("REPL_URL")
    if not repl_url:
        print("⚠️ REPL_URL не задан")
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
