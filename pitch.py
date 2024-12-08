import subprocess
import os
from pydantic import BaseModel
from trancription import Transcriber
from simli import Simli
import json




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

    def improve_transcription(self, transcription):
        return transcription.results.channels[0].alternatives[0].transcript
    
    def get_new_video_urls(self):
        transcription = self.get_transcription()
        new_transcription = self.improve_transcription(transcription)
        new_video_urls = Simli(text=new_transcription).get_video_url()
        return new_video_urls
    
        

if __name__ == "__main__":
    pitch = Pitch(video_path="data/video.mp4")
    url = pitch.get_new_video_urls()
    print(url)
    