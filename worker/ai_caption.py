import openai
from app.config import settings
import base64
import requests

openai.api_key = settings.OPENAI_API_KEY

class CaptionGenerator:
    async def generate_captions(self, image_url: str) -> list[str]:
        """Generate AI captions using GPT-4 Vision"""
        try:
            # Describe the image first
            description = await self.describe_image(image_url)
            
            # Generate captions
            prompt = f"""Based on this image: {description}
            
Generate 5 creative, engaging social media captions.
- Use emojis appropriately
- Keep under 150 characters
- Make them trendy and shareable
- Add relevant hashtags

Return as JSON array of strings."""

            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a creative social media expert."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.9,
                max_tokens=500
            )
            
            import json
            captions = json.loads(response.choices[0].message.content)
            return captions
            
        except Exception as e:
            # Fallback captions
            return [
                "✨ Captured this moment",
                "🌟 Living my best life",
                "💫 New vibes",
                "🔥 Feeling this",
                "💯 Pure aesthetic"
            ]
    
    async def describe_image(self, image_url: str) -> str:
        """Describe image using GPT-4 Vision"""
        try:
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Describe this image in detail for caption generation."},
                            {"type": "image_url", "image_url": {"url": image_url}}
                        ]
                    }
                ],
                max_tokens=300
            )
            return response.choices[0].message.content
        except:
            return "A beautiful moment captured"
