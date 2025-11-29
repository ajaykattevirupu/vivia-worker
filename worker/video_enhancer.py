import subprocess
import os
import uuid
from pathlib import Path
import tempfile
import replicate
import requests
from supabase import create_client
import random


class VideoEnhancer:
    def __init__(self):

        # Worker loads environment variables directly from Railway
        SUPABASE_URL = os.getenv("SUPABASE_URL")
        SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

        if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
            raise ValueError("Supabase environment variables missing in worker")

        self.supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

        self.music_library = [
            "https://example.com/music/upbeat1.mp3",
            "https://example.com/music/chill1.mp3",
            "https://example.com/music/energetic1.mp3"
        ]
    
    async def enhance_video(self, video_path: str, user_id: str) -> dict:
        """Complete video enhancement pipeline"""
        temp_dir = tempfile.gettempdir()
        output_id = str(uuid.uuid4())
        
        # Step 1: Stabilization
        stabilized = os.path.join(temp_dir, f"{output_id}_stabilized.mp4")
        await self.stabilize_video(video_path, stabilized)
        
        # Step 2: Color Grading
        graded = os.path.join(temp_dir, f"{output_id}_graded.mp4")
        await self.apply_color_grade(stabilized, graded)
        
        # Step 3: Upscale (Replicate)
        upscaled = os.path.join(temp_dir, f"{output_id}_upscaled.mp4")
        await self.upscale_video(graded, upscaled)
        
        # Step 4: Add Transitions
        final = os.path.join(temp_dir, f"{output_id}_final.mp4")
        await self.add_transitions(upscaled, final)
        
        # Step 5: Reframe to Mobile (9:16)
        mobile = os.path.join(temp_dir, f"{output_id}_mobile.mp4")
        await self.reframe_to_mobile(final, mobile)
        
        # Step 6: Thumbnail
        thumbnail = os.path.join(temp_dir, f"{output_id}_thumb.jpg")
        await self.generate_thumbnail(mobile, thumbnail)
        
        # Step 7: Music selection
        music_url = await self.select_music(mobile)
        
        # Step 8: Upload
        media_url = await self.upload_to_storage(mobile, user_id, bucket="processed_media")
        thumbnail_url = await self.upload_to_storage(thumbnail, user_id, bucket="thumbnails")
        
        # Cleanup temp files
        for file in [stabilized, graded, upscaled, final, mobile, thumbnail]:
            if os.path.exists(file):
                os.remove(file)
        
        return {
            "media_url": media_url,
            "thumbnail_url": thumbnail_url,
            "music_url": music_url,
            "ai_style": "cinematic"
        }
    
    async def stabilize_video(self, input_path: str, output_path: str):
        cmd = [
            'ffmpeg', '-i', input_path,
            '-vf', 'deshake',
            '-c:v', 'libx264', '-preset', 'medium',
            '-c:a', 'copy',
            output_path
        ]
        subprocess.run(cmd, check=True, capture_output=True)
    
    async def apply_color_grade(self, input_path: str, output_path: str):
        lut_filter = "curves=vintage"
        
        cmd = [
            'ffmpeg', '-i', input_path,
            '-vf', f'{lut_filter},eq=contrast=1.2:brightness=0.05:saturation=1.3',
            '-c:v', 'libx264', '-preset', 'medium',
            '-c:a', 'copy',
            output_path
        ]
        subprocess.run(cmd, check=True, capture_output=True)
    
    async def upscale_video(self, input_path: str, output_path: str):
        try:
            with open(input_path, 'rb') as f:
                output = replicate.run(
                    "nightmareai/real-esrgan:42fed1c4974146d4d2414e2be2c5277c7fcf05fcc3a73abf41610695738c1d7b",
                    input={
                        "image": f,
                        "scale": 2,
                        "face_enhance": True
                    }
                )
            
            res = requests.get(output)
            with open(output_path, 'wb') as f:
                f.write(res.content)
        
        except Exception:
            # fallback upscale
            cmd = [
                'ffmpeg', '-i', input_path,
                '-vf', 'scale=1080:1920:flags=lanczos',
                '-c:v', 'libx264', '-preset', 'medium',
                output_path
            ]
            subprocess.run(cmd, check=True, capture_output=True)
    
    async def add_transitions(self, input_path: str, output_path: str):
        cmd = [
            'ffmpeg', '-i', input_path,
            '-vf', 'fade=in:0:30,fade=out:st=8:d=1',
            '-c:v', 'libx264', '-preset', 'medium',
            '-c:a', 'copy',
            output_path
        ]
        subprocess.run(cmd, check=True, capture_output=True)
    
    async def reframe_to_mobile(self, input_path: str, output_path: str):
        cmd = [
            'ffmpeg', '-i', input_path,
            '-vf', 'scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920',
            '-c:v', 'libx264', '-preset', 'medium',
            '-c:a', 'copy',
            output_path
        ]
        subprocess.run(cmd, check=True, capture_output=True)
    
    async def generate_thumbnail(self, video_path: str, output_path: str):
        cmd = [
            'ffmpeg', '-i', video_path,
            '-ss', '00:00:01',
            '-vframes', '1',
            '-vf', 'scale=1080:1920',
            output_path
        ]
        subprocess.run(cmd, check=True, capture_output=True)
    
    async def select_music(self, video_path: str) -> str:
        return random.choice(self.music_library)
    
    async def upload_to_storage(self, file_path: str, user_id: str, bucket: str) -> str:
        filename = f"{user_id}/{uuid.uuid4()}.{Path(file_path).suffix[1:]}"
        
        with open(file_path, 'rb') as f:
            self.supabase.storage.from_(bucket).upload(filename, f)

        return self.supabase.storage.from_(bucket).get_public_url(filename)
