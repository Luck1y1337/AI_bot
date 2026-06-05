import asyncio
from database.repository import Database

async def seed_cards(db: Database):
    cards = [
        # Common (Stats: 5-10)
        ('Обычная Махиро', 'Common', 5, ''),
        ('Махиро в пижаме', 'Common', 7, ''),
        ('Злая Михари', 'Common', 6, ''),
        ('Соня Махиро', 'Common', 8, ''),
        ('Смущенная Махиро', 'Common', 6, ''),
        ('Махиро за компьютером', 'Common', 7, ''),
        ('Каэде с чаем', 'Common', 6, ''),
        ('Радостная Момидзи', 'Common', 7, ''),
        ('Асахи на пробежке', 'Common', 8, ''),
        ('Школьная форма Махиро', 'Common', 9, ''),
        ('Михари за работой', 'Common', 8, ''),
        ('Случайно упавшая Махиро', 'Common', 5, ''),
        ('Удивленная Каэде', 'Common', 7, ''),
        ('Скучающая Момидзи', 'Common', 6, ''),
        ('Махиро ест сладости', 'Common', 9, ''),
        
        # Rare (Stats: 15-25)
        ('Михари-ученый', 'Rare', 15, ''),
        ('Каэде с макияжем', 'Rare', 18, ''),
        ('Стесняшка Момидзи', 'Rare', 16, ''),
        ('Махиро в купальнике', 'Rare', 20, ''),
        ('Михари с зельем', 'Rare', 22, ''),
        ('Асахи на турнире', 'Rare', 19, ''),
        ('Махиро-горничная', 'Rare', 25, ''),
        ('Каэде готовит ужин', 'Rare', 17, ''),
        ('Момидзи в мужской одежде', 'Rare', 21, ''),
        ('Махиро на горячих источниках', 'Rare', 24, ''),
        ('Михари в ярости', 'Rare', 23, ''),
        ('Махиро играет на консоли', 'Rare', 18, ''),
        
        # Epic (Stats: 35-50)
        ('Махиро-геймер (Pro)', 'Epic', 40, ''),
        ('Асахи-спортсменка', 'Epic', 35, ''),
        ('Михари-гений', 'Epic', 45, ''),
        ('Старшая сестра Каэде', 'Epic', 42, ''),
        ('Махиро-айдол', 'Epic', 50, ''),
        ('Момидзи-пацанка', 'Epic', 38, ''),
        ('Махиро в костюме кошки', 'Epic', 48, ''),
        ('Пьяная Каэде', 'Epic', 46, ''),
        ('Махиро на фестивале', 'Epic', 44, ''),
        
        # Legendary (Stats: 100-150)
        ('Легендарная Истинная Махиро', 'Legendary', 100, ''),
        ('Гениальное Зелье Михари', 'Legendary', 120, ''),
        ('Богиня Каэде', 'Legendary', 110, ''),
        ('Абсолютный Геймер Махиро', 'Legendary', 150, ''),
        ('Махиро: Возвращение брата', 'Legendary', 140, '')
    ]
    
    existing = await db.get_all_cards()
    existing_names = {c[1] for c in existing} # c[1] is name
    
    added = 0
    for c in cards:
        if c[0] not in existing_names:
            await db._conn.execute('INSERT INTO cards (name, rarity, stats, image_path) VALUES (?, ?, ?, ?)', c)
            added += 1
            
    if added > 0:
        await db._conn.commit()
        print(f'Seeded {added} new cards!')
    else:
        print('No new cards to seed.')

if __name__ == "__main__":
    async def run_local_seed():
        db = Database()
        await db.connect()
        await seed_cards(db)
        await db.close()
    asyncio.run(run_local_seed())
