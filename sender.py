from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import firebase_admin
from firebase_admin import credentials, firestore
from google.oauth2 import service_account
from google.auth.transport.requests import Request
import os
import json
import requests

app = FastAPI()

# ======== Pydantic Model for Request =========
class UserData(BaseModel):
    email: str
    aliasName: str

# ========== Server Class ==========
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

            # OAuth2 token
            credentials_obj = service_account.Credentials.from_service_account_info(
                self.cred_json, scopes=self.SCOPES
            )
            credentials_obj.refresh(Request())
            self.access_token = credentials_obj.token

        except Exception as e:
            print("Initialization error:", e)
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

# ========== API Route ==========
@app.post("/notify")
def send_notification(data: UserData):
    try:
        server = ServerFunctions()
        other_tokens = server.get_other_tokens(data.email)
        if not other_tokens:
            raise HTTPException(status_code=404, detail="No active tokens found")
        
        server.send_fcm_notification(
            tokens=other_tokens,
            title="There is a new post",
            body=f"{data.aliasName} has posted something",
            data={"aliasName": data.aliasName}
        )
        return {"message": "Notifications sent!"}
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail="Internal server error")