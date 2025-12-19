from fastapi import FastAPI, Response
from fastapi.responses import HTMLResponse
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

# АВТОМАТИЧЕСКОЕ ОПРЕДЕЛЕНИЕ ПУТЕЙ ДЛЯ СЕРВЕРА
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "db.json")
STATIC_DIR = os.path.join(BASE_DIR, "static")

# Создаем папку static, если ее нет (на всякий случай)
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR)

if not os.path.exists(DB_PATH):
    with open(DB_PATH, "w") as f: json.dump({"tokens": 0, "best": 0}, f)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

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

@app.get("/", response_class=HTMLResponse)
async def index():
    return """
    <!DOCTYPE html><html><head><meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <script src="telegram.org"></script>
    
    <script src="telegram.org"></script>
    <style>
        body{margin:0;overflow:hidden;background:#4ec0ca;font-family:sans-serif;}
        #ui{position:absolute;top:20px;width:100%;text-align:center;color:white;font-size:24px;z-index:10;text-shadow:2px 2px 0 #000;font-weight:bold;}
    </style></head><body>
    <div id="ui">UBUNTU: <span id="t">0</span> | РЕКОРД: <span id="b">0</span></div>
    <canvas id="c"></canvas>
    <script>
        const tg = window.Telegram.WebApp;
        tg.expand();

        const cvs=document.getElementById('c'); const ctx=cvs.getContext('2d');
        function res(){cvs.width=window.innerWidth; cvs.height=window.innerHeight;}
        window.onresize=res; res();

        let bird={x:80, y:200, w:50, h:50, v:0, g:0.45, j:-8};
        let pipes=[]; let frame=0; let dead=false; 
        let score=0; let bestScore=0;

        const bI=new Image(); bI.src='/static/bird.png';
        const pI=new Image(); pI.src='/static/pipe.png';
        const bg=new Image(); bg.src='/static/background.png';

        function resetGame() {
            bird.y = 200; bird.v = 0; pipes = []; frame = 0; score = 0; dead = false;
        }

        function draw(){
            ctx.drawImage(bg, 0, 0, cvs.width, cvs.height);
            bird.v += bird.g; bird.y += bird.v;
            if(!dead) frame++;

            ctx.save(); ctx.translate(bird.x, bird.y); ctx.rotate(Math.min(0.7, bird.v/10));
            ctx.drawImage(bI, -25, -25, 50, 50); ctx.restore();

            if(!dead && frame % 100 === 0) {
                pipes.push({x:cvs.width, t:Math.random()*(cvs.height-350)+50, p:false, id: score + pipes.filter(p=>!p.p).length + 1});
            }

            pipes.forEach((p,i)=>{
                if(!dead) p.x -= 4.5;
                let gap = 190;
                ctx.save();
                if(bestScore > 0 && p.id === bestScore) {
                    ctx.filter = "brightness(1.2) sepia(1) saturate(10) hue-rotate(10deg)";
                    ctx.shadowBlur = 15; ctx.shadowColor = "yellow";
                }
                ctx.save(); ctx.translate(p.x+40, p.t); ctx.scale(1,-1);
                ctx.drawImage(pI, -40, 0, 80, cvs.height); ctx.restore();
                ctx.drawImage(pI, p.x, p.t + gap, 80, cvs.height);
                ctx.restore();

                if(!dead && bird.x+20>p.x && bird.x-20<p.x+80 && (bird.y-20<p.t || bird.y+20>p.t+gap)) dead=true;

                if(!dead && !p.p && p.x + 80 < bird.x){
                    p.p = true; score++;
                    fetch('/earn/' + score, {method:'POST'}).then(r=>r.json()).then(data=>{
                        document.getElementById('t').innerText = data.tokens;
                        document.getElementById('b').innerText = data.best;
                        bestScore = data.best;
                    });
                }
            });
            if(bird.y > cvs.height + 50) resetGame();
            requestAnimationFrame(draw);
        }
        const act = (e) => { if(e) e.preventDefault(); if(!dead) bird.v=-8; else if(bird.y > 100) resetGame(); };
        window.onmousedown = act; window.ontouchstart = act;
        draw();
    </script></body></html>
    """

if __name__ == "__main__":
    # ВАЖНО: Render передает порт через переменную окружения PORT
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

