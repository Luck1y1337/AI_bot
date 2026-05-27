import time
from typing import Optional

def parse_time(time_str: str) -> Optional[float]:
    units = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
    total_seconds = 0
    current_num = ''
    
    for char in time_str:
        if char.isdigit():
            current_num += char
        elif char in units and current_num:
            total_seconds += int(current_num) * units[char]
            current_num = ''
        else:
            return None
            
    if total_seconds > 0:
        return time.time() + total_seconds
    return None

def format_time_remaining(fire_at: float) -> str:
    rem = max(0, fire_at - time.time())
    if rem < 60:
        return f"{int(rem)} seconds"
    elif rem < 3600:
        return f"{int(rem//60)} minutes"
    else:
        return f"{int(rem//3600)} hours"
