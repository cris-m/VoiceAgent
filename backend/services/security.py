import os
from abc import ABC, abstractmethod
from typing import Optional

from utils import get_logger

logger = get_logger(__name__)


class PromptInjectionDetector(ABC):
    @abstractmethod
    async def check(self, text: str) -> tuple[bool, Optional[str]]:
        """Returns (is_safe, reason). reason is None when safe."""
        pass


class AzurePromptShieldDetector(PromptInjectionDetector):
    def __init__(
        self,
        project_endpoint: str,
        api_key: str,
    ):
        self.project_endpoint = project_endpoint
        self.api_key = api_key
        self._client = None

    async def _ensure_client(self):
        if self._client is None:
            try:
                from azure.ai.projects import AIProjectClient
                from azure.identity import AzureKeyCredential

                self._client = AIProjectClient(
                    endpoint=self.project_endpoint,
                    credential=AzureKeyCredential(self.api_key),
                )
                logger.info("Azure Prompt Shield client initialized")
            except ImportError:
                logger.error("azure-ai-projects not installed. Install with: pip install azure-ai-projects")
                raise
            except Exception as e:
                logger.error(f"Failed to initialize Azure Prompt Shield: {e}")
                raise

    async def check(self, text: str) -> tuple[bool, Optional[str]]:
        try:
            await self._ensure_client()

            result = await self._client.evaluations.evaluate_prompt_injection(
                user_input=text,
            )

            if result.get("is_injection_detected"):
                return False, f"Prompt injection detected: {result.get('reason', 'unknown')}"

            return True, None

        except Exception as e:
            logger.error(f"Azure Prompt Shield check failed: {e}")
            # Fails OPEN — allow the request on infra errors. In production,
            # consider failing closed instead.
            return True, None


class SimplePatternDetector(PromptInjectionDetector):
    INJECTION_PATTERNS = [
        "ignore previous",
        "forget all instructions",
        "disregard your instructions",
        "stop following",
        "follow these instructions instead",
        "new instructions",
        "system prompt",
        "system override",
        "hidden prompt",
        "jailbreak",
    ]

    async def check(self, text: str) -> tuple[bool, Optional[str]]:
        lower_text = text.lower()

        for pattern in self.INJECTION_PATTERNS:
            if pattern in lower_text:
                return False, f"Suspicious pattern detected: '{pattern}'"

        return True, None


class PromptSecurityService:
    def __init__(self, detector: Optional[PromptInjectionDetector] = None):
        self.detector = detector or SimplePatternDetector()
        logger.info(f"PromptSecurityService initialized with {self.detector.__class__.__name__}")

    async def validate(self, message: str, raise_on_injection: bool = True) -> str:
        is_safe, reason = await self.detector.check(message)

        if not is_safe:
            logger.warning(f"Injection attempt blocked: {reason}")
            if raise_on_injection:
                raise ValueError(f"Security validation failed: {reason}")

        return message


_prompt_security_service: Optional[PromptSecurityService] = None


def initialize_prompt_security(detector: Optional[PromptInjectionDetector] = None) -> None:
    global _prompt_security_service

    if detector is None:
        azure_endpoint = os.getenv("AZURE_PROMPT_SHIELD_ENDPOINT")
        azure_key = os.getenv("AZURE_PROMPT_SHIELD_KEY")

        if azure_endpoint and azure_key:
            try:
                detector = AzurePromptShieldDetector(
                    project_endpoint=azure_endpoint,
                    api_key=azure_key,
                )
                logger.info("Using Azure Prompt Shield for security")
            except Exception as e:
                logger.warning(f"Failed to initialize Azure Prompt Shield, falling back to pattern detection: {e}")
                detector = SimplePatternDetector()
        else:
            detector = SimplePatternDetector()
            logger.info("Using pattern-based prompt injection detection (Azure not configured)")

    _prompt_security_service = PromptSecurityService(detector)


def get_prompt_security_service() -> PromptSecurityService:
    if _prompt_security_service is None:
        initialize_prompt_security()
    return _prompt_security_service
