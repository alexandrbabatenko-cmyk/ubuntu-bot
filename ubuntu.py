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

MIN_EXCHANGE = 10000  # 🔐 минимальный порог вывода

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

# 🪙 Начисление токенов — ТОЛЬКО если есть кошелёк
@app.post("/earn/{wallet}/{score}")
async def earn(wallet: str, score: int):
    if not wallet:
        return {"tokens": 0}

    with open(DB_PATH, "r") as f:
        db = json.load(f)

    user = db["users"].get(wallet, {"tokens": 0, "best": 0})
    user["tokens"] += 1

    if score > user.get("best", 0):
        user["best"] = score

    db["users"][wallet] = user

    with open(DB_PATH, "w") as f:
        json.dump(db, f)

    return user

# 🔄 Обмен токенов
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
    user["tokens"] -= send_amount
    db["users"][wallet] = user

    with open(DB_PATH, "w") as f:
        json.dump(db, f)

    # ⚠️ Здесь позже подключишь реальный перевод из горячего кошелька
    return {
        "sent": send_amount,
        "tokens": user["tokens"]
    }

# 🎮 Игра
@app.get("/", response_class=HTMLResponse)
async def index():
    return """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
body{margin:0;overflow:hidden;background:#4ec0ca;font-family:sans-serif;}
#ui{position:absolute;top:20px;width:100%;text-align:center;color:white;font-size:24px;font-weight:bold;}
button{padding:6px 12px;font-size:16px;}
canvas{display:block;}
</style>
</head>
<body>
<div id="ui">
<span id="t">0</span> UBUNTU
<button id="exchangeBtn">Обменять</button>
</div>
<canvas id="c"></canvas>

<script>
const cvs = document.getElementById('c');
const ctx = cvs.getContext('2d');
cvs.width = innerWidth;
cvs.height = innerHeight;

let bird={x:80,y:200,v:0,g:0.5};
let pipes=[];
let score=0;

function draw(){
    ctx.fillStyle="#4ec0ca";
    ctx.fillRect(0,0,cvs.width,cvs.height);

    bird.v+=bird.g;
    bird.y+=bird.v;

    ctx.fillStyle="yellow";
    ctx.fillRect(bird.x,bird.y,40,40);

    pipes.forEach(p=>{
        p.x-=4;
        ctx.fillStyle="green";
        ctx.fillRect(p.x,0,80,p.t);
        ctx.fillRect(p.x,p.t+180,80,cvs.height);

        if(p.x<bird.x && !p.passed){
            p.passed=true;
            score++;

            const wallet = localStorage.getItem("wallet");
            if(wallet){
                fetch(`/earn/${wallet}/${score}`,{method:"POST"})
                .then(r=>r.json())
                .then(d=>document.getElementById("t").innerText=d.tokens);
            }
        }
    });

    if(Math.random()<0.01){
        pipes.push({x:cvs.width,t:Math.random()*300+50});
    }

    requestAnimationFrame(draw);
}
draw();

onclick=()=>bird.v=-8;

document.getElementById("exchangeBtn").onclick=async()=>{
    let wallet = localStorage.getItem("wallet");
    if(!wallet){
        wallet = prompt("Введите кошелёк:");
        if(!wallet) return;
        localStorage.setItem("wallet",wallet);
        alert("Кошелёк сохранён. Теперь очки будут начисляться.");
        return;
    }

    const r = await fetch("/exchange",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({wallet})
    });

    const d = await r.json();
    if(d.error) alert(d.error);
    else{
        alert("Отправлено "+d.sent+" UBUNTU");
        document.getElementById("t").innerText=d.tokens;
    }
}
</script>
</body>
</html>
"""

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
