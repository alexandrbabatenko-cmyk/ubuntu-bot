from fastapi import FastAPI, Response, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn, json, os, requests
from dotenv import load_dotenv

# Загружаем ENV
load_dotenv()

HOT_WALLET_ADDRESS = os.getenv("HOT_WALLET_ADDRESS")
HOT_WALLET_KEY = os.getenv("HOT_WALLET_KEY")
TOKEN_CONTRACT_ADDRESS = os.getenv("TOKEN_CONTRACT_ADDRESS")
MIN_EXCHANGE = int(os.getenv("MIN_EXCHANGE", 10000))

# Проверка ENV
if not HOT_WALLET_ADDRESS or not HOT_WALLET_KEY or not TOKEN_CONTRACT_ADDRESS:
    raise RuntimeError(
        "ENV переменные HOT_WALLET_ADDRESS, HOT_WALLET_KEY и TOKEN_CONTRACT_ADDRESS должны быть заданы!"
    )

# FastAPI
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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
    if not wallet:
        return {"tokens": 0}

    with open(DB_PATH, "r") as f:
        db = json.load(f)
    if "users" not in db:
        db["users"] = {}

    user = db["users"].get(wallet, {"tokens": 0, "best": 0})
    user["tokens"] += 1
    if score > user.get("best", 0):
        user["best"] = score

    db["users"][wallet] = user
    with open(DB_PATH, "w") as f:
        json.dump(db, f)
    return user

# Отправка UBUNTU напрямую через ключ
def send_ubuntu(from_address, key, to_address, amount):
    url = "https://toncenter.com/api/v2/sendTransaction"
    payload = {
        "from": from_address,
        "to": to_address,
        "amount": amount,
        "secret": key
    }
    try:
        resp = requests.post(url, json=payload, timeout=10)
        if resp.ok:
            print(f"[MAINNET] Успешно отправлено {amount} UBUNTU с {from_address} на {to_address}")
            return True
        else:
            print(f"[ERROR] TonCenter ответил: {resp.text}")
            return False
    except Exception as e:
        print(f"[EXCEPTION] Ошибка отправки: {e}")
        return False

# Обмен токенов на UBUNTU
@app.post("/exchange")
async def exchange(request: Request):
    data = await request.json()
    wallet = data.get("wallet")
    if not wallet:
        return JSONResponse({"error": "wallet missing"}, status_code=400)

    with open(DB_PATH, "r") as f:
        db = json.load(f)

    user = db["users"].get(wallet)
    tokens = user.get("tokens", 0) if user else 0

    if tokens < MIN_EXCHANGE:
        return JSONResponse(
            {"error": f"Минимум для вывода — {MIN_EXCHANGE} UBUNTU"},
            status_code=400
        )

    send_amount = (tokens // MIN_EXCHANGE) * MIN_EXCHANGE

    success = send_ubuntu(HOT_WALLET_ADDRESS, HOT_WALLET_KEY, wallet, send_amount)
    if success:
        user["tokens"] -= send_amount
        db["users"][wallet] = user
        with open(DB_PATH, "w") as f:
            json.dump(db, f)
    else:
        return JSONResponse({"error": "Ошибка отправки UBUNTU. Попробуйте позже."}, status_code=500)

    return {"sent": send_amount, "tokens": user["tokens"]}

# Игровая страница (весь игровой процесс сохранён!)
@app.get("/", response_class=HTMLResponse)
async def index():
    return """
<!DOCTYPE html><html><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<script src="telegram.org"></script>
<style>
body{margin:0;overflow:hidden;background:#4ec0ca;font-family:sans-serif;}
#ui{position:absolute;top:20px;width:100%;text-align:center;color:white;font-size:24px;z-index:10;text-shadow:2px 2px 0 #000;font-weight:bold;display:flex;justify-content:center;align-items:center;gap:15px;}
canvas{display:block;width:100vw;height:100vh;}
#exchangeBtn{padding:6px 12px;font-size:16px;}
</style>
</head><body>
<div id="ui"><span id="t">0</span> Ubuntu <button id="exchangeBtn">Обменять</button></div>
<canvas id="c"></canvas>
<script>
const tg = window.Telegram ? window.Telegram.WebApp : null;
if(tg){ tg.expand(); tg.ready(); }

const cvs=document.getElementById('c'); const ctx=cvs.getContext('2d');
function res(){cvs.width=window.innerWidth; cvs.height=window.innerHeight;}
window.onresize=res; res();

let bird={x:80, y:200, w:50, h:50, v:0, g:0.45, score:0, angle:0, wingPhase:0};
let pipes=[]; let frame=0; let dead=false;

const bI=new Image(); bI.src='/static/bird.png';
const pI=new Image(); pI.src='/static/pipe.png';
const bg=new Image(); bg.src='/static/background.png';

function draw(){
    ctx.fillStyle = "#4ec0ca";
    ctx.fillRect(0, 0, cvs.width, cvs.height);
    if(bg.complete) ctx.drawImage(bg, 0, 0, cvs.width, cvs.height);

    bird.v += bird.g;
    bird.y += bird.v;
    bird.v *= 0.98;
    bird.angle += (bird.v * 6 - bird.angle) * 0.1;
    bird.wingPhase += 0.2;
    let wingOffset = Math.sin(bird.wingPhase) * 5;

    ctx.save(); 
    ctx.translate(bird.x, bird.y);
    ctx.rotate((bird.angle + wingOffset) * Math.PI / 180);
    if(bI.complete && bI.width > 0) ctx.drawImage(bI, -25, -25, 50, 50);
    else { ctx.fillStyle="yellow"; ctx.fillRect(-25,-25,50,50); }
    ctx.restore();

    if(!dead) frame++;
    if(!dead && frame % 100 === 0) pipes.push({x:cvs.width, t:Math.random()*(cvs.height-350)+50, p:false});

    pipes.forEach((p,i)=>{
        if(!dead) p.x -= 4.5;
        if(pI.complete && pI.width > 0){
            ctx.save(); ctx.translate(p.x + 40, p.t); ctx.scale(1, -1); ctx.drawImage(pI, -40, 0, 80, p.t); ctx.restore();
            ctx.drawImage(pI, p.x, p.t + 190, 80, cvs.height);
        } else { ctx.fillStyle="green"; ctx.fillRect(p.x, 0, 80, p.t); ctx.fillRect(p.x, p.t + 190, 80, cvs.height); }

        if(!dead && bird.x+20>p.x && bird.x-20<p.x+80 && (bird.y-20<p.t || bird.y+20>p.t+190)) dead=true;

        if(!dead && !p.p && p.x < bird.x){
            p.p = true; bird.score++;
            const wallet = localStorage.getItem('wallet');
            if(wallet){
                fetch('/earn/'+wallet+'/'+bird.score,{method:'POST'}).then(r=>r.json()).then(data=>{document.getElementById('t').innerText=data.tokens;});
            }
        }
    });

    if(bird.y > cvs.height + 50){ bird.y=200; bird.v=0; pipes=[]; frame=0; dead=false; bird.score=0; bird.wingPhase=0; }
    requestAnimationFrame(draw);
}

window.onmousedown = () => { if(!dead) bird.v=-8; };
window.ontouchstart = () => { if(!dead) bird.v=-8; };
draw();

document.getElementById('exchangeBtn').onclick = async () => {
    let wallet = localStorage.getItem('wallet');
    if(!wallet){ wallet = prompt("Введите ваш кошелек для получения Ubuntu:"); if(!wallet) return; localStorage.setItem('wallet', wallet); }
    const res = await fetch('/exchange',{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({wallet})
    });
    const data = await res.json();
    if(data.error) alert("Ошибка: "+data.error);
    else { alert("Отправлено "+data.sent+" Ubuntu на ваш кошелек! Остаток очков: "+data.tokens); document.getElementById('t').innerText = data.tokens; }
};
</script>
</body></html>
"""

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
