from collections import deque

class ShortTermMemory:
    def __init__(self, maxlen=20):
        self.buffers = {}
        self.maxlen = maxlen

    def get_history(self, user_id: int) -> list:
        if user_id not in self.buffers:
            self.buffers[user_id] = deque(maxlen=self.maxlen)
        return list(self.buffers[user_id])

    def add_message(self, user_id: int, role: str, content: str):
        if user_id not in self.buffers:
            self.buffers[user_id] = deque(maxlen=self.maxlen)
        self.buffers[user_id].append({"role": role, "content": content})
