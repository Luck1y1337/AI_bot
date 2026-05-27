import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import os
import asyncio

async def generate_activity_chart(data: dict) -> str:
    os.makedirs("cache/charts", exist_ok=True)
    path = "cache/charts/activity.png"
    
    def draw():
        plt.figure(figsize=(10, 5))
        plt.bar(data.keys(), data.values(), color='skyblue')
        plt.title("Message Activity (Last 14 Days)")
        plt.xlabel("Days")
        plt.ylabel("Messages")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(path)
        plt.close()
        
    await asyncio.to_thread(draw)
    return path

async def generate_trust_chart(data: list) -> str:
    os.makedirs("cache/charts", exist_ok=True)
    path = "cache/charts/trust.png"
    
    def draw():
        plt.figure(figsize=(10, 5))
        plt.plot(range(len(data)), data, color='gold', marker='o')
        plt.title("Trust Progression")
        plt.xlabel("Interactions")
        plt.ylabel("Trust Level")
        plt.tight_layout()
        plt.savefig(path)
        plt.close()
        
    await asyncio.to_thread(draw)
    return path
