import random
from typing import Tuple

def analyze_triggers(text: str) -> Tuple[int, str, dict]:
    text = text.lower()
    trust_delta = 0
    mood_force = None
    
    categories = {
        "anime": ["anime", "manga", "weeb", "otaku"],
        "greetings": ["hello", "hi", "hey", "morning"],
        "school": ["school", "homework", "teacher", "study"],
        "food": ["food", "eat", "hungry", "snack"],
        "sleep": ["sleep", "tired", "bed", "night"],
        "compliments": ["cute", "pretty", "smart", "good girl"],
        "toxic": ["fuck", "shit", "bitch", "stupid", "hate", "ugly"],
        "kind": ["thank you", "thanks", "please", "help"],
    }
    
    found = {k: any(word in text for word in words) for k, words in categories.items()}
    
    if found["toxic"]:
        trust_delta -= 15
        mood_force = random.choice(["annoyed", "sad"])
    if found["compliments"]:
        trust_delta += 12
        mood_force = "happy"
    if found["kind"] and not found["toxic"]:
        trust_delta += 7
    
    # Base delta for just talking normally
    if not found["toxic"] and not found["compliments"] and not found["kind"]:
        trust_delta += 2
        
    return trust_delta, mood_force, found
