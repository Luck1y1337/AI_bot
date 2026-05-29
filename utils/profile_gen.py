from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io
import os
from database.models import User

def create_rounded_mask(size, radius):
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0) + size, radius, fill=255)
    return mask

async def generate_profile_image(user: User, avatar_bytes: bytes = None) -> io.BytesIO:
    # Set sizes
    bg_width, bg_height = 800, 450
    
    # 1. Load Background
    bg_path = "media/profile_bg/default.png"
    if os.path.exists(bg_path):
        base = Image.open(bg_path).convert("RGBA").resize((bg_width, bg_height))
    else:
        # Fallback background
        base = Image.new("RGBA", (bg_width, bg_height), (40, 44, 52))

    # Add dark overlay for readability
    overlay = Image.new("RGBA", (bg_width, bg_height), (0, 0, 0, 100))
    base = Image.alpha_composite(base, overlay)

    draw = ImageDraw.Draw(base)

    # 2. Load Fonts
    try:
        font_large = ImageFont.truetype("media/fonts/Roboto-Bold.ttf", 48)
        font_medium = ImageFont.truetype("media/fonts/Roboto-Bold.ttf", 28)
        font_small = ImageFont.truetype("media/fonts/Roboto-Regular.ttf", 24)
    except IOError:
        font_large = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_small = ImageFont.load_default()

    # 3. Draw Avatar
    avatar_size = 180
    avatar_x, avatar_y = 50, 50
    
    if avatar_bytes:
        try:
            avatar_img = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
            avatar_img = avatar_img.resize((avatar_size, avatar_size))
        except Exception:
            avatar_img = Image.new("RGBA", (avatar_size, avatar_size), (100, 100, 100))
    else:
        avatar_img = Image.new("RGBA", (avatar_size, avatar_size), (100, 100, 100))

    # Make avatar circular
    mask = Image.new("L", (avatar_size, avatar_size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse((0, 0, avatar_size, avatar_size), fill=255)
    
    # Create circular avatar
    circular_avatar = Image.new("RGBA", (avatar_size, avatar_size), (0, 0, 0, 0))
    circular_avatar.paste(avatar_img, (0, 0), mask=mask)
    
    # Draw avatar border
    draw.ellipse((avatar_x-4, avatar_y-4, avatar_x+avatar_size+4, avatar_y+avatar_size+4), fill=(255, 255, 255, 200))
    base.paste(circular_avatar, (avatar_x, avatar_y), circular_avatar)

    # 4. Draw User Info
    text_x = 260
    
    # Name
    name = user.username if user.username else f"Игрок {user.id}"
    draw.text((text_x, 60), name, font=font_large, fill=(255, 255, 255))
    
    # Stats
    draw.text((text_x, 130), f"Доверие Махиро: {user.trust}%", font=font_medium, fill=(255, 150, 200))
    draw.text((text_x, 170), f"Настроение: {user.mood.capitalize()}", font=font_medium, fill=(150, 200, 255))
    draw.text((text_x, 210), f"Коины: {user.coins} 🪙", font=font_medium, fill=(255, 223, 0))

    # 5. Draw XP Bar
    xp_level = (user.xp // 1000) + 1
    xp_current = user.xp % 1000
    xp_needed = 1000

    bar_x = 50
    bar_y = 350
    bar_width = 700
    bar_height = 30
    
    # Draw background of bar
    draw.rounded_rectangle((bar_x, bar_y, bar_x + bar_width, bar_y + bar_height), 15, fill=(50, 50, 50, 200))
    
    # Draw fill
    fill_width = int((xp_current / xp_needed) * bar_width)
    if fill_width > 15:
        draw.rounded_rectangle((bar_x, bar_y, bar_x + fill_width, bar_y + bar_height), 15, fill=(100, 255, 100))
        
    # Draw Level Text
    draw.text((bar_x, bar_y - 40), f"Уровень {xp_level}", font=font_medium, fill=(255, 255, 255))
    draw.text((bar_x + bar_width - 150, bar_y - 40), f"{xp_current} / {xp_needed} XP", font=font_small, fill=(200, 200, 200))

    # Output to BytesIO
    out_io = io.BytesIO()
    base.save(out_io, format="PNG")
    out_io.seek(0)
    return out_io
