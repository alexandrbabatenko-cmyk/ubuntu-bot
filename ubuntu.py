from fastapi import FastAPI, Response, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn, json, os

# --- Конфигурация горячего кошелька ---
HOT_WALLET_ADDRESS = "UQDpW4gtsT9Y77oze2el7fpJ-9OFPtvgSLmZZ6a57gOgL4vZ"
HOT_WALLET_IPL_KEY = "6cefc5f49a86d1dc85152a5cf3b2b743a50e06b6fa9f235c1619ca4a32117b13"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MIN_EXCHANGE = 10000  # минимальный порог вывода

# Пути
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "db.json")
STATIC_DIR = os.path.join(BASE_DIR, "static")

if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR)

if not os.path.exists(DB_PATH):
    with open(DB_PATH, "w") as f:
        json.dump({"users": {}}, f)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)

# Начисление токенов
@app.post("/earn/{wallet}/{score}")
async def earn(wallet: str, score: int):
    with open(DB_PATH, "r") as f:
        db = json.load(f)
    if "users" not in db:
        db["users"] = {}

    user = db["users"].get(wallet, {"tokens": 0, "best": 0})
    user["tokens"] += 1
    if int(score) > int(user.get("best", 0)):
        user["best"] = int(score)
    db["users"][wallet] = user

    with open(DB_PATH, "w") as f:
        json.dump(db, f)
    return user

# Обмен токенов на Ubuntu с горячего кошелька
@app.post("/exchange")
async def exchange(request: Request):
    data = await request.json()
    wallet = data.get("wallet")
    if not wallet:
        return JSONResponse({"error": "wallet missing"}, status_code=400)

    with open(DB_PATH, "r") as f:
        db = json.load(f)

    user = db["users"].get(wallet)
    if not user or user.get("tokens", 0) < MIN_EXCHANGE:
        return JSONResponse(
            {"error": f"Минимум для вывода — {MIN_EXCHANGE} Ubuntu"},
            status_code=400
        )

    # Сколько отправляем
    send_amount = (user["tokens"] // MIN_EXCHANGE) * MIN_EXCHANGE
    user["tokens"] -= send_amount
    db["users"][wallet] = user

    with open(DB_PATH, "w") as f:
        json.dump(db, f)

    # --- Подключение к горячему кошельку (пример) ---
    # Здесь вставьте реальный вызов API сети TON или stonecenter для отправки Ubuntu
    # Используем HOT_WALLET_ADDRESS и HOT_WALLET_IPL_KEY
    # Например:
    # result = send_ubuntu(wallet_address=wallet, amount=send_amount, hot_wallet=HOT_WALLET_ADDRESS, ipl_key=HOT_WALLET_IPL_KEY)
    # Для примера вернем фиктивный tx_hash
    tx_hash = "FAKE_TX_HASH_1234567890"

    return {
        "sent": send_amount,
        "tokens": user["tokens"],
        "tx_hash": tx_hash
    }

# Игровая страница (логика птички, труб, фона оставлена как есть)
@app.get("/", response_class=HTMLResponse)
async def index():
    with open(os.path.join(BASE_DIR, "game.html"), "r", encoding="utf-8") as f:
        return f.read()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

