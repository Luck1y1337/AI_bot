import hashlib
import os
from gtts import gTTS
import asyncio
import uuid

async def generate_tts(text: str) -> str:
    os.makedirs("cache/tts", exist_ok=True)
    text_hash = hashlib.md5(text.encode()).hexdigest()
    mp3_path = f"cache/tts/{text_hash}.mp3"
    ogg_path = f"cache/tts/{text_hash}.ogg"

    if os.path.exists(ogg_path):
        return ogg_path

    # Run gTTS in a thread to avoid blocking
    def create_mp3():
        tts = gTTS(text=text, lang='en', tld='co.jp') # trying to sound a bit japanese
        tts.save(mp3_path)
    
    await asyncio.to_thread(create_mp3)

    # Convert to OGG for Telegram Voice
    cmd = f"ffmpeg -i {mp3_path} -c:a libopus -b:a 32k {ogg_path} -y"
    proc = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    await proc.communicate()
    
    if os.path.exists(ogg_path):
        return ogg_path
    return mp3_path
