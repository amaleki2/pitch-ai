import os
from pydantic import BaseModel
import requests

SIMLI_URL= "https://api.simli.ai/textToVideoStream"    

class Simli(BaseModel):
    text: str

    def get_video_url(self):
        payload = {
            "ttsAPIKey": os.getenv("ELEVENLABS_API_KEY"),
            "simliAPIKey": os.getenv("SIMLI_API_KEY"),
            "faceId": "tmp9i8bbq7c",
            "requestBody": {
                "audioProvider": "ElevenLabs",
                "text": self.text,
                "voiceName": "pMsXgVXv3BLzUgSXRplE",
                "model_id": "eleven_turbo_v2",
                "voice_settings": {
                    "stability": 0.1,
                    "similarity_boost": 0.3,
                    "style": 0.2
                }
            }
        }
        headers = {"Content-Type": "application/json"}
        response = requests.request("POST", SIMLI_URL, json=payload, headers=headers)
        response_data = response.json()
        if response.status_code == 200:
            hls_url = response_data.get('hls_url')
            return hls_url
        