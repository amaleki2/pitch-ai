import os
import requests
from pydantic import BaseModel

SIMLI_URL = "https://api.simli.ai/textToVideoStream"


class Pitch(BaseModel):
    
    video_url: str

    def read_video(self):
        pass

    def read_audio(self):
        pass

    def read_transcription(self):
        pass

    def improve_transcription(self):
        pass

    def create_new_video(self, text):

        payload = {
            "ttsAPIKey": os.getenv("ELEVENLABS_API_KEY"),
            "simliAPIKey": os.getenv("SIMLI_API_KEY"),
            "faceId": "tmp9i8bbq7c",
            "requestBody": {
                "audioProvider": "ElevenLabs",
                "text": text,
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