import os
from typing import Optional

from deepagents.backends import (
    CompositeBackend,
    FilesystemBackend,
    StateBackend,
    StoreBackend,
)


def composite_backend(user_id: Optional[str] = None):
    """Return a backend factory namespaced by user_id.

    Each user gets isolated /memories/ and /workspace/ stores so that
    multi-user deployments don't share conversation state.  The /skills/
    route is read-only and shared across all users.

    Args:
        user_id: Unique user identifier from Config.  When None, falls back
                 to "anonymous" so a missing ID still works but is isolated
                 from real user sessions.
    """
    base_dir = os.path.dirname(os.path.dirname(__file__))
    skills_dir = os.path.abspath(os.path.join(base_dir, "skills"))

    safe_uid = (user_id or "anonymous").replace("/", "_").replace(".", "_").strip("_") or "anonymous"

    def factory(runtime):
        routes = {
            f"/memories/{safe_uid}/": StoreBackend(runtime),
            f"/workspace/{safe_uid}/": StoreBackend(runtime),
            "/skills/": FilesystemBackend(
                root_dir=skills_dir,
                virtual_mode=True,
            ),
        }

        return CompositeBackend(
            default=StateBackend(runtime),
            routes=routes
        )

    return factory