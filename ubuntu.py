from fastapi import FastAPI, Response, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn, json, os, requests

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Пути
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "db.json")
STATIC_DIR = os.path.join(BASE_DIR, "static")

if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR)

if not os.path.exists(DB_PATH):
    with open(DB_PATH, "w") as f: json.dump({"tokens": 0, "best": 0}, f)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Конфиг для TON (твой кошелек и контракт)
TON_WALLET = "UQDpW4gtsT9Y77oze2el7fpJ-9OFPtvgSLmZZ6a57gOgL4vZ"
TOKEN_CONTRACT = "EQA25M3v5zYC6-f8uyjFf1QPaZaNSS7WOJggo14DWsYiXmZc"
EXCHANGE_RATE = 10  # 1 очко = 10 токенов

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)

@app.post("/earn/{score}")
async def earn(score: int):
    try:
        with open(DB_PATH, "r") as f: db = json.load(f)
    except: db = {"tokens": 0, "best": 0}
    
    db["tokens"] = db.get("tokens", 0) + 1
    if int(score) > int(db.get("best", 0)):
        db["best"] = int(score)
        
    with open(DB_PATH, "w") as f: json.dump(db, f)
    return db

@app.post("/exchange")
async def exchange(request: Request):
    """
    Эндпоинт для обмена очков на реальные Ubuntu
    """
    data = await request.json()
    user_wallet = data.get("wallet")
    
    if not user_wallet:
        return JSONResponse({"error": "wallet missing"}, status_code=400)
    
    # Загружаем текущие очки
    with open(DB_PATH, "r") as f:
        db = json.load(f)
    
    tokens = db.get("tokens", 0)
    if tokens < 1:
        return JSONResponse({"error": "not enough tokens"}, status_code=400)
    
    amount_to_send = tokens * EXCHANGE_RATE
    
    # Здесь вставляем реальный вызов TON API или SDK для перевода
    # Например, через TonTools или HTTP API
    # Ниже просто пример запроса (замени на настоящий метод перевода)
    try:
        response = requests.post(
            "https://toncenter.com/api/v2/sendTransaction",
            json={
                "from": TON_WALLET,
                "to": user_wallet,
                "amount": amount_to_send,
                "contract": TOKEN_CONTRACT
            }
        )
        response.raise_for_status()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    
    # Обнуляем очки после обмена
    db["tokens"] = 0
    with open(DB_PATH, "w") as f: json.dump(db, f)
    
    return {"sent": amount_to_send, "tokens": 0}


@app.get("/", response_class=HTMLResponse)
async def index():
    return f"""
<!DOCTYPE html><html><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<script src="telegram.org"></script>
<style>
body{{margin:0;overflow:hidden;background:#4ec0ca;font-family:sans-serif;}}
#ui{{position:absolute;top:20px;width:100%;text-align:center;color:white;font-size:24px;z-index:10;text-shadow:2px 2px 0 #000;font-weight:bold;}}
canvas{{display:block;width:100vw;height:100vh;}}
#exchangeBtn{{position:absolute;top:60px;left:50%;transform:translateX(-50%);padding:10px 20px;font-size:18px;z-index:10;}}
</style>
</head><body>
<div id="ui">UBUNTU: <span id="t">0</span> | РЕКОРД: <span id="b">0</span></div>
<button id="exchangeBtn">Обменять очки на Ubuntu</button>
<canvas id="c"></canvas>
<script>
const tg = window.Telegram ? window.Telegram.WebApp : null;
if(tg){{ tg.expand(); tg.ready(); }}

const cvs=document.getElementById('c'); const ctx=cvs.getContext('2d');
function res(){{cvs.width=window.innerWidth; cvs.height=window.innerHeight;}}
window.onresize=res; res();

let bird={{x:80, y:200, w:50, h:50, v:0, g:0.45, score:0}};
let pipes=[]; let frame=0; let dead=false;

const bI=new Image(); bI.src='/static/bird.png';
const pI=new Image(); pI.src='/static/pipe.png';
const bg=new Image(); bg.src='/static/background.png';

function draw(){{
    ctx.fillStyle = "#4ec0ca"; ctx.fillRect(0, 0, cvs.width, cvs.height);
    if(bg.complete) ctx.drawImage(bg, 0,0,cvs.width,cvs.height);
    bird.v += 0.45; bird.y += bird.v;
    ctx.save(); ctx.translate(bird.x, bird.y);
    if(bI.complete && bI.width>0) ctx.drawImage(bI,-25,-25,50,50);
    else {{ctx.fillStyle="yellow"; ctx.fillRect(-25,-25,50,50);}}
    ctx.restore();

    if(!dead) frame++;
    if(!dead && frame % 100===0) pipes.push({{x:cvs.width, t:Math.random()*(cvs.height-350)+50, p:false}});

    pipes.forEach((p,i)=>{{
        if(!dead) p.x-=4.5;
        if(pI.complete && pI.width>0){{
            ctx.drawImage(pI,p.x,0,80,p.t);
            ctx.drawImage(pI,p.x,p.t+190,80,cvs.height);
        }} else {{
            ctx.fillStyle="green"; ctx.fillRect(p.x,0,80,p.t);
            ctx.fillRect(p.x,p.t+190,80,cvs.height);
        }}
        if(!dead && bird.x+20>p.x && bird.x-20<p.x+80 && (bird.y-20<p.t || bird.y+20>p.t+190)) dead=true;
        if(!dead && !p.p && p.x<bird.x){{
            p.p=true; bird.score++;
            fetch('/earn/'+bird.score,{{method:'POST'}}).then(r=>r.json()).then(data=>{{
                document.getElementById('t').innerText=data.tokens;
                document.getElementById('b').innerText=data.best;
            }});
        }}
    }});
    if(bird.y>cvs.height+50){{ bird.y=200; bird.v=0; pipes=[]; frame=0; dead=false; bird.score=0; }}
    requestAnimationFrame(draw);
}}
window.onmousedown=()=>{{ if(!dead) bird.v=-8; }};
window.ontouchstart=()=>{{ if(!dead) bird.v=-8; }};
draw();

// Кнопка обмена
document.getElementById('exchangeBtn').onclick = async () => {{
    const wallet = prompt("Введите адрес вашего кошелька для получения Ubuntu:");
    if(!wallet) return;
    const res = await fetch('/exchange', {{
        method:'POST',
        headers:{{'Content-Type':'application/json'}},
        body: JSON.stringify({{wallet}})
    }});
    const data = await res.json();
    if(data.error) alert("Ошибка: "+data.error);
    else {{
        alert("Отправлено "+data.sent+" Ubuntu на ваш кошелек!");
        document.getElementById('t').innerText = data.tokens;
    }}
}};
</script>
</body></html>
"""

if __name__=="__main__":
    port=int(os.environ.get("PORT",8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
