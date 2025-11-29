from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import httpx
import os
import uuid
from pathlib import Path
import tempfile

from worker.video_enhancer import VideoEnhancer
from worker.photo_enhancer import PhotoEnhancer
from worker.ai_caption import CaptionGenerator

app = FastAPI(title="VIVIA AI Worker")

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

@app.post("/process", response_model=ProcessResult)
async def process_media(request: ProcessRequest):
    try:
        media_path = await download_media(request.media_url)
        media_type = detect_media_type(media_path)

        if media_type == "video":
            result = await process_video(media_path, request.user_id)
        else:
            result = await process_photo(media_path, request.user_id)

        caption_gen = CaptionGenerator()
        captions = await caption_gen.generate_captions(result["media_url"])

        result["caption"] = captions[0] if captions else ""
        result["captions"] = captions
        result["media_type"] = media_type

        os.remove(media_path)
        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def download_media(url: str) -> str:
    tmp = tempfile.gettempdir()
    filename = f"{uuid.uuid4()}{Path(url).suffix}"
    filepath = os.path.join(tmp, filename)

    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        resp.raise_for_status()
        with open(filepath, "wb") as f:
            f.write(resp.content)

    return filepath


def detect_media_type(path: str) -> str:
    ext = Path(path).suffix.lower()
    return "video" if ext in [".mp4", ".mov", ".avi", ".mkv", ".webm"] else "photo"


async def process_video(path: str, user_id: str):
    return await VideoEnhancer().enhance_video(path, user_id)


async def process_photo(path: str, user_id: str):
    return await PhotoEnhancer().enhance_photo(path, user_id)
