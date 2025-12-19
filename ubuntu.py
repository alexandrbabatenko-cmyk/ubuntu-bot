from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn, os

app = FastAPI()

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
html, body {
    margin: 0;
    padding: 0;
    width: 100%;
    height: 100%;
    overflow: hidden;
    background: #4ec0ca;
}
#ui {
    position: absolute;
    top: 15px;
    width: 100%;
    text-align: center;
    color: white;
    font-size: 20px;
    font-weight: bold;
    text-shadow: 2px 2px 0 #000;
    z-index: 10;
}
canvas {
    display: block;
}
</style>
</head>

<body>
<div id="ui">UBUNTU: <span id="t">0</span> | РЕКОРД: <span id="b">0</span></div>
<canvas id="c"></canvas>

<script>
document.addEventListener("DOMContentLoaded", () => {

    // --- TELEGRAM SAFE ---
    if (window.Telegram && Telegram.WebApp) {
        Telegram.WebApp.expand();
    }

    // --- CANVAS ---
    const canvas = document.getElementById("c");
    if (!canvas) {
        alert("Canvas not found");
        return;
    }

    const ctx = canvas.getContext("2d");
    if (!ctx) {
        alert("Canvas context error");
        return;
    }

    function resize() {
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
    }
    window.addEventListener("resize", resize);
    resize();

    // --- GAME STATE ---
    let bird = { x: 80, y: 200, v: 0 };
    let pipes = [];
    let frame = 0;
    let dead = false;

    function loop() {
        ctx.fillStyle = "#4ec0ca";
        ctx.fillRect(0, 0, canvas.width, canvas.height);

        bird.v += 0.5;
        bird.y += bird.v;

        ctx.fillStyle = "yellow";
        ctx.fillRect(bird.x - 20, bird.y - 20, 40, 40);

        if (!dead) frame++;
        if (!dead && frame % 90 === 0) {
            pipes.push({
                x: canvas.width,
                gap: Math.random() * (canvas.height - 300) + 150,
                passed: false
            });
        }

        pipes.forEach(p => {
            if (!dead) p.x -= 4;

            ctx.fillStyle = "green";
            ctx.fillRect(p.x, 0, 80, p.gap - 80);
            ctx.fillRect(p.x, p.gap + 80, 80, canvas.height);

            if (
                bird.x + 20 > p.x &&
                bird.x - 20 < p.x + 80 &&
                (bird.y - 20 < p.gap - 80 || bird.y + 20 > p.gap + 80)
            ) {
                dead = true;
            }
        });

        if (bird.y > canvas.height) {
            bird.y = 200;
            bird.v = 0;
            pipes = [];
            frame = 0;
            dead = false;
        }

        requestAnimationFrame(loop);
    }

    window.addEventListener("mousedown", () => bird.v = -8);
    window.addEventListener("touchstart", () => bird.v = -8);

    loop();
});
</script>
</body>
</html>
"""

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
