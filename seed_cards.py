import asyncio
from database.repository import Database

async def seed_cards():
    db = Database()
    await db.connect()
    
    cards = [
        ('Обычная Махиро', 'Common', 5, ''),
        ('Махиро в пижаме', 'Common', 7, ''),
        ('Злая Михари', 'Common', 6, ''),
        ('Соня Махиро', 'Common', 8, ''),
        
        ('Михари-ученый', 'Rare', 15, ''),
        ('Каэде с макияжем', 'Rare', 18, ''),
        ('Стесняшка Момидзи', 'Rare', 16, ''),
        
        ('Махиро-геймер (Pro)', 'Epic', 40, ''),
        ('Асахи-спортсменка', 'Epic', 35, ''),
        
        ('Легендарная Истинная Махиро', 'Legendary', 100, ''),
        ('Гениальное Зелье Михари', 'Legendary', 120, '')
    ]
    
    existing = await db.get_all_cards()
    if not existing:
        for c in cards:
            await db._conn.execute('INSERT INTO cards (name, rarity, stats, image_path) VALUES (?, ?, ?, ?)', c)
        await db._conn.commit()
        print('Cards seeded!')
    else:
        print('Cards already exist.')

asyncio.run(seed_cards())
