import os
import openai
import json

# Load from environment (Railway → Variables)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai.api_key = OPENAI_API_KEY


class CaptionGenerator:
    async def generate_captions(self, image_url: str) -> list[str]:
        """Generate AI captions using GPT-4o Vision."""
        try:
            # Step 1: Describe the image using GPT-4o Vision
            description = await self.describe_image(image_url)

            # Step 2: Ask GPT-4o to write 5 captions
            prompt = f"""
Based on this image description: "{description}"

Generate 5 creative, engaging social media captions.
Requirements:
- Use emojis
- Keep under 150 characters
- Make it aesthetic, trendy, and viral-ready
- Add relevant hashtags
- Return output ONLY as a JSON array of strings
            """

            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a creative social media caption expert."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.9,
                max_tokens=500,
            )

            raw = response.choices[0].message["content"]

            # Parse JSON array
            captions = json.loads(raw)

            return captions

        except Exception as e:
            print("Caption error:", str(e))
            return [
                "✨ Capturing the vibe",
                "🔥 Living in the moment",
                "💫 Aesthetic energy",
                "🌟 Pure mood",
                "📸 Vibes only"
            ]


    async def describe_image(self, image_url: str) -> str:
        """Use GPT-4o Vision to describe the image."""
        try:
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Describe this image clearly for caption generation."},
                            {"type": "image_url", "image_url": {"url": image_url}}
                        ]
                    }
                ],
                max_tokens=300
            )

            return response.choices[0].message["content"]

        except Exception as e:
            print("Vision error:", str(e))
            return "A beautifully captured moment"
