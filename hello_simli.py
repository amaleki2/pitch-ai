import streamlit as st
import requests
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Retrieve API keys from environment variables
elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
simli_api_key = os.getenv("SIMLI_API_KEY")

# Streamlit app
st.title("Text to Video Stream")

# Text input for the user to enter the text
user_text = st.text_area("Enter the text for the video", height=200)

# Button to generate video
if st.button("Generate Video"):
    url = "https://api.simli.ai/textToVideoStream"

    payload = {
        "ttsAPIKey": elevenlabs_api_key,
        "simliAPIKey": simli_api_key,
        "faceId": "tmp9i8bbq7c",
        "requestBody": {
            "audioProvider": "ElevenLabs",
            "text": user_text,
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

    response = requests.request("POST", url, json=payload, headers=headers)
    response_data = response.json()
    print(response_data)

    if response.status_code == 200:
        hls_url = response_data.get('hls_url')
        print(hls_url)
        if hls_url:
            video_html = f"""
<link href="https://vjs.zencdn.net/7.11.4/video-js.css" rel="stylesheet" />
<script src="https://vjs.zencdn.net/7.11.4/video.min.js"></script>
<video-js id="my-video" class="vjs-default-skin" controls preload="auto" width="640" height="264" data-setup='{{ "techOrder": ["html5", "flash"] }}'>
    <source src="{hls_url}" type="application/x-mpegURL">
</video-js>
<script>
    var player = videojs('my-video');
</script>
"""
            st.components.v1.html(video_html, height=300)
        else:
            st.error("No stream URL found in response")
    else:
        st.error(f"Error: {response.status_code}")
        st.error(response.text)