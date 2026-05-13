from fastapi import APIRouter

from services.agent.client import get_agent_client
from services.voice_pipeline import get_voice_pipeline

router = APIRouter(tags=["Health"])


async def _get_health_status():
    try:
        pipeline = get_voice_pipeline()
        agent = get_agent_client()
        return {
            "pipeline": pipeline.is_initialized,
            "agent": agent.is_ready,
        }
    except RuntimeError:
        return {"pipeline": False, "agent": False}


@router.get("/health")
async def health():
    status = await _get_health_status()
    all_healthy = all(status.values())
    return {"status": "healthy" if all_healthy else "degraded", "services": status}


@router.get("/ready")
async def ready():
    status = await _get_health_status()
    all_ready = all(status.values())
    return {"status": "ready" if all_ready else "not_ready", "services": status}
