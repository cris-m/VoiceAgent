from typing import Any, Dict, List

API_TITLE = "VoiceAgent API"
API_DESCRIPTION = """
## Real-Time Voice Agent API

A production-ready voice agent backend supporting real-time audio streaming,
speech-to-text, text-to-speech, and LLM-powered conversations.

### Features

* **Real-time Audio Streaming** - WebSocket-based bidirectional audio
* **Speech-to-Text** - Whisper (faster-whisper, local)
* **Text-to-Speech** - Kokoro ONNX (fast, local) and Pocket TTS (voice cloning)
* **LLM Integration** - OpenAI GPT, Anthropic Claude
* **Voice Activity Detection** - Automatic turn-taking
* **Interrupt Handling** - Barge-in support

### Authentication

API endpoints require authentication via Bearer token or API key.

### Rate Limits

- WebSocket connections: 10 per user
- REST API: 100 requests/minute
"""

API_VERSION = "0.1.0"
API_TERMS_OF_SERVICE = "https://example.com/terms"

API_CONTACT: Dict[str, str] = {
    "name": "VoiceAgent Support",
    "url": "https://example.com/support",
    "email": "support@example.com",
}

API_LICENSE: Dict[str, str] = {
    "name": "MIT",
    "url": "https://opensource.org/licenses/MIT",
}

API_TAGS: List[Dict[str, Any]] = [
    {
        "name": "Server",
        "description": "Server health and status endpoints.",
    },
    {
        "name": "Voice",
        "description": "Voice agent endpoints - audio streaming, STT, TTS, and LLM processing.",
    },
]

OPENAPI_URL = "/openapi.json"
DOCS_URL = "/docs"
REDOC_URL = "/redoc"

