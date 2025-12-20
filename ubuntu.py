from fastapi import FastAPI, Response, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn, json, os, requests

# 🔐 Горячий кошелёк (fallback, чтобы сервер НЕ ПАДАЛ)
HOT_WALLET_ADDRESS = os.getenv(
    "HOT_WALLET_ADDRESS",
    "UQDpW4gtsT9Y77oze2el7fpJ-9OFPtvgSLmZZ6a57gOgL4vZ"
)
HOT_WALLET_KEY = os.getenv(
    "HOT_WALLET_KEY",
    "6cefc5f49a86d1dc85152a5cf3b2b743a50e06b6fa9f235c1619ca4a32117b13"
)

MIN_EXCHANGE = 10000

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

os.makedirs(STATIC_DIR, exist_ok=True)

if not os.path.exists(DB_PATH):
    with open(DB_PATH, "w") as f:
        json.dump({"users": {}}, f)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)

# 🎯 Начисление токенов
@app.post("/earn/{wallet}/{score}")
async def earn(wallet: str, score: int):
    if not wallet:
        return {"tokens": 0}

    with open(DB_PATH, "r") as f:
        db = json.load(f)

    user = db["users"].get(wallet, {"tokens": 0, "best": 0})
    user["tokens"] += 1
    user["best"] = max(user.get("best", 0), score)

    db["users"][wallet] = user

    with open(DB_PATH, "w") as f:
        json.dump(db, f)

    return user

# 💸 Отправка UBUNTU (как у тебя работало)
def send_ubuntu(from_address, key, to_address, amount):
    url = "https://toncenter.com/api/v2/sendTransaction"
    payload = {
        "from": from_address,
        "to": to_address,
        "amount": amount,
        "secret": key
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        print("[TONCENTER]", r.text)
        return r.ok
    except Exception as e:
        print("[ERROR]", e)
        return False

@app.post("/exchange")
async def exchange(request: Request):
    data = await request.json()
    wallet = data.get("wallet")

    if not wallet:
        return JSONResponse({"error": "wallet missing"}, status_code=400)

    with open(DB_PATH, "r") as f:
        db = json.load(f)

    user = db["users"].get(wallet)
    tokens = user["tokens"] if user else 0

    if tokens < MIN_EXCHANGE:
        return JSONResponse(
            {"error": f"Минимум для вывода — {MIN_EXCHANGE} UBUNTU"},
            status_code=400
        )

    send_amount = (tokens // MIN_EXCHANGE) * MIN_EXCHANGE
    user["tokens"] -= send_amount
    db["users"][wallet] = user

    with open(DB_PATH, "w") as f:
        json.dump(db, f)

    send_ubuntu(HOT_WALLET_ADDRESS, HOT_WALLET_KEY, wallet, send_amount)

    return {"sent": send_amount, "tokens": user["tokens"]}

# 🎮 ИГРА — ЦЕЛИКОМ
@app.get("/", response_class=HTMLResponse)
async def index():
    return """
<!DOCTYPE html><html><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<script src="https://telegram.org/js/telegram-web-app.js"></script>
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

const cvs=document.getElementById('c');
const ctx=cvs.getContext('2d');

function res(){cvs.width=window.innerWidth; cvs.height=window.innerHeight;}
window.onresize=res; res();

let bird={x:80,y:200,v:0,g:0.45,score:0,angle:0,wingPhase:0};
let pipes=[]; let frame=0; let dead=false;

const bI=new Image(); bI.src='/static/bird.png';
const pI=new Image(); pI.src='/static/pipe.png';
const bg=new Image(); bg.src='/static/background.png';

function draw(){
ctx.fillStyle="#4ec0ca";
ctx.fillRect(0,0,cvs.width,cvs.height);
if(bg.complete) ctx.drawImage(bg,0,0,cvs.width,cvs.height);

bird.v+=bird.g;
bird.y+=bird.v;
bird.v*=0.98;
bird.angle+=(bird.v*6-bird.angle)*0.1;
bird.wingPhase+=0.2;

ctx.save();
ctx.translate(bird.x,bird.y);
ctx.rotate(bird.angle*Math.PI/180);
if(bI.complete) ctx.drawImage(bI,-25,-25,50,50);
else {ctx.fillStyle="yellow";ctx.fillRect(-25,-25,50,50);}
ctx.restore();

if(!dead) frame++;
if(!dead && frame%100===0)
pipes.push({x:cvs.width,t:Math.random()*(cvs.height-350)+50,p:false});

pipes.forEach(p=>{
if(!dead) p.x-=4.5;
ctx.drawImage(pI,p.x,0,80,p.t);
ctx.drawImage(pI,p.x,p.t+190,80,cvs.height);

if(!dead && bird.x+20>p.x && bird.x-20<p.x+80 &&
(bird.y-20<p.t || bird.y+20>p.t+190)) dead=true;

if(!dead && !p.p && p.x<bird.x){
p.p=true; bird.score++;
const w=localStorage.getItem('wallet');
if(w) fetch('/earn/'+w+'/'+bird.score,{method:'POST'})
.then(r=>r.json()).then(d=>t.innerText=d.tokens);
}});

if(bird.y>cvs.height+50){
bird.y=200; bird.v=0; pipes=[]; frame=0; dead=false; bird.score=0;
}
requestAnimationFrame(draw);
}

window.onmousedown=()=>{if(!dead) bird.v=-8;}
window.ontouchstart=()=>{if(!dead) bird.v=-8;}
draw();

exchangeBtn.onclick=async()=>{
let w=localStorage.getItem('wallet');
if(!w){w=prompt("Введите кошелёк");if(!w)return;localStorage.setItem('wallet',w);}
const r=await fetch('/exchange',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({wallet:w})});
const d=await r.json();
alert(d.error||`Отправлено ${d.sent} UBUNTU`);
t.innerText=d.tokens||0;
};
</script>
</body></html>
"""

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
