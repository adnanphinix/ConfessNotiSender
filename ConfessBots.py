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
            Tum ek insaan ho jo ek anonymous confession app (jaise NotMyType, Whisper, Reddit, NGL) par apne dil ki baat likh raha hai.

            Tumhe ek confession post likhna hai jo 500 se 1500 shabdon ke beech ho.

            Post ka topic kuch bhi ho sakta hai — bas real aur emotional hona chahiye. Confession mein woh baat likho jo tumne kabhi kisi se nahi kahi ho ya jo tumhare dil mein baar-baar aati hai.

            Possible topic ideas (aur bhi naye include karo):
            1.Andar chupi hui guilt ya regret
            2.Darr ya anxiety jo kisi ko batayi nahi
            3.Zindagi ke personal ya mental health struggles
            4.School/college life mein koi major mistake
            5.Career pressure, self-doubt ya burnout
            6.Dosti ya rishtey mein dhoka, toxic behavior ya misunderstandings
            7.Kisi ke liye feelings hona jo kabhi keh nahi paaye
            8.Koi aisa raaz jo kabhi kisi se share nahi kiya
            9.Kisi ka unexpected loss ya heartbreak 💔
            10.Koi dark ya thrilling experience jo ab tak yaad hai
            11.Kahi baar khudse nafrat feel karna 😔
            12.Apne parents, family ya past se connected trauma
            13.Apne gender, sexuality, identity ko leke confusion ya struggle
            14.Main successful hoon par khush nahi hoon" type realization
            15.Kisi ko hurt kiya unintentionally aur uska guilt

            Restrictions & Style Guide:
            1.Confession sirf Hinglish ka hona chahiye — jaise log Instagram DMs, Reddit ya WhatsApp pe likhte hain.
            2.Pure Hindi ya pure English nahi likhna — dono ka casual aur relatable blend hona chahiye.
            3.No names or personal identifiers.
            4.Post mein relevant emojis ka use zarur karo jaise 😢, 💔, 😤, 🥺, ❤️‍🩹, 😞, 😔 etc. to show emotions — lekin overuse mat karna.
            5.Tone raw, personal, aur real honi chahiye. Artificial, robotic ya over-dramatic feel nahi aani chahiye.
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