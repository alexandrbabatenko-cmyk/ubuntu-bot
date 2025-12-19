from fastapi import FastAPI, Response, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn, json, os

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

TON_WALLET = "UQDpW4gtsT9Y77oze2el7fpJ-9OFPtvgSLmZZ6a57gOgL4vZ"
TOKEN_CONTRACT = "EQA25M3v5zYC6-f8uyjFf1QPaZaNSS7WOJggo14DWsYiXmZc"
EXCHANGE_RATE = 1  # 1 очко = 1 Ubuntu

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)

@app.post("/earn/{wallet}/{score}")
async def earn(wallet: str, score: int):
    with open(DB_PATH, "r") as f:
        db = json.load(f)

    if "users" not in db:
        db["users"] = {}

    user = db["users"].get(wallet, {"tokens": 0, "best": 0})
    user["tokens"] += 1
    new_record = False
    if score > user.get("best", 0):
        user["best"] = score
        new_record = True

    db["users"][wallet] = user
    with open(DB_PATH, "w") as f:
        json.dump(db, f)

    return {"tokens": user["tokens"], "best": user["best"], "new_record": new_record}

@app.post("/exchange")
async def exchange(request: Request):
    data = await request.json()
    wallet = data.get("wallet")

    if not wallet:
        return JSONResponse({"error": "wallet missing"}, status_code=400)

    with open(DB_PATH, "r") as f:
        db = json.load(f)

    user = db["users"].get(wallet)
    if not user or user["tokens"] < 1:
        return JSONResponse({"error": "not enough tokens"}, status_code=400)

    amount_to_send = user["tokens"]

    # Заглушка для реального перевода через TON API
    success = True

    if success:
        user["tokens"] = 0
        db["users"][wallet] = user
        with open(DB_PATH, "w") as f:
            json.dump(db, f)
        return {"sent": amount_to_send, "tokens": 0}
    else:
        return JSONResponse({"error": "transaction failed"}, status_code=500)

@app.get("/", response_class=HTMLResponse)
async def index():
    return """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
<script src="telegram.org"></script>
<style>
body{margin:0;overflow:hidden;background:#4ec0ca;font-family:sans-serif;}
#ui{position:absolute;top:20px;width:100%;text-align:center;color:white;font-size:24px;z-index:10;text-shadow:2px 2px 0 #000;font-weight:bold;}
canvas{display:block;width:100vw;height:100vh;}
#exchangeBtn{position:absolute;top:60px;left:50%;transform:translateX(-50%);padding:10px 20px;font-size:18px;z-index:10;}
</style>
</head>
<body>
<div id="ui">UBUNTU: <span id="t">0</span></div>
<button id="exchangeBtn">Обменять очки на Ubuntu</button>
<canvas id="c"></canvas>
<script>
const tg = window.Telegram ? window.Telegram.WebApp : null;
if(tg){ tg.expand(); tg.ready(); }

const cvs = document.getElementById('c'); 
const ctx = cvs.getContext('2d');

const GAME_WIDTH = 400;
const GAME_HEIGHT = 600;
let scaleX = 1, scaleY = 1;

function res(){
    cvs.width = window.innerWidth;
    cvs.height = window.innerHeight;
    scaleX = cvs.width / GAME_WIDTH;
    scaleY = cvs.height / GAME_HEIGHT;
}
window.onresize = res; res();

let bird = {x:80, y:200, w:50, h:50, v:0, g:0.45, score:0};
let pipes = []; let frame=0; let dead=false;
let lastRecordScore = 0;
let recordPipes = [];

const bI = new Image(); bI.src='/static/bird.png';
const bg = new Image(); bg.src='/static/background.png';
const PIPE_WIDTH = 80;
const PIPE_GAP = 190;

function draw(){
    ctx.fillStyle="#4ec0ca"; ctx.fillRect(0,0,cvs.width,cvs.height);
    if(bg.complete) ctx.drawImage(bg,0,0,cvs.width,cvs.height);

    ctx.save();
    ctx.scale(scaleX, scaleY);

    for(let i=0; i<recordPipes.length; i++){
        const p = recordPipes[i];
        ctx.fillStyle="yellow";
        ctx.fillRect(p.x,0,PIPE_WIDTH,p.t);
        ctx.fillRect(p.x,p.t+PIPE_GAP,PIPE_WIDTH,GAME_HEIGHT-p.t-PIPE_GAP);
    }

    bird.v += bird.g; bird.y += bird.v;
    ctx.save(); ctx.translate(bird.x,bird.y);
    if(bI.complete && bI.width>0) ctx.drawImage(bI,-bird.w/2,-bird.h/2,bird.w,bird.h);
    else {ctx.fillStyle="yellow"; ctx.fillRect(-bird.w/2,-bird.h/2,bird.w,bird.h);}
    ctx.restore();

    if(!dead) frame++;
    if(!dead && frame%100===0) pipes.push({x:GAME_WIDTH,t:Math.random()*(GAME_HEIGHT-350)+50,p:false,highlight:false});

    pipes.forEach((p)=>{
        if(!dead) p.x-=4.5;
        ctx.fillStyle = p.highlight ? "yellow" : "green";
        ctx.fillRect(p.x,0,PIPE_WIDTH,p.t);
        ctx.fillRect(p.x,p.t+PIPE_GAP,PIPE_WIDTH,GAME_HEIGHT-p.t-PIPE_GAP);

        if(!dead && bird.x+bird.w/2>p.x && bird.x-bird.w/2<p.x+PIPE_WIDTH && (bird.y-bird.h/2<p.t || bird.y+bird.h/2>p.t+PIPE_GAP)) dead=true;

        if(!dead && !p.p && p.x<bird.x){
            p.p=true; bird.score++;
            const wallet = localStorage.getItem('wallet');
            if(wallet){
                fetch('/earn/'+wallet+'/'+bird.score,{method:'POST'}).then(r=>r.json()).then(data=>{
                    document.getElementById('t').innerText=data.tokens;
                    if(data.best>lastRecordScore){
                        recordPipes = pipes.slice(0,data.best);
                        lastRecordScore = data.best;
                    }
                });
            }
        }
    });

    if(bird.y>GAME_HEIGHT+50){ bird.y=200; bird.v=0; pipes=[]; frame=0; dead=false; bird.score=0; }

    ctx.restore();
    requestAnimationFrame(draw);
}

window.onmousedown=()=>{ if(!dead) bird.v=-8; };
window.ontouchstart=()=>{ if(!dead) bird.v=-8; };
draw();

document.getElementById('exchangeBtn').onclick = async () => {
    let wallet = localStorage.getItem('wallet');
    if(!wallet){
        wallet = prompt("Введите ваш кошелек для получения Ubuntu:");
        if(!wallet) return;
        localStorage.setItem('wallet', wallet);
    }
    const res = await fetch('/exchange',{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body: JSON.stringify({wallet})
    });
    const data = await res.json();
    if(data.error) alert("Ошибка: "+data.error);
    else {
        alert("Отправлено "+data.sent+" Ubuntu на ваш кошелек! Остаток очков: "+data.tokens);
        document.getElementById('t').innerText = data.tokens;
    }
};
</script>
</body></html>
"""

if __name__=="__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
