def generate_progress_bar(current: int, total: int, length: int = 10, fill_char: str = "█", empty_char: str = "░") -> str:
    """Генерирует текстовый прогресс-бар"""
    if total <= 0:
        return empty_char * length
        
    percent = min(1.0, current / total)
    filled_len = int(length * percent)
    empty_len = length - filled_len
    
    return f"[{fill_char * filled_len}{empty_char * empty_len}]"
