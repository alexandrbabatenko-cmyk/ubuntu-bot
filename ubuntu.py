from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn, json, os, logging

app = FastAPI()
logging.basicConfig(level=logging.INFO)

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
        json.dump({}, f)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ---------- API ----------

@app.get("/stats")
async def stats(user_id: str = "guest"):
    with open(DB_PATH, "r") as f:
        db = json.load(f)

    if user_id not in db:
        db[user_id] = {"tokens": 0, "best": 0}
        with open(DB_PATH, "w") as f:
            json.dump(db, f)

    return db[user_id]


@app.post("/earn/{score}")
async def earn(score: int, user_id: str = "guest"):
    with open(DB_PATH, "r") as f:
        db = json.load(f)

    if user_id not in db:
        db[user_id] = {"tokens": 0, "best": 0}

    db[user_id]["tokens"] += 1
    if score > db[user_id]["best"]:
        db[user_id]["best"] = score

    with open(DB_PATH, "w") as f:
        json.dump(db, f)

    return db[user_id]


# ---------- FRONT ----------

@app.get("/", response_class=HTMLResponse)
async def index():
    return """
<!DOCTYPE html>
<html lang="ru">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<script src="https://telegram.org/js/telegram-web-app.js"></script>

<style>
body { margin:0; overflow:hidden; background:#4ec0ca; font-family:sans-serif; }
#ui {
    position:absolute; top:15px; width:100%;
    text-align:center; color:white;
    font-size:20px; font-weight:bold;
    text-shadow:2px 2px 0 #000;
    z-index:10;
}
canvas { display:block; }
</style>
</head>

<body>
<div id="ui">UBUNTU: <span id="t">0</span> | РЕКОРД: <span id="b">0</span></div>
<canvas id="c"></canvas>

<script>
/* ---------- TELEGRAM SAFE ---------- */
const tg = window.Telegram && window.Telegram.WebApp ? window.Telegram.WebApp : null;
if (tg) tg.expand();

const user_id = tg?.initDataUnsafe?.user?.id || "guest";

/* ---------- CANVAS ---------- */
const cvs = document.getElementById("c");
const ctx = cvs.getContext("2d");

function resize() {
    cvs.width = window.innerWidth;
    cvs.height = window.innerHeight;
}
window.addEventListener("resize", resize);
resize();

/* ---------- LOAD STATS ---------- */
fetch(`/stats?user_id=${user_id}`)
  .then(r => r.json())
  .then(d => {
    document.getElementById("t").innerText = d.tokens;
    document.getElementById("b").innerText = d.best;
  });

/* ---------- GAME ---------- */
let bird = { x:80, y:200, v:0 };
let pipes = [];
let frame = 0;
let dead = false;

function loop() {
    ctx.fillStyle = "#4ec0ca";
    ctx.fillRect(0,0,cvs.width,cvs.height);

    bird.v += 0.5;
    bird.y += bird.v;

    ctx.fillStyle = "yellow";
    ctx.fillRect(bird.x-20, bird.y-20, 40, 40);

    if (!dead) frame++;
    if (!dead && frame % 90 === 0) {
        pipes.push({
            x: cvs.width,
            gap: Math.random() * (cvs.height - 300) + 100,
            passed:false
        });
    }

    pipes.forEach(p => {
        if (!dead) p.x -= 4;

        ctx.fillStyle = "green";
        ctx.fillRect(p.x, 0, 80, p.gap - 80);
        ctx.fillRect(p.x, p.gap + 80, 80, cvs.height);

        if (
            bird.x+20 > p.x &&
            bird.x-20 < p.x+80 &&
            (bird.y-20 < p.gap-80 || bird.y+20 > p.gap+80)
        ) dead = true;

        if (!p.passed && p.x < bird.x) {
            p.passed = true;
            fetch(`/earn/${frame}?user_id=${user_id}`)
              .then(r=>r.json())
              .then(d=>{
                document.getElementById("t").innerText = d.tokens;
                document.getElementById("b").innerText = d.best;
              });
        }
    });

    if (bird.y > cvs.height) {
        bird.y = 200; bird.v = 0;
        pipes = []; frame = 0; dead = false;
    }

    requestAnimationFrame(loop);
}

window.addEventListener("mousedown", () => bird.v = -8);
window.addEventListener("touchstart", () => bird.v = -8);

loop();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
