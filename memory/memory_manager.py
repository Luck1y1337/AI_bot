from .short_term import ShortTermMemory
from .long_term import LongTermMemory

class MemoryManager:
    def __init__(self, long_term: LongTermMemory, short_term: ShortTermMemory):
        self.long = long_term
        self.short = short_term

    async def extract_and_update(self, user_id: int, text: str):
        text_lower = text.lower()
        updates = {}
        if "my name is" in text_lower:
            name = text.split("my name is")[-1].strip()
            updates["name"] = name
        if "i like" in text_lower or "i love" in text_lower:
            updates["interests"] = [text]
        if "anime" in text_lower:
            updates["anime_preferences"] = ["likes anime"]
        
        if updates:
            await self.long.update_user_memory(user_id, updates)
