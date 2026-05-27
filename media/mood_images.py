from PIL import Image, ImageDraw, ImageFont
import os

def create_placeholders():
    os.makedirs("media/images", exist_ok=True)
    moods = {
        "normal": "gray",
        "happy": "yellow",
        "annoyed": "red",
        "tired": "purple",
        "sleepy": "blue",
        "excited": "orange",
        "sad": "darkblue"
    }
    
    for mood, color in moods.items():
        path = f"media/images/{mood}.png"
        if not os.path.exists(path):
            img = Image.new('RGB', (400, 400), color=color)
            d = ImageDraw.Draw(img)
            d.text((150, 180), mood.upper(), fill="white")
            img.save(path)
