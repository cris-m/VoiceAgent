import io
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

STATIC_DIR = Path(__file__).parent.parent / "static"
NARRATIONS_DIR = STATIC_DIR / "narrations"
MUSICS_DIR = STATIC_DIR / "musics"


def ensure_dirs():
    NARRATIONS_DIR.mkdir(parents=True, exist_ok=True)
    MUSICS_DIR.mkdir(parents=True, exist_ok=True)


def _dir_for(file_type: str) -> Path:
    if file_type == "narration":
        return NARRATIONS_DIR
    elif file_type == "music":
        return MUSICS_DIR
    else:
        raise ValueError(f"Unknown file type: {file_type}")


def _url_prefix(file_type: str) -> str:
    if file_type == "narration":
        return "/static/narrations"
    elif file_type == "music":
        return "/static/musics"
    else:
        raise ValueError(f"Unknown file type: {file_type}")


def save_audio_file(
    wav_buffer: io.BytesIO,
    file_type: str,
    user_id: str,
    duration: float,
    sample_rate: int,
    prompt: str,
    voice_name: str = "",
) -> dict:
    file_id = str(uuid.uuid4())
    d = _dir_for(file_type)
    wav_path = d / f"{file_id}.wav"
    json_path = d / f"{file_id}.json"

    wav_buffer.seek(0)
    wav_path.write_bytes(wav_buffer.read())

    meta = {
        "id": file_id,
        "user_id": user_id,
        "file_type": file_type,
        "prompt": prompt[:500] if prompt else "",
        "voice_name": voice_name,
        "duration": round(duration, 2),
        "sample_rate": sample_rate,
        "url": f"{_url_prefix(file_type)}/{file_id}.wav",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    json_path.write_text(json.dumps(meta, indent=2))
    return meta


def list_files(file_type: str, user_id: str) -> list[dict]:
    """List all saved files for a user, newest first.

    Only returns files where the sidecar JSON's user_id matches.
    """
    d = _dir_for(file_type)
    results = []

    if not d.exists():
        return results

    for p in d.glob("*.json"):
        try:
            meta = json.loads(p.read_text())
            if meta.get("user_id") == user_id:
                results.append(meta)
        except Exception:
            continue

    return sorted(results, key=lambda x: x.get("created_at", ""), reverse=True)


def delete_file(file_type: str, file_id: str, user_id: str) -> bool:
    """Delete WAV and JSON files for a file.

    Returns False if file not found or user_id doesn't match (permission denied).
    """
    d = _dir_for(file_type)
    json_path = d / f"{file_id}.json"
    wav_path = d / f"{file_id}.wav"

    if not json_path.exists():
        return False

    try:
        meta = json.loads(json_path.read_text())
        if meta.get("user_id") != user_id:
            return False  # Permission denied
    except Exception:
        return False

    json_path.unlink(missing_ok=True)
    wav_path.unlink(missing_ok=True)
    return True
