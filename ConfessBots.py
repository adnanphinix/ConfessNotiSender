import google.generativeai as genai
from itertools import cycle
import time
import os
import requests
import json
import datetime

class BotSender:
    def __init__(self):
        keys = [
            os.environ["key1"],
            os.environ["key2"],
            os.environ["key3"]
        ]
        users = [
            os.environ["user1"],
            os.environ["user2"],
            os.environ["user3"],
            os.environ["user4"],
            os.environ["user5"],
            os.environ["user6"]
        ]

        self.url = os.environ["url"]
        self.headers = {
            "x-api-key": os.environ["server_api"],
            "Content-Type": "application/json"
        }
        self.keyCycle = cycle(keys)
        self.userCycle = cycle(users)

    def clean_confession(self, text: str) -> str:
        lines = text.strip().split('\n')
        lines = lines[4:]  # Remove first 4 lines (assuming metadata or intro)
        cleaned_lines = [line for line in lines if not line.strip().startswith(("*", "-"))]
        return "\n".join(cleaned_lines).strip()

    def post_generator(self, key: str) -> str:
        genai.configure(api_key=key)
        model = genai.GenerativeModel("gemini-1.5-flash")  # Adjust if you're using another version
        prompt = """
Tum ek insaan ho jo ek anonymous confession app par apne dil ki baat likh raha hai.
Ek confession post likho jo 500 se 1500 shabdon ke beech ho.
Yeh confession kisi bhi topic par ho sakta hai:
- Andar chupi hui guilt ya regret
- Darr ya tanav
- Zindagi ke personal struggles
- College/school ya career ki problems
- Doston ya rishtey mein problems
- Koi secret jo kabhi kisi ko nahi bataya
- Koi thrilling ya dark experience

Example ideas:
- "Main apne best friend ke saath cheat kiya aur aaj tak us guilt mein jee raha hoon."
- "Main sabke beech hota hoon phir bhi akela feel karta hoon."
- "College mein ek aisi galti kari jo kabhi bhool nahi pa raha."
- "Main dar raha hoon ki kahin main apne toxic parents jaisa na ban jaun."

Confession post sirf aur sirf **Hinglish mein likhna hai** (Roman script Hindi-English mix), jaise log WhatsApp, Reddit ya Insta pe likhte hain.

**Post mein relevant emojis ka use karo** to express feelings like 😢, 😔, 😤, ❤️‍🩹, 😱, 😞, etc., jahan zarurat ho. 
Emojis se emotions aur clear hone chahiye.

Emotion raw aur real hona chahiye. Artificial ya robotic feel nahi aani chahiye. Naam ya identity mat likhna.

Please generate only the confession in Hinglish with emojis.
"""
        response = model.generate_content(prompt)
        return response.text.strip()

    def sender(self, current_user: str, post_data: str):
        payload = {
            "email": current_user,
            "date": datetime.datetime.now().isoformat(),
            "post": post_data,
            "isComment": True
        }

        server_response = requests.post(self.url, json=payload, headers=self.headers)

        if server_response.status_code == 200:
            print("✅ Posted successfully for", current_user)
        else:
            print("❌ Post error:", server_response.status_code, server_response.text)

    def caller(self):
        key = next(self.keyCycle)
        user = next(self.userCycle)

        response_text = self.post_generator(key)
        clean_text = self.clean_confession(response_text)
        self.sender(user, clean_text)

        time.sleep(3600) 