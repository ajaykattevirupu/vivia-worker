from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import os
import uuid
from pathlib import Path
import tempfile

# Local worker modules
from worker.video_enhancer import VideoEnhancer
from worker.photo_enhancer import PhotoEnhancer
from worker.ai_caption import CaptionGenerator

app = FastAPI(title="VIVIA AI Worker")

# ===========================
# Models
# ===========================

class ProcessRequest(BaseModel):
    job_id: str
    media_url: str
    user_id: str

class ProcessResult(BaseModel):
    media_url: str
    thumbnail_url: str
    caption: str
    captions: list[str]
    music_url: str | None
    ai_style: str
    media_type: str


# ===========================
# Main Processing Endpoint
# ===========================

@app.post("/process", response_model=ProcessResult)
async def process_media(request: ProcessRequest):
    """Main AI processing pipeline."""
    try:
        # 1. Download media
        media_path = await download_media(request.media_url)

        # 2. Detect file type
        media_type = detect_media_type(media_path)

        # 3. Process media based on type
        if media_type == "video":
            result = await process_video(media_path, request.user_id)
        else:
            result = await process_photo(media_path, request.user_id)

        # 4. Generate AI captions
        caption_gen = CaptionGenerator()
        captions = await caption_gen.generate_captions(result["media_url"])

        result["caption"] = captions[0] if captions else ""
        result["captions"] = captions
        result["media_type"] = media_type

        # 5. Cleanup
        if os.path.exists(media_path):
            os.remove(media_path)

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ===========================
# Helper Functions
# ===========================

async def download_media(url: str) -> str:
    """Downloads media file to temp directory."""
    temp_dir = tempfile.gettempdir()
    filename = f"{uuid.uuid4()}{Path(url).suffix}"
    filepath = os.path.join(temp_dir, filename)

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()

        with open(filepath, 'wb') as f:
            f.write(response.content)

    return filepath


def detect_media_type(filepath: str) -> str:
    """Detects if media is a video or photo."""
    video_exts = ['.mp4', '.mov', '.avi', '.mkv', '.webm']
    ext = Path(filepath).suffix.lower()

    return "video" if ext in video_exts else "photo"


async def process_video(video_path: str, user_id: str) -> dict:
    """Process video using AI + FFmpeg."""
    enhancer = VideoEnhancer()
    return await enhancer.enhance_video(video_path, user_id)


async def process_photo(photo_path: str, user_id: str) -> dict:
    """Process photo using AI."""
    enhancer = PhotoEnhancer()
    return await enhancer.enhance_photo(photo_path, user_id)
