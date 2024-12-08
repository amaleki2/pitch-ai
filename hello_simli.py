import streamlit as st
import requests
from dotenv import load_dotenv
import os, asyncio
from pitch import Pitch

# Load environment variables from .env file
load_dotenv()


async def run(video_path: str):
    st.title("Text to Video Stream")
    pitch = Pitch(video_path=video_path)

    # Button to generate video
    if st.button("Generate Video"):
       hls_url = await pitch.get_new_video_urls()
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
    

if __name__ == "__main__":
    video_path = "video.mp4"
    asyncio.run(run(video_path=video_path))