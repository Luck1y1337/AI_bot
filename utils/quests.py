from database.repository import Database
from datetime import datetime

def get_start_of_day() -> float:
    now = datetime.now()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return start.timestamp()

async def increment_quest_progress(user_id: int, task_type: str, amount: int, db: Database):
    start_of_day = get_start_of_day()
    contracts = await db.get_user_contracts(user_id, start_of_day)
    
    for c in contracts:
        c_id, t_type, progress, target, is_completed, dt = c
        if t_type == task_type and not is_completed:
            new_progress = min(progress + amount, target)
            await db.update_contract_progress(c_id, new_progress, False)
