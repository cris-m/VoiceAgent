import asyncio
import hmac
import io
import json
import os
import random
import re
import tempfile
import time
import wave
from typing import Optional

_FILLER_PHRASES = [
    "Hmm.",
    "Let me think.",
    "One sec.",
    "Got it.",
    "Okay.",
]
FILLER_DELAY_S = 1.2


_INCOMPLETE_LAST_WORDS = {
    "can",
    "could",
    "would",
    "should",
    "will",
    "shall",
    "may",
    "might",
    "must",
    "do",
    "does",
    "did",
    "have",
    "has",
    "had",
    "is",
    "are",
    "was",
    "were",
    "am",
    "be",
    "been",
    "being",
    "and",
    "but",
    "or",
    "nor",
    "so",
    "yet",
    "for",
    "because",
    "since",
    "although",
    "though",
    "while",
    "whereas",
    "if",
    "unless",
    "until",
    "when",
    "where",
    "as",
    "a",
    "an",
    "the",
    "my",
    "your",
    "his",
    "her",
    "its",
    "our",
    "their",
    "this",
    "that",
    "these",
    "those",
    "to",
    "of",
    "in",
    "on",
    "at",
    "by",
    "from",
    "with",
    "about",
    "into",
    "onto",
    "upon",
    "over",
    "under",
    "between",
    "through",
    "um",
    "uh",
    "uhm",
    "ahh",
    "er",
    "like",
    "well",
    "hmm",
    "what",
    "who",
    "whom",
    "whose",
    "where",
    "when",
    "why",
    "how",
    "which",
}
SEMANTIC_GRACE_MS = 700.0


def _is_incomplete_utterance(text: str) -> bool:
    """Hold the transcript if it ends in a hanging word (modal, conjunction,
    preposition, filler) so a paused-mid-thought user isn't cut off."""
    text = text.strip()
    if not text:
        return True
    stripped = text.rstrip(".!?,;: ")
    if not stripped:
        return True
    words = stripped.split()
    if len(words) <= 1:
        return False
    last = re.sub(r"[^\w]", "", words[-1]).lower()
    return last in _INCOMPLETE_LAST_WORDS


from uuid import UUID

import numpy as np
from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import JSONResponse
from pydub import AudioSegment

from api.dependency import check_rate_limit, verify_api_key
from api.dependency.auth import get_current_user_id
from config.settings import settings
from schemas.voice import (
    AgentStatus,
    ClonedVoicesResponse,
    LanguageInfo,
    LanguagesResponse,
    NarrationRequest,
    TranscriptionResponse,
    VoiceCloneResponse,
    VoiceConfig,
    VoiceConfigUpdate,
    VoiceInfo,
    VoicesResponse,
    VoiceStatusResponse,
)
from services.agent import get_agent_client
from services.stt.audio_chunker import AudioChunker
from services.tts.base import BaseTTS
from services.tts.text_chunker import TextChunker
from services.vad.silero import VADState
from services.voice_pipeline import create_voice_pipeline_for_connection, get_voice_pipeline
from utils import get_logger
from utils.file_storage import delete_file, list_files, save_audio_file
from utils.tts_sanitizer import sanitize_for_tts

logger = get_logger(__name__)
router = APIRouter(
    prefix="/voice",
    tags=["Voice"],
)

_config = VoiceConfig()
_status = AgentStatus.IDLE
_active_connections = 0
_connections_lock = asyncio.Lock()

_INJECTION_PATTERNS = [
    r"\n\s*(Human|Assistant|System|User):\s*",
    r"</?\w+>",
    r"\[INST\]|\[/INST\]",
    r"<\|im_start\||<\|im_end\|",
    r"`{3,}",
]
_INJECTION_REGEX = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)

_AUDIO_MAGIC_AT_OFFSET_0 = {
    b"RIFF": "wav",
    b"ID3": "mp3",
    b"\xff\xfb": "mp3",
    b"\xff\xfa": "mp3",
    b"\xff\xf3": "mp3",
    b"\xff\xf2": "mp3",
    b"\xff\xf1": "aac",
    b"\xff\xf9": "aac",
    b"OggS": "ogg",
    b"fLaC": "flac",
    b"FORM": "aiff",
    b"\x1a\x45\xdf\xa3": "webm",
}
_FTYP_MAGIC = b"ftyp"


def _validate_audio_magic_bytes(data: bytes) -> str:
    for magic, fmt in _AUDIO_MAGIC_AT_OFFSET_0.items():
        if data.startswith(magic):
            return fmt
    if len(data) >= 8 and data[4:8] == _FTYP_MAGIC:
        return "mp4"
    raise ValueError("Unsupported audio format")


def _sanitize_user_input(text: str, max_length: int = 5000) -> str:
    if not text or not isinstance(text, str):
        raise ValueError("Invalid input")

    if len(text) > max_length:
        raise ValueError(f"Input exceeds {max_length} characters")

    text = text.strip()

    if _INJECTION_REGEX.search(text):
        raise ValueError("Input contains invalid patterns")

    return text


def _apply_fade(audio: np.ndarray, sample_rate: int, fade_ms: int = 10) -> np.ndarray:
    """Apply fade-in/out to eliminate click artifacts at audio boundaries."""
    fade_samples = int(sample_rate * fade_ms / 1000)
    if len(audio) < fade_samples * 2:
        return audio

    audio = audio.copy()
    audio[:fade_samples] *= np.linspace(0, 1, fade_samples, dtype=np.float32)
    audio[-fade_samples:] *= np.linspace(1, 0, fade_samples, dtype=np.float32)
    return audio


def _read_wav_data(wav_buffer: io.BytesIO) -> tuple[np.ndarray, int]:
    wav_buffer.seek(0)
    with wave.open(wav_buffer, "rb") as wav_file:
        sample_rate = wav_file.getframerate()
        audio_int16 = np.frombuffer(wav_file.readframes(wav_file.getnframes()), dtype=np.int16)
        if wav_file.getnchannels() == 2:
            audio_int16 = audio_int16.reshape(-1, 2).mean(axis=1).astype(np.int16)
    return audio_int16, sample_rate


def _create_wav_buffer(audio_int16: np.ndarray, sample_rate: int) -> io.BytesIO:
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_int16.tobytes())
    wav_buffer.seek(0)
    return wav_buffer


def _supports_cloning(tts: BaseTTS) -> bool:
    from services.tts.pocket_tts import PocketTTS

    return isinstance(tts, PocketTTS)


_ABBREVIATIONS = {
    "mr.",
    "mrs.",
    "ms.",
    "dr.",
    "sr.",
    "jr.",
    "st.",
    "vs.",
    "etc.",
    "i.e.",
    "e.g.",
    "u.s.",
    "u.k.",
    "a.m.",
    "p.m.",
    "no.",
}
_SENTENCE_END_RE = re.compile(r"([.!?])(\s+|$)")


def _strip_markdown(text: str) -> str:
    """Remove markdown formatting while preserving text content.

    Removes: **bold**, *italic*, ### headers, - lists, etc.
    Preserves: actual text content and avoid eating content between unbalanced delimiters

    WARNING: sanitize_for_tts() collapses all whitespace before this runs, so the text
    is a single line here. Do NOT use DOTALL/re.MULTILINE as they can match across
    unrelated markdown delimiters and delete content between them.
    """
    # NO DOTALL — only match same-line pairs
    text = re.sub(r"\*\*([^\n]*?)\*\*", r"\1", text)
    text = re.sub(r"\*([^\n]*?)\*", r"\1", text)
    text = re.sub(r"__([^\n]*?)__", r"\1", text)

    text = re.sub(r"^#+\s+", "", text, flags=re.MULTILINE)

    # Pocket TTS tokenizes "---" as 3 punctuation tokens, eating into the
    # 50-token budget.
    text = re.sub(r"^\s*([-*_]\s*){3,}\s*$", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s+-{3,}\s+", " ", text)

    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)

    text = re.sub(r"^\s*>\s+", "", text, flags=re.MULTILINE)

    text = re.sub(r"\[([^\n]*?)\]\([^\n]*?\)", r"\1", text)

    text = re.sub(r"`([^\n]*?)`", r"\1", text)

    text = re.sub(r"\n\n+", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)

    return text.strip()


def _split_sentences(buffer: str) -> tuple[list[str], str]:
    """Extract complete sentences from a growing token buffer.

    Returns (complete_sentences, remaining_buffer).
    Handles abbreviations so "Dr. Smith said hi." isn't split after "Dr."
    """
    complete: list[str] = []
    last_end = 0

    for match in _SENTENCE_END_RE.finditer(buffer):
        end = match.end()
        candidate_end = match.start() + 1
        word_start = buffer.rfind(" ", 0, candidate_end) + 1
        word = buffer[word_start:candidate_end].lower()
        if word in _ABBREVIATIONS:
            continue
        sentence = buffer[last_end:end].strip()
        if sentence:
            complete.append(sentence)
        last_end = end

    remaining = buffer[last_end:]
    return complete, remaining


@router.websocket("/ws")
async def voice_websocket(websocket: WebSocket) -> None:
    """Real-time voice WebSocket using a fully concurrent streaming pipeline.

    Architecture:
      Task 1: Audio receiver       — reads WS bytes, feeds STT + VAD
      Task 2: Transcript collector — reads STT events, emits partials/finals
      Task 3: Response orchestrator — on final transcript, runs LLM → sentence queue
      Task 4: TTS streamer         — reads sentences, synthesizes, sends audio bytes

    All four tasks run concurrently via asyncio.gather. Queues decouple stages so
    the LLM doesn't wait for TTS, TTS doesn't wait for the LLM to finish, and
    STT runs DURING user speech rather than after.
    """
    from api.dependency import _get_client_ip, rate_limiter

    global _active_connections

    client_ip = _get_client_ip(websocket)

    if settings.API_KEY is not None:
        token = websocket.query_params.get("token")
        if not token or not hmac.compare_digest(token, settings.API_KEY):
            await websocket.close(code=4001, reason="Unauthorized")
            return

    # Rate-limit BEFORE accepting connection
    if not await rate_limiter.is_allowed(client_ip):
        await websocket.close(code=4029, reason="Rate limit exceeded")
        return

    async with _connections_lock:
        if _active_connections >= settings.MAX_WS_CONNECTIONS:
            await websocket.close(code=4002, reason="Too many connections")
            return
        _active_connections += 1

    await websocket.accept()
    logger.info(f"Voice WebSocket connected from {client_ip}")

    # Per-connection pipeline with isolated VAD prevents cross-talk between concurrent users
    pipeline = create_voice_pipeline_for_connection()
    agent = get_agent_client()
    sample_rate = 16000

    if not pipeline.is_initialized:
        await pipeline.initialize()
    if not agent.is_ready:
        await agent.start()

    thread = await agent.create_thread()
    thread_id = thread.thread_id
    logger.info(f"Created agent thread: {thread_id}")

    try:
        await websocket.send_json({"type": "thread", "thread_id": thread_id})
    except Exception as e:
        logger.warning(f"Client disconnected before receiving thread_id: {e}")
        return

    transcript_queue: asyncio.Queue[str] = asyncio.Queue(maxsize=4)
    sentence_queue: asyncio.Queue = asyncio.Queue(maxsize=8)
    interrupt_event = asyncio.Event()
    stop_event = asyncio.Event()
    is_responding_ref = {"value": False}
    last_vad_state_ref = {"value": None}
    turn_metrics: dict = {}
    connection_voice_id_ref = {"value": _config.voice_id}
    connection_speed_ref: dict = {"value": _config.speed}
    connection_language_ref: dict = {"value": _config.language}
    thread_title_set_ref = {"value": False}
    # Two-phase barge-in: stamps the moment VAD first reports SPEECH_START
    # during TTS playback. The interrupt only fires if speech continues for
    # BARGE_IN_HOLD_MS — short bursts (coughs, "uh-huh", "yeah") get filtered.
    barge_in_candidate_ref: dict = {"value": None}

    stt_session = await pipeline.open_stt_stream(sample_rate=sample_rate)
    stt_supports_streaming = pipeline.stt_supports_streaming
    logger.info(f"STT session opened (streaming={stt_supports_streaming}, provider={type(pipeline.stt).__name__})")

    async def audio_receiver() -> None:
        try:
            while not stop_event.is_set():
                message = await websocket.receive()

                if "text" in message:
                    try:
                        json_data = json.loads(message["text"])
                        if json_data.get("type") == "config":
                            if json_data.get("voice_id"):
                                connection_voice_id_ref["value"] = json_data["voice_id"]
                            if json_data.get("speed") is not None:
                                try:
                                    connection_speed_ref["value"] = float(json_data["speed"])
                                except (TypeError, ValueError):
                                    pass
                            if json_data.get("language"):
                                connection_language_ref["value"] = json_data["language"]
                            continue
                        elif json_data.get("type") == "text_input":
                            try:
                                text_input = _sanitize_user_input(json_data.get("text", ""))
                                await transcript_queue.put(text_input)
                                await websocket.send_json(
                                    {
                                        "type": "partial_transcript",
                                        "text": text_input,
                                        "is_final": True,
                                    }
                                )
                            except ValueError as e:
                                await websocket.send_json(
                                    {
                                        "type": "error",
                                        "message": f"Invalid input: {str(e)}",
                                    }
                                )
                            continue
                    except Exception as e:
                        logger.warning(f"Failed to parse JSON message: {e}")
                        continue

                if "bytes" not in message:
                    continue

                data = message["bytes"]

                audio_array = np.frombuffer(data, dtype=np.int16)

                await stt_session.send_audio(audio_array)

                vad_event, is_echo = pipeline.process_audio_chunk(audio_array)
                prob = pipeline.get_speech_probability(audio_array)

                # Two-phase barge-in: stamp on speech-start, confirm after
                # BARGE_IN_HOLD_MS of continuous speech. Do NOT gate on
                # is_echo — that flag is True throughout TTS playback so it
                # would block barge-in entirely.
                BARGE_IN_HOLD_MS = 200.0

                vad_state_now = pipeline.get_vad_state()
                ai_audible = is_responding_ref["value"] or pipeline.is_ai_speaking()

                speech_event = (
                    vad_event is not None and vad_event.state == VADState.SPEECH_START
                ) or vad_state_now == VADState.SPEAKING

                if (
                    ai_audible
                    and barge_in_candidate_ref["value"] is None
                    and not interrupt_event.is_set()
                    and speech_event
                ):
                    barge_in_candidate_ref["value"] = time.monotonic()
                    logger.info(
                        f"[Barge-in] Candidate stamped "
                        f"(prob={prob:.2f}, vad_state={vad_state_now.value}, "
                        f"is_responding={is_responding_ref['value']}, "
                        f"ai_speaking={pipeline.is_ai_speaking()})"
                    )
                elif (
                    speech_event
                    and barge_in_candidate_ref["value"] is None
                    and not interrupt_event.is_set()
                    and vad_event is not None
                    and vad_event.state == VADState.SPEECH_START
                ):
                    logger.info(
                        f"[Barge-in] Speech start but gate skipped "
                        f"(ai_audible={ai_audible}, "
                        f"is_responding={is_responding_ref['value']}, "
                        f"ai_speaking={pipeline.is_ai_speaking()})"
                    )

                candidate_at = barge_in_candidate_ref["value"]
                if candidate_at is not None and not interrupt_event.is_set():
                    elapsed_ms = (time.monotonic() - candidate_at) * 1000
                    if vad_state_now == VADState.SPEAKING and elapsed_ms >= BARGE_IN_HOLD_MS:
                        logger.info(
                            f"[Barge-in] Confirmed after {elapsed_ms:.0f}ms "
                            f"continuous speech (prob={prob:.2f}); interrupting"
                        )
                        interrupt_event.set()
                        barge_in_candidate_ref["value"] = None
                    elif vad_state_now not in (VADState.SPEAKING, VADState.SPEECH_START):
                        logger.info(
                            f"[Barge-in] Candidate dropped after {elapsed_ms:.0f}ms "
                            f"(VAD={vad_state_now.value}, treated as backchannel)"
                        )
                        barge_in_candidate_ref["value"] = None

                current_state = pipeline.get_vad_state().value
                if current_state != last_vad_state_ref["value"]:
                    await websocket.send_json(
                        {
                            "type": "vad",
                            "state": current_state,
                            "probability": round(prob, 2),
                            "is_speaking": pipeline.is_speaking(),
                            "is_echo": is_echo,
                            "aec_state": pipeline.get_aec_state(),
                            "is_responding": is_responding_ref["value"],
                        }
                    )
                    last_vad_state_ref["value"] = current_state

                # Streaming STT (Kyutai): the model handles end-of-utterance internally
                # via causal streaming — no commit signal required from the route.

                # Whisper is batch — local VAD decides when to close and transcribe.
                if (
                    not stt_supports_streaming
                    and vad_event is not None
                    and getattr(vad_event, "audio_buffer", None) is not None
                    and len(vad_event.audio_buffer) > 0
                ):
                    logger.info(f"[Batch STT] VAD endpoint reached ({vad_event.duration_ms:.0f}ms audio)")
                    # Close to flush; transcript_collector loop reopens for next turn.
                    await stt_session.close()
        except WebSocketDisconnect:
            logger.info("WS disconnect in audio_receiver")
            stop_event.set()
        except Exception as e:
            logger.error(f"audio_receiver error: {e}")
            stop_event.set()

    # Semantic-turn-detection grace window: if a final transcript looks
    # incomplete we hold it for SEMANTIC_GRACE_MS rather than dispatching to
    # the LLM; if more audio arrives in that window the two transcripts are
    # concatenated.
    pending_text_ref: dict = {"value": ""}
    pending_flush_task_ref: dict = {"task": None}

    async def _flush_pending_after_grace(text: str) -> None:
        """Flush a held-incomplete transcript to the LLM after the grace
        window expires with no further speech. Cancelled (and replaced)
        if a new transcript arrives that combines with this one."""
        try:
            await asyncio.sleep(SEMANTIC_GRACE_MS / 1000)
        except asyncio.CancelledError:
            return
        # Only flush if pending wasn't superseded by a fresh transcript.
        if pending_text_ref["value"] != text or stop_event.is_set():
            return
        pending_text_ref["value"] = ""
        turn_metrics["stt_final_at"] = time.monotonic()
        logger.info(f"[Turn] Grace expired, flushing as-is: '{text[:60]}'")
        try:
            await websocket.send_json(
                {
                    "type": "partial_transcript",
                    "text": text,
                    "is_final": True,
                }
            )
        except Exception:
            pass
        await transcript_queue.put(text)

    async def transcript_collector() -> None:
        """Read STT events, hold incomplete utterances briefly, push
        completed (or grace-expired) finals to the LLM queue."""
        nonlocal stt_session
        try:
            while not stop_event.is_set():
                try:
                    async for event in stt_session:
                        if stop_event.is_set():
                            return

                        if "stt_first_partial_at" not in turn_metrics:
                            turn_metrics["stt_first_partial_at"] = time.monotonic()

                        if not event.is_final:
                            if event.text:
                                await websocket.send_json(
                                    {
                                        "type": "partial_transcript",
                                        "text": event.text,
                                        "is_final": False,
                                    }
                                )
                            continue

                        text = (event.text or "").strip()
                        if not text:
                            continue

                        # Combine with any held-incomplete transcript so
                        # "Hey can you" + "book a flight" → "Hey can you book a flight".
                        combined = (
                            (pending_text_ref["value"] + " " + text).strip() if pending_text_ref["value"] else text
                        )

                        prev_task = pending_flush_task_ref["task"]
                        if prev_task and not prev_task.done():
                            prev_task.cancel()
                        pending_flush_task_ref["task"] = None

                        if _is_incomplete_utterance(combined):
                            pending_text_ref["value"] = combined
                            await websocket.send_json(
                                {
                                    "type": "partial_transcript",
                                    "text": combined,
                                    "is_final": False,
                                }
                            )
                            pending_flush_task_ref["task"] = asyncio.create_task(_flush_pending_after_grace(combined))
                            logger.info(
                                f"[Turn] Incomplete (last word looks hanging): "
                                f"'{combined[:60]}' — holding {SEMANTIC_GRACE_MS:.0f}ms"
                            )
                        else:
                            pending_text_ref["value"] = ""
                            turn_metrics["stt_final_at"] = time.monotonic()
                            await websocket.send_json(
                                {
                                    "type": "partial_transcript",
                                    "text": combined,
                                    "is_final": True,
                                }
                            )
                            logger.info(f"[Transcript Received] {combined}")
                            await transcript_queue.put(combined)

                            if not thread_title_set_ref["value"]:
                                thread_title_set_ref["value"] = True
                                title = combined.strip()[:45]
                                if len(combined.strip()) > 45:
                                    title += "…"
                                try:
                                    await agent.update_thread_metadata(thread_id, {"name": title})
                                    await websocket.send_json(
                                        {
                                            "type": "thread_title",
                                            "thread_id": thread_id,
                                            "title": title,
                                        }
                                    )
                                    logger.info(f"[Thread Title] {thread_id} → {title!r}")
                                except Exception as e:
                                    # Non-fatal — leave the default title
                                    # in place if the metadata update fails.
                                    logger.warning(f"Failed to set thread title: {e}")
                                    thread_title_set_ref["value"] = False
                except StopAsyncIteration:
                    pass

                if not stt_supports_streaming and not stop_event.is_set():
                    stt_session = await pipeline.open_stt_stream(sample_rate=sample_rate)
                    logger.debug("[Batch STT] Reopened session for next turn")
                else:
                    return
        except Exception as e:
            logger.error(f"transcript_collector error: {e}")
            stop_event.set()

    async def response_orchestrator() -> None:
        while not stop_event.is_set():
            try:
                text = await asyncio.wait_for(transcript_queue.get(), timeout=0.5)
            except asyncio.TimeoutError:
                continue
            except Exception:
                break

            if stop_event.is_set():
                return

            MAX_TRANSCRIPT_LENGTH = 5000
            if not text or len(text) > MAX_TRANSCRIPT_LENGTH:
                logger.warning(f"Transcript rejected: length {len(text)} (max {MAX_TRANSCRIPT_LENGTH})")
                continue

            is_responding_ref["value"] = True
            interrupt_event.clear()
            barge_in_candidate_ref["value"] = None
            turn_metrics.clear()
            turn_metrics["response_start_at"] = time.monotonic()

            buffer = ""
            full_response = ""
            first_sentence_emitted = False

            # Schedule a filler phrase. Fires after FILLER_DELAY_S if the
            # LLM hasn't produced a token yet — bridges the dead air during
            # slow first-token latency. Cancelled when first token arrives
            # OR when the turn ends (in finally). The filler shares the
            # sentence_queue with real LLM output, so it plays first (FIFO)
            # and the real response follows naturally after it finishes.
            async def _maybe_play_filler() -> None:
                try:
                    await asyncio.sleep(FILLER_DELAY_S)
                except asyncio.CancelledError:
                    return
                if "llm_first_token_at" in turn_metrics or interrupt_event.is_set():
                    return
                phrase = random.choice(_FILLER_PHRASES)
                logger.info(f"[Filler] LLM slow, queueing '{phrase}'")
                try:
                    await sentence_queue.put(phrase)
                except Exception:
                    pass

            filler_task = asyncio.create_task(_maybe_play_filler())

            try:
                voice_id = connection_voice_id_ref.get("value") or ""
                if not voice_id or voice_id == "default":
                    voice_id = pipeline.tts.default_voice or ""
                voice_obj = await pipeline.tts.get_voice(voice_id) if voice_id else None
                voice_name = voice_obj.name if voice_obj else None
                voice_description = voice_obj.description if voice_obj else None
                logger.info(f"[Voice→Agent] voice_id={voice_id} name={voice_name!r} desc={voice_description!r}")

                async for llm_event in agent.stream_events(
                    thread_id,
                    text,
                    mode="voice",
                    voice_name=voice_name,
                    voice_description=voice_description,
                ):
                    if interrupt_event.is_set() or stop_event.is_set():
                        break

                    etype = llm_event.get("type")
                    if etype == "token":
                        if "llm_first_token_at" not in turn_metrics:
                            turn_metrics["llm_first_token_at"] = time.monotonic()
                            first_token_ms = (
                                turn_metrics["llm_first_token_at"] - turn_metrics["response_start_at"]
                            ) * 1000
                            logger.info(f"[Latency] LLM first token: {first_token_ms:.0f}ms")
                            # Cancel pending filler so we don't queue "let me
                            # think" right before the actual answer. If the
                            # filler already fired (TTFT > FILLER_DELAY_S),
                            # it plays first and the real response follows.
                            filler_task.cancel()

                        buffer += llm_event["content"]
                        full_response += llm_event["content"]
                        await websocket.send_json(
                            {
                                "type": "text_stream",
                                "text": llm_event["content"],
                                "done": False,
                            }
                        )
                        sentences, buffer = _split_sentences(buffer)

                        # First-sentence early break: if no sentence yet but
                        # the buffer already has a comma after enough words,
                        # treat that comma as a chunk boundary so TTS starts
                        # 200-500ms sooner. Only applies to the very first
                        # chunk of a turn — subsequent sentences wait for
                        # proper end-of-sentence punctuation.
                        if not first_sentence_emitted and not sentences and len(buffer) >= 30 and "," in buffer:
                            comma_idx = buffer.find(",")
                            if comma_idx >= 20:
                                head = buffer[: comma_idx + 1].strip()
                                buffer = buffer[comma_idx + 1 :].lstrip()
                                if head:
                                    sentences = [head]

                        for sent in sentences:
                            if interrupt_event.is_set():
                                break
                            clean_sent = sanitize_for_tts(_strip_markdown(sent), aggressive=False)
                            if clean_sent:
                                await sentence_queue.put(clean_sent)
                                first_sentence_emitted = True
                    elif etype == "error":
                        logger.error(f"Agent error: {llm_event.get('message')}")
                        await websocket.send_json(
                            {
                                "type": "error",
                                "message": llm_event.get("message", "Agent error"),
                            }
                        )
                        break
                    elif etype == "done":
                        await websocket.send_json(
                            {
                                "type": "text_stream",
                                "text": "",
                                "done": True,
                            }
                        )

                if buffer.strip() and not interrupt_event.is_set():
                    clean_buffer = sanitize_for_tts(_strip_markdown(buffer.strip()), aggressive=False)
                    if clean_buffer:
                        await sentence_queue.put(clean_buffer)

            except asyncio.CancelledError:
                logger.info("response_orchestrator cancelled")
                raise
            except Exception as e:
                logger.error(f"response_orchestrator error: {e}")
                if buffer.strip():
                    clean_buffer = sanitize_for_tts(_strip_markdown(buffer.strip()), aggressive=False)
                    if clean_buffer:
                        await sentence_queue.put(clean_buffer)
            finally:
                # Defensive cancel: if filler hasn't fired yet (LLM was fast,
                # error occurred, or stream was cancelled), kill the task so
                # it doesn't queue a stale "hmm" into the next turn.
                filler_task.cancel()
                # Sentinel signals end-of-response to TTS consumer.
                await sentence_queue.put(None)
                if interrupt_event.is_set():
                    pipeline.on_interrupt()
                    try:
                        await websocket.send_json({"type": "interrupt"})
                    except Exception:
                        pass
                # NOTE: is_responding_ref is NOT flipped here. It stays True
                # until tts_streamer drains the queue (after processing the
                # None sentinel above). That keeps the barge-in window armed
                # through the entire audible response, not just the LLM-
                # streaming window — which previously created a dead zone
                # where TTS was still playing but interrupt was disabled.

    async def tts_streamer() -> None:
        audio_info_sent = False
        while not stop_event.is_set():
            try:
                sentence = await asyncio.wait_for(sentence_queue.get(), timeout=0.5)
            except asyncio.TimeoutError:
                continue
            except Exception:
                break

            if sentence is None:
                # End-of-response marker. By this point the tts_streamer has
                # processed every sentence queued by response_orchestrator
                # (FIFO order — None is queued LAST in the orchestrator's
                # finally block). Synthesize_stream calls were awaited inline,
                # so all audio bytes for this turn have already been sent on
                # the WS. Safe to mark the response as done.
                audio_info_sent = False
                is_responding_ref["value"] = False
                # Drop any stale barge-in candidate from the just-completed
                # response so it doesn't carry into the next turn.
                barge_in_candidate_ref["value"] = None
                continue

            if interrupt_event.is_set() or stop_event.is_set():
                continue

            try:
                voice_id = connection_voice_id_ref.get("value")
                speed = connection_speed_ref.get("value")
                language = connection_language_ref.get("value")
                audio_sent_for_sentence = False

                synth_kwargs: dict = {"voice": voice_id}
                if pipeline.tts.supports_speed and speed:
                    synth_kwargs["speed"] = float(speed)
                if pipeline.tts.supports_language and language:
                    synth_kwargs["lang"] = language

                client_gone = False
                async for chunk in pipeline.synthesize_stream(sentence, **synth_kwargs):
                    if interrupt_event.is_set() or stop_event.is_set() or client_gone:
                        break

                    if not audio_sent_for_sentence and chunk["type"] == "audio":
                        try:
                            await websocket.send_json({"type": "spoken_text", "text": sentence})
                        except (WebSocketDisconnect, RuntimeError) as e:
                            logger.info(f"[TTS] Client gone before spoken_text send: {e}")
                            client_gone = True
                            break
                        audio_sent_for_sentence = True

                    if chunk["type"] == "audio_info":
                        if not audio_info_sent:
                            try:
                                await websocket.send_json(
                                    {
                                        "type": "audio_info",
                                        "sample_rate": chunk["sample_rate"],
                                    }
                                )
                            except (WebSocketDisconnect, RuntimeError) as e:
                                logger.info(f"[TTS] Client gone during audio_info send: {e}")
                                client_gone = True
                                break
                            audio_info_sent = True
                    elif chunk["type"] == "audio":
                        if "tts_first_byte_at" not in turn_metrics:
                            turn_metrics["tts_first_byte_at"] = time.monotonic()
                            if "stt_final_at" in turn_metrics:
                                ttfb_ms = (turn_metrics["tts_first_byte_at"] - turn_metrics["stt_final_at"]) * 1000
                                logger.info(f"[Latency] TTFB (STT-final → TTS-first-byte): {ttfb_ms:.0f}ms")
                        try:
                            await websocket.send_bytes(chunk["audio"].tobytes())
                        except (WebSocketDisconnect, RuntimeError) as e:
                            # Client disconnected or WebSocket in bad state.
                            # Break cleanly so the generator's interrupt path
                            # (immediate AEC cleanup) runs instead of an
                            # exception propagating mid-stream.
                            logger.info(f"[TTS] send_bytes failed, stopping stream: {e}")
                            client_gone = True
                            break

                if not audio_sent_for_sentence:
                    logger.warning(f"TTS produced no audio for: {sentence[:40]}")

                if client_gone:
                    stop_event.set()

            except Exception as e:
                logger.error(f"tts_streamer error synthesizing '{sentence[:40]}': {e}")

    tasks = [
        asyncio.create_task(audio_receiver(), name="audio_receiver"),
        asyncio.create_task(transcript_collector(), name="transcript_collector"),
        asyncio.create_task(response_orchestrator(), name="response_orchestrator"),
        asyncio.create_task(tts_streamer(), name="tts_streamer"),
    ]

    try:
        await asyncio.gather(*tasks, return_exceptions=True)
    except WebSocketDisconnect:
        logger.info(f"Voice WebSocket disconnected (thread: {thread_id})")
    except Exception as e:
        logger.error(f"Voice WebSocket error: {e}")
        try:
            await websocket.close(code=1011, reason="Internal server error")
        except Exception:
            pass
    finally:
        stop_event.set()
        for t in tasks:
            if not t.done():
                t.cancel()
        try:
            await stt_session.close()
        except Exception:
            pass
        pipeline.on_interrupt()
        # Per-connection pipeline shares STT/TTS with the singleton (loaded
        # once at app startup, ~30s for Whisper). Calling pipeline.shutdown()
        # here would unload the SHARED models and force the next connection
        # to wait 30+s for them to reload — that was the cause of the
        # "signal aborted" timeouts in the frontend. Only the VAD is
        # per-connection state; it's released by garbage collection when the
        # `pipeline` reference goes out of scope at the end of this handler.
        try:
            await agent.delete_thread(thread_id)
        except Exception:
            pass
        async with _connections_lock:
            _active_connections -= 1
        logger.info("Voice WebSocket cleanup complete")


async def startup_voice_services() -> None:
    """Initialize voice services on startup."""
    pipeline = get_voice_pipeline()
    await pipeline.initialize()
    logger.info("Voice pipeline ready")

    agent = get_agent_client()
    await agent.start()
    logger.info("Agent client ready")


@router.get(
    "/status",
    response_model=VoiceStatusResponse,
    dependencies=[Depends(verify_api_key), Depends(check_rate_limit)],
)
async def get_status() -> VoiceStatusResponse:
    """Get voice agent status."""
    try:
        pipeline = get_voice_pipeline()
        agent = get_agent_client()
        stt_ready = pipeline.is_initialized
        tts_ready = pipeline.is_initialized
        llm_ready = agent.is_ready
    except RuntimeError:
        stt_ready = tts_ready = llm_ready = False

    return VoiceStatusResponse(
        status=_status,
        is_connected=_active_connections > 0,
        active_connections=_active_connections,
        stt_ready=stt_ready,
        tts_ready=tts_ready,
        llm_ready=llm_ready,
        config=_config,
    )


@router.get("/config", dependencies=[Depends(verify_api_key), Depends(check_rate_limit)])
async def get_config():
    """Get voice configuration including TTS capabilities."""
    pipeline = get_voice_pipeline()
    if not pipeline.is_initialized:
        await pipeline.initialize()

    return {
        "voice_id": _config.voice_id,
        "language": _config.language,
        "speed": _config.speed,
        "stt_model": _config.stt_model,
        "supports_cloning": pipeline.supports_voice_cloning,
        "supports_speed": pipeline.tts.supports_speed,
        "supports_language": pipeline.tts.supports_language,
    }


@router.put("/config", response_model=VoiceConfig, dependencies=[Depends(verify_api_key), Depends(check_rate_limit)])
async def update_config(update: VoiceConfigUpdate) -> VoiceConfig:
    """Update voice configuration."""
    global _config
    if update.voice_id is not None:
        _config.voice_id = update.voice_id
    if update.language is not None:
        _config.language = update.language
    if update.speed is not None:
        _config.speed = update.speed
    logger.info(f"Voice config updated: {_config}")
    return _config


@router.get("/voices", response_model=VoicesResponse, dependencies=[Depends(verify_api_key), Depends(check_rate_limit)])
async def get_voices() -> VoicesResponse:
    """Get available TTS voices — catalog + cloned voices in one list.

    Originally this endpoint returned ONLY the catalog. Cloned voices
    were exposed separately via /voice/clones. The frontend expects a
    single voice picker, so we merge them here. Cloned entries are
    tagged with `["Cloned"]` so the UI can badge them.
    """
    pipeline = get_voice_pipeline()
    if not pipeline.is_initialized:
        await pipeline.initialize()

    tts_voices = await pipeline.tts.get_voices()
    voices = [
        VoiceInfo(
            id=v.id,
            name=v.name,
            language=v.language,
            gender=v.gender,
            description=v.description,
            style=v.metadata.get("style") if v.metadata else None,
            tags=v.metadata.get("tags") if v.metadata else None,
            preview_text=v.metadata.get("preview_text") if v.metadata else None,
        )
        for v in tts_voices
    ]

    # Append cloned voices for providers that support cloning. We render
    # them at the END so the catalog ordering doesn't shift as users
    # add/remove clones.
    if _supports_cloning(pipeline.tts):
        try:
            cloned = await pipeline.tts.get_cloned_voices()
            voices.extend(
                VoiceInfo(
                    id=v.id,
                    name=v.name,
                    language=v.language,
                    gender=v.gender,
                    description=v.description,
                    style=v.metadata.get("style") if v.metadata else None,
                    tags=["Cloned"],
                    preview_text=v.metadata.get("preview_text") if v.metadata else None,
                )
                for v in cloned
            )
        except Exception as e:
            logger.warning(f"Failed to load cloned voices: {e}")

    voice_ids = {v.id for v in voices}
    default_voice = _config.voice_id if _config.voice_id in voice_ids else (voices[0].id if voices else "")
    return VoicesResponse(voices=voices, default_voice=default_voice)


@router.get(
    "/languages",
    response_model=LanguagesResponse,
    dependencies=[Depends(verify_api_key), Depends(check_rate_limit)],
)
async def get_languages() -> LanguagesResponse:
    """Get supported TTS languages."""
    pipeline = get_voice_pipeline()
    if not pipeline.is_initialized:
        await pipeline.initialize()

    tts_languages = await pipeline.tts.get_languages()
    languages = []
    for lang in tts_languages:
        if isinstance(lang, dict):
            languages.append(
                LanguageInfo(
                    code=lang.get("code", ""), name=lang.get("name", ""), native_name=lang.get("native_name", "")
                )
            )
        else:
            languages.append(LanguageInfo(code=lang.code, name=lang.name, native_name=getattr(lang, "native_name", "")))
    return LanguagesResponse(languages=languages, default_language="auto")


@router.post("/interrupt", dependencies=[Depends(verify_api_key), Depends(check_rate_limit)])
async def interrupt() -> dict:
    """Interrupt current response."""
    global _status
    pipeline = get_voice_pipeline()
    pipeline.on_interrupt()
    _status = AgentStatus.LISTENING
    logger.info("Interrupt requested")
    return {"status": "interrupted", "aec_state": pipeline.get_aec_state()}


@router.post(
    "/transcribe",
    response_model=TranscriptionResponse,
    dependencies=[Depends(verify_api_key), Depends(check_rate_limit)],
)
async def transcribe_audio(
    file: UploadFile = File(..., description="Audio file"),
    language: str = Form(default=None, description="Language hint"),
) -> TranscriptionResponse:
    """Transcribe audio to text."""
    pipeline = get_voice_pipeline()
    if not pipeline.is_initialized:
        await pipeline.initialize()

    MAX_UPLOAD_BYTES = 50 * 1024 * 1024
    read_chunks = []
    total_size = 0
    while True:
        chunk = await file.read(8192)
        if not chunk:
            break
        total_size += len(chunk)
        if total_size > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="File too large (max 50MB)")
        read_chunks.append(chunk)
    audio_bytes = b"".join(read_chunks)

    try:
        _validate_audio_magic_bytes(audio_bytes)
        audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes))
        duration_seconds = len(audio_segment) / 1000.0
        logger.info(f"Audio duration: {duration_seconds:.2f}s")

        if duration_seconds > settings.AUDIO_CHUNK_THRESHOLD:
            chunker = AudioChunker(
                chunk_duration_ms=settings.AUDIO_FILE_CHUNK_DURATION_MS,
                min_silence_len=settings.AUDIO_MIN_SILENCE_MS,
                silence_thresh=settings.AUDIO_SILENCE_THRESH_DB,
            )
            chunks = chunker.chunk_by_duration(audio_segment)
            logger.info(f"Split into {len(chunks)} chunks")

            transcriptions = []
            for chunk in chunks:
                chunk_wav = io.BytesIO()
                chunk.export(chunk_wav, format="wav")
                audio_int16, sr = _read_wav_data(chunk_wav)
                audio_float = audio_int16.astype(np.float32) / 32768.0
                result = await pipeline.stt.transcribe(audio_float, sample_rate=sr, language=language)
                transcriptions.append(result.text)

            full_text = " ".join(transcriptions)
        else:
            wav_buffer = io.BytesIO()
            audio_segment.export(wav_buffer, format="wav")
            audio_int16, sr = _read_wav_data(wav_buffer)
            audio_float = audio_int16.astype(np.float32) / 32768.0
            result = await pipeline.stt.transcribe(audio_float, sample_rate=sr, language=language)
            full_text = result.text

        logger.info(f"Transcribed: '{full_text[:100]}'...")
        return TranscriptionResponse(text=full_text, language=language or "auto", duration_seconds=duration_seconds)

    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise


@router.post("/narrate", dependencies=[Depends(verify_api_key), Depends(check_rate_limit)])
async def narrate_text(
    request: NarrationRequest,
    user_id: UUID = Depends(get_current_user_id),
) -> JSONResponse:
    """Convert text to speech and save to disk."""
    MAX_TEXT_LENGTH = 10000
    if len(request.text) > MAX_TEXT_LENGTH:
        raise HTTPException(status_code=400, detail=f"Text too long (max {MAX_TEXT_LENGTH} characters)")

    clean_text = sanitize_for_tts(request.text, aggressive=False)
    if not clean_text:
        raise HTTPException(status_code=400, detail="Text contains only unspeakable characters")

    pipeline = get_voice_pipeline()
    if not pipeline.is_initialized:
        await pipeline.initialize()

    try:
        voice_id = request.voice_id or _config.voice_id

        if voice_id == "default":
            voices = await pipeline.tts.get_voices()
            if voices:
                voice_id = voices[0].id
            else:
                if settings.TTS_PROVIDER == "pocket_tts":
                    voice_id = "alba"
                else:
                    voice_id = "af_heart"

        if request.language and request.language != "auto":
            lang = request.language
        else:
            voice = await pipeline.tts.get_voice(voice_id)
            lang = voice.language if voice else "en-us"

        logger.info(f"Narrate: voice={voice_id}, lang={lang}, len={len(clean_text)} (orig {len(request.text)})")

        if len(clean_text) > settings.TEXT_CHUNK_THRESHOLD:
            # Strip markdown before chunking to avoid bad splits at headers
            # (e.g., "### 2" shouldn't be a separate chunk)
            text_for_chunking = _strip_markdown(clean_text)
            chunker = TextChunker(max_chunk_size=settings.TEXT_MAX_CHUNK_SIZE)
            chunks = chunker.chunk_by_sentences(text_for_chunking)

            logger.info(f"Chunked text into {len(chunks)} segments:")
            for i, chunk in enumerate(chunks):
                logger.info(f"  Chunk {i + 1}: {len(chunk)} chars: {chunk[:80]}{'...' if len(chunk) > 80 else ''}")

            audio_segments = []
            total_duration = 0.0

            for idx, chunk_text in enumerate(chunks):
                logger.debug(f"Synthesizing chunk {idx + 1}/{len(chunks)}: {chunk_text[:60]}...")
                tts_result = await pipeline.tts.synthesize(
                    chunk_text, voice=voice_id, speed=request.speed or _config.speed, lang=lang
                )
                total_duration += tts_result.duration
                faded = _apply_fade(tts_result.audio, tts_result.sample_rate, fade_ms=15)
                audio_int16 = (faded * 32767).astype(np.int16)
                wav_buffer = _create_wav_buffer(audio_int16, tts_result.sample_rate)
                audio_segments.append(AudioSegment.from_wav(wav_buffer))

            if not audio_segments:
                raise HTTPException(status_code=422, detail="TTS produced no audio output")

            final_audio = audio_segments[0]
            for segment in audio_segments[1:]:
                final_audio = final_audio.append(segment, crossfade=20)

            wav_buffer = io.BytesIO()
            final_audio.export(wav_buffer, format="wav")
            wav_buffer.seek(0)
            result_duration = total_duration
            result_sample_rate = tts_result.sample_rate

        else:
            tts_result = await pipeline.tts.synthesize(
                clean_text, voice=voice_id, speed=request.speed or _config.speed, lang=lang
            )
            faded = _apply_fade(tts_result.audio, tts_result.sample_rate, fade_ms=15)
            audio_int16 = (faded * 32767).astype(np.int16)
            wav_buffer = _create_wav_buffer(audio_int16, tts_result.sample_rate)
            result_duration = tts_result.duration
            result_sample_rate = tts_result.sample_rate

        logger.info(f"Narrated -> {result_duration:.2f}s audio")

        voice_obj = await pipeline.tts.get_voice(voice_id)
        voice_name = voice_obj.name if voice_obj else voice_id

        meta = save_audio_file(
            wav_buffer=wav_buffer,
            file_type="narration",
            user_id=str(user_id),
            duration=result_duration,
            sample_rate=result_sample_rate,
            prompt=request.text[:200],
            voice_name=voice_name,
        )
        return JSONResponse(content=meta)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Narration error: {e}")
        raise


@router.get("/narrations")
async def list_narrations(user_id: UUID = Depends(get_current_user_id)):
    """List all narrations saved by the current user."""
    return list_files("narration", str(user_id))


@router.delete("/narrations/{file_id}")
async def delete_narration(file_id: str, user_id: UUID = Depends(get_current_user_id)):
    """Delete a narration."""
    ok = delete_file("narration", file_id, str(user_id))
    if not ok:
        raise HTTPException(status_code=404, detail="File not found or permission denied")
    return {"deleted": file_id}


@router.post(
    "/clone",
    response_model=VoiceCloneResponse,
    dependencies=[Depends(verify_api_key), Depends(check_rate_limit)],
)
async def clone_voice(
    file: UploadFile = File(..., description="Reference audio file"),
    name: str = Form(..., description="Name for the cloned voice"),
    ref_text: Optional[str] = Form(default=None, description="Transcript of reference audio"),
    language: str = Form(default="auto", description="Language code"),
    description: Optional[str] = Form(default=None, description="Description"),
) -> VoiceCloneResponse:
    """Clone a voice from reference audio."""
    pipeline = get_voice_pipeline()
    if not pipeline.is_initialized:
        await pipeline.initialize()

    if not _supports_cloning(pipeline.tts):
        raise HTTPException(status_code=400, detail="Voice cloning requires Pocket TTS (set TTS_PROVIDER=pocket_tts)")

    MAX_CLONE_BYTES = 20 * 1024 * 1024
    clone_chunks = []
    total_size = 0
    while True:
        chunk = await file.read(8192)
        if not chunk:
            break
        total_size += len(chunk)
        if total_size > MAX_CLONE_BYTES:
            raise HTTPException(status_code=413, detail="File too large (max 20MB)")
        clone_chunks.append(chunk)
    audio_bytes = b"".join(clone_chunks)

    try:
        _validate_audio_magic_bytes(audio_bytes)
        audio_segment = AudioSegment.from_file(io.BytesIO(audio_bytes))
        duration_seconds = len(audio_segment) / 1000.0

        if duration_seconds < 1:
            raise HTTPException(status_code=400, detail="Audio too short (min 1s)")
        if duration_seconds > 120:
            raise HTTPException(status_code=400, detail="Audio too long (max 2min)")

        safe_name = re.sub(r"[^a-zA-Z0-9_\-]", "_", name)[:64]
        if not safe_name:
            safe_name = "unnamed"

        audio_mono = audio_segment.set_channels(1)
        temp_dir = os.path.join(tempfile.gettempdir(), "voiceagent_clone")
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, f"clone_ref_{safe_name}.wav")
        audio_mono.export(temp_path, format="wav")

        logger.info(f"Cloning: {temp_path}, {duration_seconds:.2f}s")

        try:
            cloned_voice = await pipeline.tts.clone_voice(
                audio_path=temp_path, name=name, language=language, description=description
            )
        finally:
            try:
                os.remove(temp_path)
            except OSError:
                pass

        logger.info(f"Voice cloned: {cloned_voice.id}")
        return VoiceCloneResponse(
            id=cloned_voice.id,
            name=cloned_voice.name,
            language=cloned_voice.language,
            description=cloned_voice.description,
            is_cloned=True,
            message=f"Voice '{name}' cloned from {duration_seconds:.1f}s audio",
        )

    except HTTPException:
        raise
    except Exception as e:
        msg = str(e)
        logger.error(f"Clone error: {msg}")
        # Pocket TTS / Kyutai cloning weights are gated on HuggingFace.
        # If the server is missing HF_TOKEN or hasn't accepted the model
        # terms, the upstream lib raises a long descriptive error. Surface
        # a concise, actionable 503 to the client instead of a raw 500.
        if "voice cloning" in msg.lower() and "weights" in msg.lower():
            raise HTTPException(
                status_code=503,
                detail=(
                    "Voice cloning is unavailable: server missing HuggingFace "
                    "credentials for kyutai/pocket-tts. Set HF_TOKEN in backend/.env "
                    "and accept the model terms at https://huggingface.co/kyutai/pocket-tts."
                ),
            )
        raise HTTPException(status_code=500, detail="Voice cloning failed")


@router.get(
    "/clones",
    response_model=ClonedVoicesResponse,
    dependencies=[Depends(verify_api_key), Depends(check_rate_limit)],
)
async def get_cloned_voices() -> ClonedVoicesResponse:
    """Get all cloned voices."""
    pipeline = get_voice_pipeline()
    if not pipeline.is_initialized:
        await pipeline.initialize()

    if not _supports_cloning(pipeline.tts):
        raise HTTPException(status_code=400, detail="Voice cloning requires Pocket TTS (set TTS_PROVIDER=pocket_tts)")

    cloned = await pipeline.tts.get_cloned_voices()
    voices = [
        VoiceInfo(
            id=v.id,
            name=v.name,
            language=v.language,
            gender=v.gender,
            description=v.description,
            style=v.metadata.get("style") if v.metadata else None,
            tags=["Cloned"],
            preview_text=v.metadata.get("preview_text") if v.metadata else None,
        )
        for v in cloned
    ]
    return ClonedVoicesResponse(voices=voices, count=len(voices))


@router.delete("/clones/{clone_id}", dependencies=[Depends(verify_api_key), Depends(check_rate_limit)])
async def delete_cloned_voice(clone_id: str) -> dict:
    """Delete a cloned voice."""
    if not re.match(r"^clone_[a-f0-9]{8}$", clone_id):
        raise HTTPException(status_code=400, detail="Invalid clone ID format")

    pipeline = get_voice_pipeline()
    if not pipeline.is_initialized:
        await pipeline.initialize()

    if not _supports_cloning(pipeline.tts):
        raise HTTPException(status_code=400, detail="Voice cloning requires Pocket TTS (set TTS_PROVIDER=pocket_tts)")

    deleted = await pipeline.tts.delete_cloned_voice(clone_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Cloned voice not found: {clone_id}")

    logger.info(f"Deleted clone: {clone_id}")
    return {"status": "deleted", "clone_id": clone_id}
