from fastapi import FastAPI, Request, BackgroundTasks, Query, Header, Depends, HTTPException
from fastapi.responses import JSONResponse
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
import firebase_admin
from firebase_admin import credentials, firestore
from google.oauth2 import service_account
from google.auth.transport.requests import Request as GRequest
import hashlib
import os
import json
import requests
import threading
import time
import psutil
import uuid
import multiprocessing
import random
from datetime import datetime

# Initialize FastAPI app
app = FastAPI()

# Track uptime
startTime = time.time()
process = psutil.Process(os.getpid())
serverId = str(uuid.uuid4())

# ========= Request Model =========
class UserData(BaseModel):
    email: str
    aliasName: str
    doneWhatTitle: str
    doneWhatBody: str

notification_sets = [
    {
        "time": "morning",
        "range": ("06:00", "10:00"),
        "messages": [
            "🌅 A new day, a new chance to feel lighter. Let it out. ✨",
            "☀️ What’s on your mind this morning? Share it anonymously. 💬",
            "🧘‍♀️ Starting your day with a clear heart makes it easier. Vent here. 🌼",
            "🌞 Good morning! Your feelings matter—say them out loud. 🗣️",
            "☕ Coffee helps. So does unburdening your thoughts. 🧠",
            "💭 Begin your day with honesty—to yourself. 🌿",
            "🕊️ Today, give your heart a moment of peace. Express yourself. ✍️",
            "📖 Before the world begins, take a moment to check in with yourself. 🤍",
            "🤍 No pressure. Just thoughts you don’t have to carry alone. 🎈",
            "🕰️ Still thinking about yesterday? Let it go here, safely. 🌈"
        ]
    },
    {
        "time": "afternoon",
        "range": ("12:00", "16:00"),
        "messages": [
            "😵‍💫 Midday stress? Take a 1-minute pause. Share what’s bothering you. 📤",
            "🍱 Lunchtime thoughts can be the heaviest. Want to vent? 💭",
            "⏳ Between meetings, tasks, and people—don't forget to breathe. 🌬️",
            "🙇‍♀️ What are you holding back today? This space is still yours. 🔐",
            "🕔 You’re halfway through. A short confession can help ease the rest. ✨",
            "😓 Tough day? Say what’s on your mind anonymously. 📣",
            "🌫️ Worried or anxious? Even a few words can lighten the load. 🪶",
            "📩 Someone else just posted how they feel. Maybe you can too. 💬",
            "🔁 Break the loop of overthinking. Vent anonymously. 🔓",
            "🎈 You don’t have to carry your emotions until bedtime. 🌙"
        ]
    },
    {
        "time": "evening",
        "range": ("18:00", "22:00"),
        "messages": [
            "🌇 Evenings are for release. What’s been weighing on you? 🪨",
            "🎒 Still carrying the day’s weight? Let it go, one post at a time. ✍️",
            "🤝 Confessions are welcome here—no judgment. 💌",
            "🗣️ What would you say if no one knew it was you? Say it here. 🕶️",
            "🌆 You made it through the day. Ready to express the rest? 🧘",
            "🖤 Nothing is too small or too dark. Let it out anonymously. 🕯️",
            "🕯️ A long day deserves a short moment of emotional clarity. 🧠",
            "🗨️ Speak your truth. Even if it’s raw. Even if it hurts. 🔥",
            "🤫 What would you whisper to a friend at midnight? Whisper it here. 🌙",
            "🛑 It’s safe here. Share something and make your heart lighter. 💞"
        ]
    },
    {
        "time": "night",
        "range": ("22:00", "02:00"),
        "messages": [
            "🌙 Can’t sleep? Maybe it’s time to unload a little. ✍️",
            "🕛 Your midnight thoughts matter. Let them out anonymously. 💭",
            "🌌 This space doesn’t close. It’s always open to your feelings. 🫶",
            "📓 Some thoughts don’t need to be kept in. You can write them here. 🖋️",
            "🛏️ It’s quiet now. The perfect time to reflect—and release. 🧠",
            "🌚 The night feels heavier with secrets. You can leave them here. 🔒",
            "👂 Sometimes you don’t need advice. Just a space to be heard. 💬",
            "🫂 Let your words rest here so your mind can rest too. 💤",
            "🫧 Late-night emotions hit hard. Write them down, feel a little lighter. 📤",
            "🌠 You’re not alone—not even at 2 AM. 🕯️"
        ]
    }
]

# ========= API Key Validator =========
class ApiValidator:
    def __init__(self):
        self.apiKey = os.environ["API_KEY"]

    def validate(self, client_key: str) -> bool:
        if not client_key:
            print("API key not found in request")
            return False
        
        match_key = hashlib.sha256(client_key.encode()).hexdigest()
        if match_key != self.apiKey:
            print("API_KEY not matched")
            return False
        return True

# ========= Server Logic =========
class ServerFunctions:
    def __init__(self):
        try:
            if not firebase_admin._apps:
                self.cred_json = json.loads(os.environ["CREDS"])
                creds = credentials.Certificate(self.cred_json)
                firebase_admin.initialize_app(creds)

            self.db = firestore.client()
            self.projectId = os.environ["projectId"]
            self.SCOPES = ["https://www.googleapis.com/auth/firebase.messaging"]
            self.url = f"https://fcm.googleapis.com/v1/projects/{self.projectId}/messages:send"

        except Exception as e:
            print("Firebase Initialization Error:", e)
            raise e

    def token(self):
        credentials_obj = service_account.Credentials.from_service_account_info(
                self.cred_json, scopes=self.SCOPES
            )
        credentials_obj.refresh(GRequest())
        self.access_token = credentials_obj.token

    def get_other_tokens(self, exclude_email):
        tokens = []
        try:
            docs = self.db.collection("Users-Fcm").stream()
            for doc in docs:
                data = doc.to_dict()
                if data.get("email") != exclude_email and data.get("status") == "active":
                    tokens.append(data.get("token"))
        except Exception as e:
            print("Firestore error:", e)
        return tokens

    def send_fcm_notification(self, tokens, title, body, data=None):
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json; UTF-8",
        }

        for token in tokens:
            payload = {
                "message": {
                    "token": token,
                    "data": {
                        "title": title,
                        "body": body,
                        **(data or {})
                    }
                }
            }

            response = requests.post(self.url, headers=headers, json=payload)
            if response.status_code != 200:
                print(f"Failed to send to {token}: {response.text}")
            else:
                print(f"Notification sent to {token}")


api_validator = ApiValidator()
server = ServerFunctions()

def get_current_period():
    now = datetime.now().strftime("%H:%M")

    for block in notification_sets:
        start, end = block["range"]
        if start < end:
            if start <= now <= end:
                return block
        else:
            # Handles 22:00 - 02:00 (overnight)
            if now >= start or now <= end:
                return block
    return None

def send_random_time_notification():
    while True:
        try:
            block = get_current_period()
            if not block:
                time.sleep(300)
                continue

            message = random.choice(block["messages"])
            title = "Feeling something?"
            body = message

            server.token()
            active_tokens = server.get_other_tokens(exclude_email=None)
            if active_tokens:
                server.send_fcm_notification(tokens=active_tokens, title=title, body=body)
                print(f"[AutoNotify] Sent '{body}' to {len(active_tokens)} users.")
            else:
                print("[AutoNotify] No active tokens found.")

        except Exception as e:
            print("[AutoNotify Error]:", e)

        time.sleep(7200)

threading.Thread(target=send_random_time_notification, daemon=True).start()

# ========= Notification Endpoint =========
@app.post("/notify")
def send_notification(request: Request, data: UserData):
    server.token()
    client_key = request.headers.get("x-api-key")
    if not api_validator.validate(client_key):
        raise HTTPException(status_code=401, detail="Invalid API Key")

    try:
        other_tokens = server.get_other_tokens(data.email)
        if not other_tokens:
            raise HTTPException(status_code=404, detail="No active tokens found")

        server.send_fcm_notification(
            tokens=other_tokens,
            title=f"{data.aliasName} has {data.doneWhatTitle}",
            body=f"There is a {data.doneWhatBody} by {data.aliasName} check it out.",
            data={"Notification Type": "Alert"}
        )
        return {"message": "Notifications sent!"}
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail="Internal server error")

# ========= Dummy Ping Route =========
@app.get("/ping")
def ping():
    return {"status": "Server is active"}

# ========= Self-Pinger Thread =========
def ping_self():
    while True:
        try:
            url = os.environ.get("SELF_URL", "https://notification-server-kqga.onrender.com/ping")
            res = requests.get(url)
            print(f"[Ping] Status: {res.status_code}")
        except Exception as e:
            print("[Ping Error]:", e)
        time.sleep(120)  # every 2 mins

threading.Thread(target=ping_self, daemon=True).start()

# ========= Health Check Helpers =========
async def cors_health_preflight(
    request: Request,
    origin: str = Header(default="*"),
    access_control_request_method: str = Header(default=""),
    access_control_request_headers: str = Header(default="*"),
):
    if request.method == "OPTIONS":
        return JSONResponse(
            status_code=200,
            content={},
            headers={
                "Access-Control-Allow-Origin": origin,
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": access_control_request_headers,
                "Access-Control-Max-Age": "86400"
            }
        )

def collect_health_data():
    cpu = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory().percent
    disk = psutil.disk_usage('/').percent
    load_avg = os.getloadavg() if hasattr(os, 'getloadavg') else (0.0, 0.0, 0.0)
    uptime = round(time.time() - startTime, 2)
    threads = process.num_threads()
    process_memory = round(process.memory_info().rss / (1024 ** 2), 2)

    return {
        "serverId": serverId,
        "cpu": cpu,
        "memory": memory,
        "disk": disk,
        "uptime": uptime,
        "loadAvg": {
            "1m": round(load_avg[0], 2),
            "5m": round(load_avg[1], 2),
            "15m": round(load_avg[2], 2)
        },
        "threads": threads,
        "processMemoryMB": process_memory,
        "active": True
    }

# ========= Health Route =========
@app.api_route("/health", methods=["GET", "OPTIONS"])
async def get_health_route(
    request: Request,
    cors_response=Depends(cors_health_preflight)
):
    if request.method == "OPTIONS":
        return cors_response

    api_key = request.headers.get("x-api-key")
    if not api_validator.validate(api_key):
        return JSONResponse(
            status_code=401,
            content={"message": False, "error": "Invalid API key"}
        )

    health_data = await run_in_threadpool(collect_health_data)

    return JSONResponse(
        status_code=200,
        content=health_data,
        headers={
            "X-Server-ID": serverId,
            "X-Response-Time": str(round(time.time(), 2)),
            "Access-Control-Allow-Origin": "*",
        }
    )
