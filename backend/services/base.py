from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Optional

from utils import get_logger


class ServiceStatus(Enum):
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    ERROR = "error"
    STOPPED = "stopped"


class BaseService(ABC):
    def __init__(self, name: str):
        self.name = name
        self.status = ServiceStatus.UNINITIALIZED
        self.logger = get_logger(f"service.{name}")
        self._error: Optional[str] = None

    @abstractmethod
    async def initialize(self) -> None:
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        pass

    async def start(self) -> None:
        self.status = ServiceStatus.INITIALIZING
        self.logger.info(f"Initializing {self.name}...")

        try:
            await self.initialize()
            self.status = ServiceStatus.READY
            self.logger.info(f"{self.name} is ready")
        except Exception as e:
            self.status = ServiceStatus.ERROR
            self._error = str(e)
            self.logger.error(f"{self.name} failed to initialize: {e}")
            raise

    async def stop(self) -> None:
        self.logger.info(f"Shutting down {self.name}...")

        try:
            await self.shutdown()
            self.status = ServiceStatus.STOPPED
            self.logger.info(f"{self.name} stopped")
        except Exception as e:
            self.status = ServiceStatus.ERROR
            self._error = str(e)
            self.logger.error(f"{self.name} failed to shutdown: {e}")
            raise

    def get_status(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "error": self._error,
        }

    @property
    def is_ready(self) -> bool:
        return self.status == ServiceStatus.READY
