import io
import wave
from uuid import UUID

import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse

from api.dependency.auth import get_current_user_id
from schemas.music import MusicGenerateRequest
from services.music.ace_step import get_music_service
from utils.file_storage import delete_file, list_files, save_audio_file

router = APIRouter(prefix="/music")


def _to_wav(audio: np.ndarray, sample_rate: int) -> io.BytesIO:
    """Convert float32 numpy array to WAV BytesIO. Handles both mono and stereo."""
    if audio.ndim == 1:
        channels = 1
        samples = audio
    elif audio.ndim == 2:
        channels = audio.shape[0]
        samples = audio
    else:
        raise ValueError(f"Unexpected audio shape: {audio.shape}")

    pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype(np.int16)

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())
    buf.seek(0)
    return buf


@router.post("/generate")
async def generate_music(
    request: MusicGenerateRequest,
    user_id: UUID = Depends(get_current_user_id),
):
    """Generate music from text description using ACE-Step and save to disk."""
    svc = get_music_service()
    try:
        audio, sample_rate = await svc.generate(
            prompt=request.prompt,
            style_tags=request.style_tags,
            duration=request.duration,
            tempo=request.tempo,
            seed=request.seed,
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    duration = len(audio) / sample_rate
    wav_buffer = _to_wav(audio, sample_rate)

    meta = save_audio_file(
        wav_buffer=wav_buffer,
        file_type="music",
        user_id=str(user_id),
        duration=duration,
        sample_rate=sample_rate,
        prompt=request.prompt,
        voice_name=", ".join(request.style_tags) if request.style_tags else "",
    )
    return JSONResponse(content=meta)


@router.get("/list")
async def list_music(user_id: UUID = Depends(get_current_user_id)):
    """List all music tracks saved by the current user."""
    return list_files("music", str(user_id))


@router.delete("/{file_id}")
async def delete_music(file_id: str, user_id: UUID = Depends(get_current_user_id)):
    """Delete a music track."""
    ok = delete_file("music", file_id, str(user_id))
    if not ok:
        raise HTTPException(status_code=404, detail="File not found or permission denied")
    return {"deleted": file_id}
