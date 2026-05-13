from typing import List, Tuple

from fastapi import FastAPI

from utils import logger


def register_routers(app: FastAPI, prefix: str = "/api/v1") -> None:
    routers_config: List[Tuple[str, str, List[str], bool]] = [
        ("auth", "", ["Authentication"], True),
        ("voice", "", ["Voice"], True),
        ("music", "", ["Music"], True),
        ("personality", "", ["Personality"], True),
        ("server", "", ["Server"], True),
        ("agent", "", ["Agent"], True),
    ]

    registered_count = 0
    skipped_count = 0

    for module_name, router_prefix, tags, enabled in routers_config:
        if not enabled:
            continue

        try:
            module = __import__(f"api.routes.v1.{module_name}", fromlist=["router"])

            if hasattr(module, "router"):
                router = getattr(module, "router")
                app.include_router(router, prefix=f"{prefix}{router_prefix}", tags=tags)
                registered_count += 1
                logger.info(f"Registered router: {prefix}{router_prefix}")

        except ImportError as e:
            logger.warning(f"Router not found: {prefix}{router_prefix} - {module_name} ({e})")
            skipped_count += 1
        except Exception as e:
            logger.error(f"Failed to register {prefix}{router_prefix}: {e}")

    logger.info(f"Router registration complete: {registered_count} registered, {skipped_count} skipped")


__all__ = ["register_routers"]
