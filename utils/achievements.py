ACHIEVEMENTS = {
    "first_talk": "First Talk - Sent your first message!",
    "trusted_friend": "Trusted Friend - Reached 80 trust!",
    "centurion": "Centurion - Sent 100 messages!",
    "spammer": "Spammer - Got muted for spamming!",
    "night_owl": "Night Owl - Chatted after midnight!",
    "quiz_master": "Quiz Master - 10 correct quiz answers!",
    "gift_giver": "Gift Giver - Sent your first gift!",
    "anime_nerd": "Anime Nerd - Mentioned anime 20 times!",
    "streak_3": "Streak 3 - Chatted 3 days in a row!",
    "streak_7": "Streak 7 - Chatted 7 days in a row!"
}

async def check_achievements(user, db, message) -> list:
    awarded = []
    current_achievements = [a.achievement_type for a in await db.get_user_achievements(user.id)]
    
    def grant(name):
        if name not in current_achievements:
            awarded.append(name)
            
    if user.message_count == 1:
        grant("first_talk")
    if user.trust >= 80:
        grant("trusted_friend")
    if user.message_count >= 100:
        grant("centurion")
        
    for a in awarded:
        await db.add_achievement(user.id, a)
        
    return awarded
