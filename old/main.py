import asyncio
from datetime import datetime, timezone, timedelta
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
import uuid
import os
import json
import urllib.request
import ssl

# Gemini API: set GEMINI_API_KEY in environment (never commit keys)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

state = {
    "support_chats": {},
    "timers": [{"name": "", "sec": 300, "state": 0} for i in range(42)]
}
connections = {}

# ★ Google公式の標準通信方式（エラー回避特化）
async def generate_ai_reply(client_id, user_msg):
    if not GEMINI_API_KEY:
        ai_text = (
            "【設定不足】環境変数 GEMINI_API_KEY が未設定です。"
            "キーはコードやGitに含めないでください。"
        )
    else:
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

            prompt = f"あなたはホワサバの有能な副官です。天津飯（総指揮）をサポートしています。短く返信して。客: {user_msg}"
            payload = {"contents": [{"parts": [{"text": prompt}]}]}
            data_bytes = json.dumps(payload).encode('utf-8')

            def call_raw_api():
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                headers = {'Content-Type': 'application/json'}

                req = urllib.request.Request(url, data=data_bytes, headers=headers, method='POST')
                with urllib.request.urlopen(req, context=ctx, timeout=10) as res:
                    res_data = json.loads(res.read().decode('utf-8'))
                    return res_data['candidates'][0]['content']['parts'][0]['text']

            loop = asyncio.get_running_loop()
            ai_text = await loop.run_in_executor(None, call_raw_api)

        except Exception as e:
            ai_text = f"【AI副官 起動待機中】Googleの準備を待っています。数分後に再度お試しください。詳細: {str(e)}"

    now_dt = datetime.now(timezone.utc) + timedelta(hours=9)
    time_str = now_dt.strftime("%H:%M")
    if client_id in state["support_chats"]:
        state["support_chats"][client_id]["messages"].append({"sender": "ai", "text": ai_text, "time": time_str})

# --- システム基盤（変更なし） ---

async def broadcast():
    payload = {"type": "tick", "data": state, "utc": datetime.now(timezone.utc).strftime("%H:%M:%S")}
    for ws in list(connections.keys()):
        try: await ws.send_json(payload)
        except: pass

async def broadcast_loop():
    while True: await broadcast(); await asyncio.sleep(0.25)

@asynccontextmanager
async def lifespan(app: FastAPI): task = asyncio.create_task(broadcast_loop()); yield; task.cancel()

app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.get("/")
async def get_player():
    with open("player.html", "r", encoding="utf-8") as f: return HTMLResponse(f.read())
@app.get("/admin_hq_777")
async def get_admin():
    with open("index.html", "r", encoding="utf-8") as f: return HTMLResponse(f.read())
@app.get("/support_hq_3301")
async def get_support():
    with open("support.html", "r", encoding="utf-8") as f: return HTMLResponse(f.read())

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept(); connections[websocket] = {"id": str(uuid.uuid4())}
    try:
        await websocket.send_json({"type": "init", "data": state})
        while True:
            data = await websocket.receive_json()
            cmd, val = data.get("cmd"), data.get("val")
            if cmd == "send_support_chat":
                cid, name, msg = val.get("client_id", "unknown"), val.get("name", "名無し"), val.get("msg", "")
                if cid not in state["support_chats"]: state["support_chats"][cid] = {"name": name, "messages": [], "unread_admin": True}
                time_str = (datetime.now(timezone.utc) + timedelta(hours=9)).strftime("%H:%M")
                state["support_chats"][cid]["messages"].append({"sender": "user" if not val.get("is_admin") else "admin", "text": msg, "time": time_str})
                if not val.get("is_admin"): asyncio.create_task(generate_ai_reply(cid, msg))
            await broadcast()
    except WebSocketDisconnect:
        if websocket in connections: del connections[websocket]

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=False)