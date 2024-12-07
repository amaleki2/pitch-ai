

from pydantic import BaseModel
from deepgram import (
    DeepgramClient,
    PrerecordedOptions,
    FileSource,
)
import os
from datetime import datetime
import httpx


class Transcriber(BaseModel):
    audo_file_path: str
    
    def _transcribe(self):
        deepgram = DeepgramClient(api_key=os.getenv("DEEPGRAM"))

        # STEP 2 Call the transcribe_file method on the rest class
        with open(self.audo_file_path, "rb") as file:
            buffer_data = file.read()

        payload: FileSource = {
            "buffer": buffer_data,
        }

        # STEP 2 Call the transcribe_url method on the prerecorded class
        options = PrerecordedOptions(
            model="nova-2",
            smart_format=True,
            summarize="v2",
        )
        response = deepgram.listen.rest.v("1").transcribe_file(
            payload, options, timeout=httpx.Timeout(300.0, connect=10.0)
        )

        return response

    def transcribe(self):
        try:
            
            before = datetime.now()
            response = self._transcribe()
            after = datetime.now()
            print(response.to_json(indent=4))
            print("")
            difference = after - before
            print(f"time: {difference.seconds}")       

        except Exception as e:
            print(f"Exception: {e}")

        
        return response