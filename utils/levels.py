from database.models import User

XP_PER_LEVEL = 100

LEVEL_TITLES = {
    1: "Новичок",
    5: "Знакомый",
    10: "Приятель",
    15: "Друг Махиро",
    20: "Доверенный",
    25: "Ветеран",
    30: "Мастер",
    40: "Легенда",
    50: "Мифический",
}

LEVEL_REWARDS = {
    2: 200,
    5: 500,
    10: 1500,
    15: 3000,
    20: 5000,
    25: 7500,
    30: 10000,
    40: 20000,
    50: 50000,
}


def get_level(xp: int) -> int:
    return xp // XP_PER_LEVEL + 1


def get_xp_for_next(xp: int) -> tuple[int, int]:
    level = get_level(xp)
    current_in_level = xp - (level - 1) * XP_PER_LEVEL
    return current_in_level, XP_PER_LEVEL


def get_title(xp: int) -> str:
    level = get_level(xp)
    title = "Новичок"
    for req_level, t in sorted(LEVEL_TITLES.items()):
        if level >= req_level:
            title = t
    return title


def check_level_up(old_xp: int, new_xp: int) -> tuple[bool, int, int]:
    old_level = get_level(old_xp)
    new_level = get_level(new_xp)
    if new_level > old_level:
        reward = 0
        for lvl in range(old_level + 1, new_level + 1):
            reward += LEVEL_REWARDS.get(lvl, 100)
        return True, new_level, reward
    return False, old_level, 0
