"""Run the real pinned Conversation App handler; capture one reproducible turn."""
import asyncio
import contextlib
import hashlib
import json
import time
import wave
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import numpy as np

REVISION = "b9f58a3587d79a3275d4402d1a8d210649d62d50"
INSTRUCTIONS = (
    "You are Reachy, a curious and friendly science explainer. Answer the user's question "
    "accurately in three short sentences, at most 55 words. Do not greet, ask a follow-up, "
    "or mention tools. Express interest without claiming feelings or consciousness."
)


class ConversationSignals:
    """Receive the upstream handler's listening/speaking lifecycle without a second motor writer."""
    def __init__(self):
        self.listening = False
        self.speaking = False

    def set_listening(self, value):
        self.listening = value

    def set_speaking(self, value):
        self.speaking = value

    def is_idle(self):
        return not (self.listening or self.speaking)


class ObservedConnection:
    """Record only response evidence, excluding session URLs, credentials and microphone PCM."""
    def __init__(self, connection, evidence):
        self.connection, self.evidence = connection, evidence

    def __getattr__(self, name):
        return getattr(self.connection, name)

    async def __aiter__(self):
        async for event in self.connection:
            record = {"type": event.type, "received_monotonic_s": time.perf_counter()}
            if event.type == "response.done":
                record["response"] = {"id": event.response.id, "status": event.response.status}
            elif event.type in {"response.output_audio_transcript.done", "conversation.item.input_audio_transcription.completed"}:
                record["transcript"] = event.transcript
            elif event.type == "error":
                record["error"] = {"code": getattr(event.error, "code", "unknown")}
            self.evidence.append(record)
            yield event


class ObservedRealtime:
    def __init__(self, realtime, evidence):
        self.realtime, self.evidence = realtime, evidence

    @contextlib.asynccontextmanager
    async def connect(self, **kwargs):
        async with self.realtime.connect(**kwargs) as connection:
            yield ObservedConnection(connection, self.evidence)


def make_handler(robot, evidence):
    # Importing the installed app executes its actual session, audio-input, transcript,
    # response-queue and audio-decoding implementation. No substitute LLM client here.
    from reachy_mini_conversation_app.huggingface_realtime import HuggingFaceRealtimeHandler
    from reachy_mini_conversation_app.tools.core_tools import ToolDependencies

    class StudyHandler(HuggingFaceRealtimeHandler):
        async def _build_realtime_client(self):
            client = await super()._build_realtime_client()
            self.raw_client = client
            return SimpleNamespace(realtime=ObservedRealtime(client.realtime, evidence))

        def _get_session_config(self, tool_specs):
            settings = super()._get_session_config([])
            settings["instructions"] = INSTRUCTIONS
            settings["tools"] = []
            settings.pop("tool_choice", None)
            settings["audio"]["input"]["turn_detection"] = None
            return settings

        async def _send_startup_greeting_prompt(self):
            # One requested turn, with no greeting contaminating the captured answer.
            self._startup_greeting_sent = True

    return StudyHandler(ToolDependencies(reachy_mini=robot, movement_manager=ConversationSignals(), camera_enabled=False))


async def capture_turn(robot, control, destination, *, text=None, input_device=None, input_wav=None, seconds=6,
                       on_phase=lambda phase: None, timeout=90):
    """Capture a genuine text- or microphone-initiated backend answer, never silently fall back."""
    destination = Path(destination)
    if destination.exists():
        raise ValueError("Capture directory already exists; preserve it and choose a new name")
    if text is None and input_device is None and input_wav is None:
        raise ValueError("Microphone capture requires an explicit --input-device number")
    if not 1 <= seconds <= 30:
        raise ValueError("Microphone recording must be 1-30 seconds")
    evidence, audio, transcripts = [], [], {}
    handler = make_handler(robot, evidence)
    handler.set_transcript_observer(lambda role, content, final: transcripts.update({role: content}) if final else None)
    task = asyncio.create_task(handler.start_up())
    started = time.perf_counter()
    destination.mkdir(parents=True)
    status = "failed"
    failure = None
    try:
        on_phase("connecting")
        while not handler._connected_event.is_set():
            if control.stop.is_set():
                raise InterruptedError("Stopped during backend connection")
            if task.done():
                await task
                raise RuntimeError("Backend closed before connection")
            if time.perf_counter()-started > 25:
                raise TimeoutError("Conversation backend connection timed out")
            await asyncio.sleep(.02)
        if text is not None:
            on_phase("text_submitted")
            await handler.connection.conversation.item.create(item={"type": "message", "role": "user",
                "content": [{"type": "input_text", "text": text}]})
        elif input_wav is not None:
            on_phase("audio_submitted")
            with wave.open(str(input_wav), "rb") as wav:
                if (wav.getnchannels(),wav.getsampwidth(),wav.getframerate()) != (1,2,16000):
                    raise ValueError("Input WAV must be mono PCM16 at 16000 Hz")
                if not 1 <= wav.getnframes()/16000 <= 30:
                    raise ValueError("Input WAV must contain 1-30 seconds")
                pcm = np.frombuffer(wav.readframes(wav.getnframes()),dtype="<i2")
            for start in range(0,len(pcm),1600):
                if control.stop.is_set():
                    raise InterruptedError("Stopped audio upload")
                await handler.receive((16000,pcm[start:start+1600]))
            await handler.connection.input_audio_buffer.commit()
        else:
            import sounddevice as sd
            on_phase("listening")
            print(f"Recording device {input_device} for {seconds}s. Speak now. Audio goes to the configured HF backend.", flush=True)
            with sd.InputStream(device=input_device, samplerate=handler.SAMPLE_RATE,
                                channels=1, dtype="int16", blocksize=1600) as microphone:
                for _ in range(round(seconds*10)):
                    if control.stop.is_set():
                        raise InterruptedError("Stopped microphone capture")
                    samples, overflow = await asyncio.to_thread(microphone.read, 1600)
                    if overflow:
                        raise RuntimeError("Microphone overflow; capture rejected")
                    await handler.receive((handler.SAMPLE_RATE, samples))
            await handler.connection.input_audio_buffer.commit()
        on_phase("thinking")
        # The HF backend commits audio asynchronously. Requesting a response before
        # its final transcript arrives can make the LLM answer an empty conversation.
        while text is None and not transcripts.get("user"):
            if control.stop.is_set():
                raise InterruptedError("Stopped during speech recognition")
            if task.done():
                await task
                raise RuntimeError("Backend closed during speech recognition")
            if time.perf_counter()-started > timeout:
                raise TimeoutError("Speech recognition did not complete")
            if any(e["type"]=="error" for e in evidence):
                raise RuntimeError("Backend reported an error during speech recognition")
            await asyncio.sleep(.02)
        await handler._safe_response_create()
        while True:
            if control.stop.is_set():
                raise InterruptedError("Stopped backend generation")
            if time.perf_counter()-started > timeout:
                raise TimeoutError("No completed backend response before timeout")
            if task.done():
                await task
                raise RuntimeError("Backend closed before completed response")
            output = await handler.emit()
            if isinstance(output, tuple):
                rate, chunk = output
                if rate != 16000:
                    raise ValueError("Unexpected upstream PCM rate")
                audio.append(np.asarray(chunk, dtype=np.int16).reshape(-1))
            errors = [e for e in evidence if e["type"] == "error"]
            if errors:
                raise RuntimeError("Backend reported error: " + str(errors[-1]["error"]["code"]))
            done = [e for e in evidence if e["type"] == "response.done"]
            if done and handler.output_queue.empty():
                if len(done) != 1 or done[0]["response"]["status"] != "completed":
                    raise RuntimeError("Backend response was incomplete or more than one turn")
                break
        if not audio or not transcripts.get("assistant"):
            raise RuntimeError("Completed response missing audio or transcript")
        if text is None and not transcripts.get("user"):
            raise RuntimeError("Microphone response missing recognized user question")
        pcm = np.concatenate(audio)
        if control.stop.is_set():
            raise InterruptedError("Stopped before capture persistence")
        if len(pcm) < 8000 or not np.any(pcm):
            raise ValueError("Backend returned empty or implausibly short speech")
        with wave.open(str(destination/"answer.wav"), "wb") as wav:
            wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(16000)
            wav.writeframes(pcm.astype("<i2").tobytes())
        receipt = {"source": "actual Conversation App HuggingFaceRealtimeHandler",
            "event_log_format": "metadata-only; PCM audio is stored once in answer.wav",
            "revision": REVISION, "input_mode": "text" if text is not None else ("wav-upload" if input_wav else "microphone"),
            "question": text if text is not None else transcripts["user"],
            "answer": transcripts["assistant"], "duration_s": len(pcm)/16000,
            "voice": handler.get_current_voice(), "sample_rate":16000,
            "sha256": hashlib.sha256((destination/"answer.wav").read_bytes()).hexdigest(),
            "response": done[0]["response"], "choreography_reviewed": False,
            "captured_at_utc":datetime.now(timezone.utc).isoformat(),
            "instructions_sha256":hashlib.sha256(INSTRUCTIONS.encode()).hexdigest(),
            "network_capture_elapsed_s": time.perf_counter()-started}
        (destination/"capture.json").write_text(json.dumps(receipt, indent=2)+"\n", encoding="utf-8")
        status = "completed"
        on_phase("captured")
        return receipt
    except (InterruptedError, asyncio.CancelledError):
        status = "interrupted"
        raise
    except Exception as exc:
        failure = {"type":type(exc).__name__}
        response = getattr(exc,"response",None)
        if response is not None:
            failure["http_status"] = response.status_code
            failure["retry_after"] = response.headers.get("retry-after")
        if failure.get("http_status") == 429:
            raise RuntimeError("Conversation backend rate-limited this session (HTTP 429). Use offline A/B trials and retry live later; no canned answer was substituted.") from None
        raise
    finally:
        (destination/"events.jsonl").write_text("".join(json.dumps(e)+"\n" for e in evidence), encoding="utf-8")
        (destination/"status.json").write_text(json.dumps({"status":status,"elapsed_s":time.perf_counter()-started,"failure":failure}))
        await handler.shutdown()
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await task
        if hasattr(handler, "raw_client"):
            await handler.raw_client.close()
