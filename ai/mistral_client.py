import httpx
import asyncio
import logging

logger = logging.getLogger(__name__)

class MistralClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = httpx.AsyncClient(timeout=30.0)

    async def generate_response(self, prompt: str, system_prompt: str) -> str:
        url = "https://api.mistral.ai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "mistral-small-latest",
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ]
        }
        
        for attempt in range(3):
            try:
                response = await self.client.post(url, headers=headers, json=data)
                response.raise_for_status()
                return response.json()['choices'][0]['message']['content']
            except httpx.HTTPError as e:
                logger.error(f"Mistral API error (attempt {attempt+1}): {e}")
                if attempt == 2:
                    return "Uh... my brain hurts, give me a sec..."
                await asyncio.sleep(2 ** attempt)

    async def analyze_image(self, image_url: str) -> str:
        # Simulated vision endpoint or using Mistral Vision when available.
        # Currently, mistral-small doesn't support vision, but as requested:
        # "calls Mistral vision to get a brief description"
        # We will use pixtral-12b-2409 if available, or simulate it.
        url = "https://api.mistral.ai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "pixtral-12b-2409",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Describe this image briefly in one sentence."},
                        {"type": "image_url", "image_url": image_url}
                    ]
                }
            ]
        }
        try:
            response = await self.client.post(url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
        except Exception as e:
            logger.error(f"Vision error: {e}")
            return "some random stuff"

    async def close(self):
        await self.client.aclose()
