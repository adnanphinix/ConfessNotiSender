from fastapi import FastAPI, Request, HTTPException, Header
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

app = FastAPI()

# ========= Request Model =========
class UserData(BaseModel):
    email: str
    aliasName: str

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

            credentials_obj = service_account.Credentials.from_service_account_info(
                self.cred_json, scopes=self.SCOPES
            )
            credentials_obj.refresh(GRequest())
            self.access_token = credentials_obj.token

        except Exception as e:
            print("Firebase Initialization Error:", e)
            raise e

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

# ========= Notification Endpoint =========
@app.post("/notify")
def send_notification(request: Request, data: UserData):
    client_key = request.headers.get("x-api-key")

    if not api_validator.validate(client_key):
        raise HTTPException(status_code=401, detail="Invalid API Key")

    try:
        other_tokens = server.get_other_tokens(data.email)
        if not other_tokens:
            raise HTTPException(status_code=404, detail="No active tokens found")

        server.send_fcm_notification(
            tokens=other_tokens,
            title="New ConfessBot Alert",
            body=f"{data.aliasName} has something to say!",
            data={"aliasName": data.aliasName}
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

@app.api_route("/health", methods=["GET", "OPTIONS"])
async def get_health_route(
    request: Request,
    cors_response=Depends(cors_health_preflight)
):
    # Handle preflight CORS
    if request.method == "OPTIONS":
        return cors_response

    # Validate API key
    api_key = request.headers.get("x-api-key")
    if not validate.validate(api_key):
        return JSONResponse(
            status_code=401,
            content={"message": False, "error": "Invalid API key"}
        )

    # Collect and return health stats
    health_data = await run_in_threadpool(collect_health_data)

    return JSONResponse(
        status_code=200,
        content=health_data,
        headers={
            "X-Server-ID": serverId,
            "X-Response-Time": str(round(time.time(), 2)),
            "Access-Control-Allow-Origin": "*",  # for GET response
        }
    )
