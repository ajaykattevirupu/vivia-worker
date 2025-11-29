import os
import uuid
from pathlib import Path
import tempfile
import replicate
import requests
from PIL import Image, ImageEnhance, ImageFilter
from supabase import create_client


class PhotoEnhancer:
    def __init__(self):
        # Load from environment variables in Railway Worker
        SUPABASE_URL = os.getenv("SUPABASE_URL")
        SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

        if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
            raise ValueError("Supabase environment variables are missing in worker")

        self.supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    
    async def enhance_photo(self, photo_path: str, user_id: str) -> dict:
        """Complete photo enhancement pipeline"""
        temp_dir = tempfile.gettempdir()
        output_id = str(uuid.uuid4())
        
        # Step 1: AI upscaling & face enhancement
        enhanced = os.path.join(temp_dir, f"{output_id}_enhanced.jpg")
        await self.ai_enhance(photo_path, enhanced)
        
        # Step 2: Color correction
        corrected = os.path.join(temp_dir, f"{output_id}_corrected.jpg")
        await self.color_correct(enhanced, corrected)
        
        # Step 3: Aesthetic filters
        filtered = os.path.join(temp_dir, f"{output_id}_filtered.jpg")
        await self.apply_filters(corrected, filtered)
        
        # Step 4: Thumbnail
        thumbnail = os.path.join(temp_dir, f"{output_id}_thumb.jpg")
        await self.generate_thumbnail(filtered, thumbnail)
        
        # Step 5: Upload to Supabase
        media_url = await self.upload_to_storage(filtered, user_id, bucket="processed_media")
        thumbnail_url = await self.upload_to_storage(thumbnail, user_id, bucket="thumbnails")
        
        # Cleanup
        for f in [enhanced, corrected, filtered, thumbnail]:
            if os.path.exists(f):
                os.remove(f)
        
        return {
            "media_url": media_url,
            "thumbnail_url": thumbnail_url,
            "music_url": None,
            "ai_style": "enhanced"
        }
    
    async def ai_enhance(self, input_path: str, output_path: str):
        """AI upscaling using Real-ESRGAN on Replicate"""
        try:
            with open(input_path, "rb") as f:
                output = replicate.run(
                    "nightmareai/real-esrgan:42fed1c4974146d4d2414e2be2c5277c7fcf05fcc3a73abf41610695738c1d7b",
                    input={"image": f, "scale": 2, "face_enhance": True}
                )

            res = requests.get(output)
            with open(output_path, "wb") as f:
                f.write(res.content)

        except Exception:
            # PIL fallback
            img = Image.open(input_path)
            img = img.resize((img.width * 2, img.height * 2), Image.LANCZOS)
            img.save(output_path, quality=95)
    
    async def color_correct(self, input_path: str, output_path: str):
        img = Image.open(input_path)
        
        img = ImageEnhance.Contrast(img).enhance(1.3)
        img = ImageEnhance.Color(img).enhance(1.2)
        img = ImageEnhance.Brightness(img).enhance(1.1)
        img = ImageEnhance.Sharpness(img).enhance(1.5)
        
        img.save(output_path, quality=95)
    
    async def apply_filters(self, input_path: str, output_path: str):
        img = Image.open(input_path)
        
        img = img.filter(ImageFilter.GaussianBlur(radius=0.5))
        img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))
        
        img.save(output_path, quality=95)
    
    async def generate_thumbnail(self, photo_path: str, output_path: str):
        img = Image.open(photo_path)
        img.thumbnail((400, 400))
        img.save(output_path, quality=85)
    
    async def upload_to_storage(self, file_path: str, user_id: str, bucket: str) -> str:
        filename = f"{user_id}/{uuid.uuid4()}.jpg"

        with open(file_path, "rb") as f:
            self.supabase.storage.from_(bucket).upload(filename, f)

        return self.supabase.storage.from_(bucket).get_public_url(filename)
