import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from api.routes import register_routers
from config import (
    API_CONTACT,
    API_DESCRIPTION,
    API_LICENSE,
    API_TAGS,
    API_TERMS_OF_SERVICE,
    API_TITLE,
    API_VERSION,
    DOCS_URL,
    OPENAPI_URL,
    REDOC_URL,
    settings,
)
from core.error_handler import register_error_handlers
from services.voice_pipeline import initialize_voice_pipeline, shutdown_voice_pipeline
from services.agent.client import initialize_agent_client, shutdown_agent_client
from services.music.ace_step import initialize_music_service, shutdown_music_service
from config.database import init_db, close_db
from config.redis import get_redis, close_redis
from utils import logger
from utils.file_storage import ensure_dirs


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up...")
    try:
        ensure_dirs()
        logger.info("✓ Static file directories created")
        await init_db()
        logger.info("✓ Database initialized")
        await get_redis()
        logger.info("✓ Redis connected")
        await initialize_voice_pipeline()
        await initialize_agent_client()
        await initialize_music_service()

        from services.voice_pipeline import get_voice_pipeline
        from services.agent.client import get_agent_client
        pipeline = get_voice_pipeline()
        agent = get_agent_client()

        stt_name = type(pipeline.stt).__name__ if pipeline.stt else "Unknown"
        tts_name = pipeline.tts.name if pipeline.tts else "Unknown"
        agent_id = agent._default_assistant_id or "Unknown"

        logger.info(f"🚀 Backend Ready — STT: {stt_name} | TTS: {tts_name} | Agent: {agent_id}")
    except Exception as e:
        logger.error(f"Failed to initialize services: {e}")
        raise

    yield

    logger.info("Shutting down...")
    try:
        await shutdown_music_service()
        await shutdown_agent_client()
        await shutdown_voice_pipeline()
        await close_db()
        await close_redis()
        logger.info("✓ Services shut down cleanly")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


def create_app() -> FastAPI:
    is_production = settings.ENVIRONMENT == "production"
    openapi_url = None if is_production else OPENAPI_URL
    docs_url = None if is_production else DOCS_URL
    redoc_url = None if is_production else REDOC_URL

    app = FastAPI(
        title=API_TITLE,
        description=API_DESCRIPTION,
        version=API_VERSION,
        terms_of_service=API_TERMS_OF_SERVICE,
        contact=API_CONTACT,
        license_info=API_LICENSE,
        openapi_tags=API_TAGS,
        openapi_url=openapi_url,
        docs_url=docs_url,
        redoc_url=redoc_url,
        lifespan=lifespan,
    )

    register_error_handlers(app)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )

    register_routers(app)

    static_dir = os.path.join(os.path.dirname(__file__), "static")
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/")
    async def root():
        return FileResponse(os.path.join(static_dir, "index.html"))


    return app


app = create_app()
