from fastapi import FastAPI, Depends, HTTPException, status, Header
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import jwt
from pydantic import BaseModel
from config.settings import get_settings
from database.repository import Database
import uvicorn
import os
import psutil
import base64
from media.charts import generate_activity_chart

app = FastAPI(title="Mahiro Dashboard")
settings = get_settings()

class LoginData(BaseModel):
    token: str

@app.post("/api/login")
async def login(data: LoginData):
    if data.token == settings.ADMIN_PANEL_TOKEN:
        encoded = jwt.encode({"sub": "admin"}, settings.ADMIN_PANEL_TOKEN, algorithm="HS256")
        return {"access_token": encoded}
    raise HTTPException(status_code=401, detail="Invalid token")

def verify_token(authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token")
    token = authorization.split(" ")[1]
    try:
        jwt.decode(token, settings.ADMIN_PANEL_TOKEN, algorithms=["HS256"])
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/", response_class=HTMLResponse)
async def index():
    if os.path.exists("web/templates/index.html"):
        with open("web/templates/index.html", "r") as f:
            return f.read()
    return "<h1>Mahiro Dashboard</h1><p>Running.</p>"

@app.get("/api/stats")
async def get_stats():
    db = Database()
    await db.connect()
    users = await db.get_all_users()
    await db.close()
    return {
        "users": len(users),
        "messages": sum(u.message_count for u in users)
    }

@app.get("/api/users", dependencies=[Depends(verify_token)])
async def get_users():
    db = Database()
    await db.connect()
    users = await db.get_all_users()
    await db.close()
    return [{"id": u.id, "trust": u.trust, "mood": u.mood, "xp": u.xp, "messages": u.message_count, "coins": u.coins, "is_banned": u.is_banned} for u in users]

@app.get("/api/logs", dependencies=[Depends(verify_token)])
async def get_logs():
    if os.path.exists("logs/mahiro.log"):
        with open("logs/mahiro.log", "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()[-50:]
        return {"logs": lines}
    return {"logs": []}

@app.get("/api/system", dependencies=[Depends(verify_token)])
async def get_system():
    return {
        "cpu": psutil.cpu_percent(),
        "ram": psutil.virtual_memory().percent,
        "disk": psutil.disk_usage('/').percent
    }

@app.get("/api/charts", dependencies=[Depends(verify_token)])
async def get_charts():
    db = Database()
    await db.connect()
    activity = await db.get_daily_activity()
    await db.close()
    
    act_path = await generate_activity_chart(activity)
    with open(act_path, "rb") as f:
        act_b64 = base64.b64encode(f.read()).decode()
        
    return {"activity_chart": f"data:image/png;base64,{act_b64}"}

@app.get("/api/config", dependencies=[Depends(verify_token)])
async def get_config():
    db = Database()
    await db.connect()
    async with db._conn.execute('SELECT key, value FROM settings') as cursor:
        rows = await cursor.fetchall()
    await db.close()
    
    db_settings = {row[0]: row[1] for row in rows}
    
    return {
        "whitelist": settings.WHITELIST_USER_IDS,
        "blacklist": settings.BLACKLIST_USER_IDS,
        "db_settings": db_settings
    }

class UserUpdateData(BaseModel):
    trust: int
    mood: str
    xp: int
    coins: int
    is_banned: bool

@app.post("/api/users/{user_id}", dependencies=[Depends(verify_token)])
async def update_user(user_id: int, data: UserUpdateData):
    db = Database()
    await db.connect()
    user = await db.get_user(user_id)
    user.trust = data.trust
    user.mood = data.mood
    user.xp = data.xp
    user.coins = data.coins
    user.is_banned = data.is_banned
    await db.update_user(user)
    await db.close()
    return {"status": "success"}

class SettingUpdateData(BaseModel):
    value: str

@app.post("/api/settings/{key}", dependencies=[Depends(verify_token)])
async def update_setting(key: str, data: SettingUpdateData):
    db = Database()
    await db.connect()
    await db._conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, data.value))
    await db._conn.commit()
    await db.close()
    return {"status": "success"}

def start_web():
    os.makedirs("web/templates", exist_ok=True)
    if not os.path.exists("web/templates/index.html"):
        with open("web/templates/index.html", "w") as f:
            f.write("<html><body><h1>Mahiro API</h1></body></html>")
    uvicorn.run(app, host="0.0.0.0", port=8000)
