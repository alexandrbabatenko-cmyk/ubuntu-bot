from fastapi import FastAPI, Response, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from TonTools import Wallet, TonCenterClient
import uvicorn, json, os, logging, asyncio

app = FastAPI()

# --- БЛОК НАСТРОЕК TON ---
TON_API_KEY = "6cefc5f49a86d1dc85152a5cf3b2b743a50e06b6fa9f235c1619ca4a32117b13" 

# ВНИМАНИЕ: Используйте эти слова только для теста, потом замените на новые секретные!
MNEMONICS = ["ribbon", "galaxy", "lens", "series", "budget", "cover", "permit", "exit", "carpet", "crisp", "tomato", "room", "portion", "spoil", "six", "key", "obvious", "river", "worry", "sword", "party", "grass", "join", "spoil"]

UBUNTU_MASTER_ADDRESS = "EQA25M3v5zYC6-f8uyjFf1QPaZaNSS7WOJggo14DWsYiXmZc"
# -------------------------

logging.basicConfig(level=logging.INFO)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "db.json")
STATIC_DIR = os.path.join(BASE_DIR, "static")

if not os.path.exists(STATIC_DIR): os.makedirs(STATIC_DIR)
if not os.path.exists(DB_PATH):
    with open(DB_PATH, "w") as f: json.dump({}, f)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

async def send_ubuntu_tokens(destination_wallet, amount):
    try:
        # ИСПРАВЛЕНО: Добавлен https:// и путь /api/v2/ (для 2025 года)
        client = TonCenterClient(base_url='toncenter.com', api_key=TON_API_KEY)
        
        wallet = Wallet(provider=client, mnemonics=MNEMONICS, version='v4r2')
        
        tx = await wallet.transfer_jetton(
            destination_address=destination_wallet,
            jetton_master_address=UBUNTU_MASTER_ADDRESS,
            jettons_amount=amount 
        )
        return True, tx
    except Exception as e:
        logging.error(f"TON ERROR: {e}")
        return False, str(e)

@app.post("/earn/{score}")
async def earn(score: int, user_id: str = "guest"):
    try:
        with open(DB_PATH, "r") as f: db = json.load(f)
    except: db = {}
    if user_id not in db: db[user_id] = {"tokens": 0, "best": 0}
    db[user_id]["tokens"] += 1
    if score > db[user_id]["best"]: db[user_id]["best"] = score
    with open(DB_PATH, "w") as f: json.dump(db, f)
    return {"tokens": db[user_id]["tokens"], "best": db[user_id]["best"]}

@app.post("/withdraw")
async def withdraw(request: Request):
    data = await request.json()
    user_id = str(data.get("user_id"))
    wallet_addr = data.get("wallet")
    amount = int(data.get("amount"))
    with open(DB_PATH, "r") as f: db = json.load(f)
    if user_id in db and db[user_id]["tokens"] >= amount:
        success, result = await send_ubuntu_tokens(wallet_addr, amount)
        if success:
            db[user_id]["tokens"] -= amount
            with open(DB_PATH, "w") as f: json.dump(db, f)
            return {"status": "ok", "message": f"Успешно! {amount} UBUNTU отправлены."}
        else:
            return {"status": "error", "message": f"Ошибка транзакции: {result}"}
    return {"status": "error", "message": "Недостаточно очков!"}

@app.get("/", response_class=HTMLResponse)
async def index():
    return """
    <!DOCTYPE html><html><head><meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <!-- ИСПРАВЛЕНО: Ссылка на официальный SDK Telegram 2025 года -->
    <script src="telegram.org"></script>
    <style>
        body{margin:0;overflow:hidden;background:#4ec0ca;font-family:sans-serif;}
        #ui{position:absolute;top:20px;width:100%;text-align:center;color:white;font-size:20px;z-index:10;text-shadow:2px 2px 0 #000;font-weight:bold;}
        canvas{display:block;width:100vw;height:100vh;}
        #wBtn{position:absolute;bottom:20px;left:50%;transform:translateX(-50%);z-index:100;padding:12px 20px;background:gold;border:none;border-radius:10px;font-weight:bold;box-shadow:0 4px 0 #b8860b;cursor:pointer;}
    </style></head><body>
    <div id="ui">UBUNTU: <span id="t">0</span> | РЕКОРД: <span id="b">0</span></div>
    <button id="wBtn">ОБМЕНЯТЬ ОЧКИ</button>
    <canvas id="c"></canvas>
    <script>
        const tg = window.Telegram.WebApp;
        tg.expand();
        const user_id = tg.initDataUnsafe?.user?.id || "guest";
        const cvs=document.getElementById('c'); const ctx=cvs.getContext('2d');
        function res(){cvs.width=window.innerWidth; cvs.height=window.innerHeight;}
        window.onresize=res; res();
        let bird={x:80, y:200, v:0, g:0.45, score:0};
        let pipes=[]; let frame=0; let dead=false; 
        const bI=new Image(); bI.src='/static/bird.png';
        const pI=new Image(); pI.src='/static/pipe.png';
        const bg=new Image(); bg.src='/static/background.png';
        document.getElementById('wBtn').onclick = () => {
            const currentScore = parseInt(document.getElementById('t').innerText);
            if(currentScore < 100) return tg.showAlert("Минимум 100 очков!");
            const wallet = prompt("Введите ваш адрес TON кошелька:");
            if(wallet && wallet.length > 10) {
                fetch('/withdraw', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ user_id: user_id, wallet: wallet, amount: currentScore })
                })
                .then(r => r.json())
                .then(res => {
                    tg.showAlert(res.message);
                    if(res.status === "ok") location.reload();
                });
            }
        };
        function draw(){
            ctx.fillStyle = "#4ec0ca"; ctx.fillRect(0, 0, cvs.width, cvs.height);
            if(bg.complete) ctx.drawImage(bg, 0, 0, cvs.width, cvs.height);
            bird.v += 0.45; bird.y += bird.v;
            ctx.save(); ctx.translate(bird.x, bird.y);
            if(bI.complete && bI.width > 0) ctx.drawImage(bI, -25, -25, 50, 50);
            else { ctx.fillStyle="yellow"; ctx.fillRect(-25,-25,50,50); }
            ctx.restore();
            if(!dead) frame++;
            if(!dead && frame % 100 === 0) pipes.push({x:cvs.width, t:Math.random()*(cvs.height-350)+50, p:false});
            pipes.forEach((p,i)=>{
                if(!dead) p.x -= 4.5;
                if(pI.complete && pI.width > 0) {
                    ctx.drawImage(pI, p.x, 0, 80, p.t);
                    ctx.drawImage(pI, p.x, p.t + 190, 80, cvs.height);
                } else {
                    ctx.fillStyle = "green"; ctx.fillRect(p.x, 0, 80, p.t); ctx.fillRect(p.x, p.t + 190, 80, cvs.height);
                }
                if(!dead && bird.x+20>p.x && bird.x-20<p.x+80 && (bird.y-20<p.t || bird.y+20>p.t+190)) dead=true;
                if(!dead && !p.p && p.x < bird.x){
                    p.p = true; bird.score++;
                    fetch(`/earn/${bird.score}?user_id=${user_id}`, {method:'POST'})
                    .then(r=>r.json()).then(data=>{
                        document.getElementById('t').innerText = data.tokens;
                        document.getElementById('b').innerText = data.best;
                    });
                }
            });
            if(bird.y > cvs.height + 50) { bird.y=200; bird.v=0; pipes=[]; frame=0; dead=false; bird.score=0; }
            requestAnimationFrame(draw);
        }
        window.onmousedown = () => { if(!dead) bird.v=-8; };
        window.ontouchstart = () => { if(!dead) bird.v=-8; };
        draw();
    </script></body></html>
    """

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    # ИСПРАВЛЕНО: запуск сервера
    uvicorn.run(app, host="0.0.0.0", port=port)
