import subprocess
import os, asyncio, json
from pydantic import BaseModel
from trancription import Transcriber
from simli import Simli
from refinePitchText2 import refinePitch

class Pitch(BaseModel):
    
    video_path: str

    def get_audio_path(self):
        video_extension = self.video_path.split(".")[-1]
        audio_path = self.video_path.replace(video_extension, "wav")
        return audio_path

    def load_audio_file(self):
        audio_path = self.get_audio_path()
        if os.path.exists(audio_path):
            return
        
        command = f"ffmpeg -i {self.video_path} -ab 160k -ac 2 -ar 44100 -vn {audio_path}"
        subprocess.call(command, shell=True)

    def get_transcription(self):
        self.load_audio_file()
        audio_path = self.get_audio_path()
        transcriber = Transcriber(audo_file_path=audio_path)
        return transcriber.transcribe()

    async def improve_transcription(self):
        transcript = json.loads(self.get_transcription())
        text = await refinePitch(transcript, "/home/znasif/llama.cpp/models/Llama-3.1.gguf", 8080, "Make it very funny")
        self.create_new_video(text)

    def create_new_video(self, text):
        return Simli(text).get_video_url()

async def main():
    pitch = Pitch(video_path="video.mp4")
    await pitch.improve_transcription()

if __name__ == "__main__":
    asyncio.run(main())