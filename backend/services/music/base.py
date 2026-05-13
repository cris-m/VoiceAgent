from abc import abstractmethod

import numpy as np

from services.base import BaseService


class BaseMusicService(BaseService):
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        style_tags: list[str],
        duration: float,
        tempo: int | None,
        seed: int | None,
    ) -> tuple[np.ndarray, int]: ...
