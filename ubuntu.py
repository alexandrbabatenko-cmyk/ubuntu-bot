from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from TonTools import Wallet, TonCenterClient
import uvicorn, json, os, logging

app = FastAPI()

# ---------------- TON CONFIG ----------------
TON_API_KEY = "PUT_YOUR_API_KEY_HERE"

MNEMONICS = [
    "ribbon","galaxy","lens","series","budget","cover",
    "permit","exit","carpet","crisp","tomato","room",
    "portion","spoil","six","key","obvious","river",
    "worry","sword","party","grass","join","spoil"
]

UBUNTU_MASTER_ADDRESS = "EQA25M3v5zYC6-f8uyjFf1QPaZaNSS7WOJggo14DWsYiXmZc"
# --------------------------------------------

logging.basicConfig(level=logging.INFO)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
DB_PATH = os.path.join(BASE_DIR, "db.json")

os.makedirs(STATIC_DIR, exist_ok=True)

if not os.path.exists(DB_PATH):
    with open(DB_PATH, "w") as f:
        json.dump({}, f)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# ---------------- DATABASE ----------------
def load_db():
    try:
        with open(DB_PATH, "r") as f:
            return json.load(f)
    except:
        return {}

def save_db(db):
    with open(DB_PATH, "w") as f:
        json.dump(db, f)

# ---------------- TON SEND ----------------
async def send_ubuntu_tokens(destination_wallet, amount):
    try:
        client = TonCenterClient(
            base_url="https://toncenter.com/api/v2/",
            api_key=TON_API_KEY
        )
        wallet = Wallet(provider=client, mnemonics=MNEMONICS, version="v4r2")
        tx = await wallet.transfer_jetton(
            destination_address=destination_wallet,
            jetton_master_address=UBUNTU_MASTER_ADDRESS,
            jettons_amount=amount
        )
        return True, tx
    except Exception as e:
        logging.error(e)
        return False, str(e)

# ---------------- API ----------------
@app.get("/stats")
async def stats(user_id: str = "guest"):
    db = load_db()
    if user_id not in db:
        db[user_id] = {"tokens": 0, "best": 0}
        save_db(db)
    return db[user_id]

@app.post("/earn/{score}")
async def earn(score: int, user_id: str = "guest"):
    db = load_db()
    if user_id not in db:
        db[user_id] = {"tokens": 0, "best": 0}

    db[user_id]["tokens"] += 1
    if score > db[user_id]["best"]:
        db[user_id]["best"] = score

    save_db(db)
    return db[user_id]

@app.post("/withdraw")
async def withdraw(request: Request):
    data = await request.json()
    user_id = str(data.get("user_id"))
    wallet_addr = data.get("wallet")
    amount = int(data.get("amount"))

    db = load_db()
    if user_id not in db or db[user_id]["tokens"] < amount:
        return {"status": "error", "message": "Недостаточно очков"}

    success, result = await send_ubuntu_tokens(wallet_addr, amount)
    if success:
        db[user_id]["tokens"] -= amount
        save_db(db)
        return {"status": "ok", "message": f"{amount} UBUNTU отправлены"}
    return {"status": "error", "message": result}

# ---------------- FRONTEND ----------------
@app.get("/", response_class=HTMLResponse)
async def index():
    return """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0,user-scalable=no">
<script src="https://telegram.org/js/telegram-web-app.js"></script>
<style>
body{margin:0;overflow:hidden;background:#4ec0ca;font-family:sans-serif}
#ui{position:absolute;top:20px;width:100%;text-align:center;color:white;font-size:20px;font-weight:bold;text-shadow:2px 2px 0 #000}
canvas{display:block}
#wBtn{position:absolute;bottom:20px;left:50%;transform:translateX(-50%);
padding:12px 20px;background:gold;border:none;border-radius:10px;font-weight:bold}
</style>
</head>
<body>

<div id="ui">UBUNTU: <span id="t">0</span> | РЕКОРД: <span id="b">0</span></div>
<button id="wBtn">ОБМЕНЯТЬ ОЧКИ</button>
<canvas id="c"></canvas>

<script>
const tg = window.Telegram?.WebApp;
if (tg) tg.expand();

const user_id = tg?.initDataUnsafe?.user?.id || "guest";

fetch(`/stats?user_id=${user_id}`)
.then(r=>r.json())
.then(d=>{
  t.innerText=d.tokens;
  b.innerText=d.best;
});

const c = document.getElementById('c');
const ctx = c.getContext('2d');
function resize(){c.width=innerWidth;c.height=innerHeight}
onresize=resize; resize();

let bird={x:80,y:200,v:0,score:0};
let pipes=[],frame=0,dead=false;

const bI=new Image(); bI.src='/static/bird.png';
const pI=new Image(); pI.src='/static/pipe.png';

wBtn.onclick=()=>{
  if(+t.innerText<100) return alert("Минимум 100");
  const w=prompt("TON кошелек:");
  if(!w) return;
  fetch('/withdraw',{method:'POST',headers:{'Content-Type':'application/json'},
  body:JSON.stringify({user_id:user_id,wallet:w,amount:+t.innerText})})
  .then(r=>r.json()).then(a=>alert(a.message));
};

function loop(){
  ctx.fillStyle='#4ec0ca';
  ctx.fillRect(0,0,c.width,c.height);

  bird.v+=0.5; bird.y+=bird.v;
  ctx.fillStyle='yellow';
  ctx.fillRect(bird.x-20,bird.y-20,40,40);

  if(!dead) frame++;
  if(frame%100===0) pipes.push({x:c.width,t:Math.random()*(c.height-300)+50,p:false});

  pipes.forEach(p=>{
    p.x-=4;
    ctx.fillStyle='green';
    ctx.fillRect(p.x,0,80,p.t);
    ctx.fillRect(p.x,p.t+180,80,c.height);

    if(!p.p && p.x<bird.x){
      p.p=true; bird.score++;
      fetch(`/earn/${bird.score}?user_id=${user_id}`,{method:'POST'})
      .then(r=>r.json()).then(d=>{
        t.innerText=d.tokens; b.innerText=d.best;
      });
    }
  });

  if(bird.y>c.height){bird.y=200;bird.v=0;pipes=[];frame=0}
  requestAnimationFrame(loop);
}
onclick=()=>bird.v=-8;
loop();
</script>
</body>
</html>
"""

# ---------------- RUN ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
