import json
import os
import aiofiles

class LongTermMemory:
    def __init__(self, filepath="data/long_term.json"):
        self.filepath = filepath
        self.data = {}

    async def load(self):
        if os.path.exists(self.filepath):
            async with aiofiles.open(self.filepath, 'r') as f:
                content = await f.read()
                self.data = json.loads(content) if content else {}
        else:
            self.data = {}

    async def save(self):
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        async with aiofiles.open(self.filepath, 'w') as f:
            await f.write(json.dumps(self.data, indent=4))

    def get_user_memory(self, user_id: int) -> dict:
        return self.data.get(str(user_id), {"name": None, "interests": [], "anime_preferences": [], "favorite_topics": [], "important_facts": []})

    async def update_user_memory(self, user_id: int, updates: dict):
        user_id_str = str(user_id)
        if user_id_str not in self.data:
            self.data[user_id_str] = {"name": None, "interests": [], "anime_preferences": [], "favorite_topics": [], "important_facts": []}
        
        for key, value in updates.items():
            if isinstance(self.data[user_id_str][key], list) and isinstance(value, list):
                self.data[user_id_str][key].extend([v for v in value if v not in self.data[user_id_str][key]])
            else:
                self.data[user_id_str][key] = value
        
        await self.save()
