import asyncio
import json
import threading
import wave
from types import SimpleNamespace

import numpy as np
import pytest

from reachy_lab2 import conversation


def test_event_log_keeps_metadata_without_duplicating_audio():
    events = [SimpleNamespace(type="response.output_audio.delta", delta="PCM already stored in WAV"),
              SimpleNamespace(type="response.done", response=SimpleNamespace(id="fixture", status="completed"))]
    class Connection:
        async def __aiter__(self):
            for event in events:
                yield event
    evidence = []
    async def consume():
        return [event async for event in conversation.ObservedConnection(Connection(), evidence)]
    assert asyncio.run(consume()) == events
    assert "delta" not in evidence[0]
    assert evidence[-1]["response"] == {"id":"fixture", "status":"completed"}


def test_audio_response_waits_for_final_transcript_and_captures_real_handler_outputs(tmp_path, monkeypatch):
    """A delayed ASR result must be in context before response.create is requested."""
    class Handler:
        SAMPLE_RATE=16000
        def __init__(self,evidence):
            self.evidence=evidence
            self._connected_event=asyncio.Event()
            self.closed=asyncio.Event()
            self.output_queue=asyncio.Queue()
            self.recognized=False
            self.received=0
            self.connection=SimpleNamespace(input_audio_buffer=SimpleNamespace(commit=self.commit))
        def set_transcript_observer(self,observer):
            self.observer=observer
        async def start_up(self):
            self._connected_event.set()
            await self.closed.wait()
        async def receive(self,frame):
            self.received += frame[1].size
        async def commit(self):
            async def transcribe():
                await asyncio.sleep(.06)
                self.recognized=True
                self.observer("user","Synthetic test question",True)
            self.transcriber=asyncio.create_task(transcribe())
        async def _safe_response_create(self):
            assert self.recognized, "LLM request preceded ASR completion"
            assert self.received==16000
            self.observer("assistant","Synthetic test answer",True)
            self.output_queue.put_nowait((16000,np.ones(16000,dtype=np.int16)))
            self.evidence.append({"type":"response.done","response":{"id":"fixture-only","status":"completed"}})
        async def emit(self):
            return await self.output_queue.get()
        async def shutdown(self):
            self.closed.set()
        def get_current_voice(self):
            return "fixture-only"
    monkeypatch.setattr(conversation,"make_handler",lambda robot,evidence:Handler(evidence))
    wav_path=tmp_path/"question.wav"
    with wave.open(str(wav_path),"wb") as wav:
        wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(16000)
        wav.writeframes(np.ones(16000,dtype="<i2").tobytes())
    receipt=asyncio.run(conversation.capture_turn(None,SimpleNamespace(stop=threading.Event()),
        tmp_path/"capture",input_wav=wav_path,timeout=2))
    assert receipt["question"]=="Synthetic test question"
    assert receipt["input_mode"]=="wav-upload"
    assert json.loads((tmp_path/"capture/status.json").read_text())["status"]=="completed"


def test_capture_requires_explicit_microphone_and_preserves_existing_directory(tmp_path):
    control=SimpleNamespace(stop=threading.Event())
    with pytest.raises(ValueError,match="explicit"):
        asyncio.run(conversation.capture_turn(None,control,tmp_path/"new"))
    with pytest.raises(ValueError,match="already exists"):
        asyncio.run(conversation.capture_turn(None,control,tmp_path,text="question"))


def test_backend_failure_has_no_canned_fallback(tmp_path,monkeypatch):
    class FailedHandler:
        def __init__(self): self._connected_event=asyncio.Event()
        def set_transcript_observer(self,observer): pass
        async def start_up(self): raise ConnectionError("fixture unavailable")
        async def shutdown(self): pass
    monkeypatch.setattr(conversation,"make_handler",lambda *args:FailedHandler())
    with pytest.raises(ConnectionError):
        asyncio.run(conversation.capture_turn(None,SimpleNamespace(stop=threading.Event()),tmp_path/"failed",text="question"))
    assert not (tmp_path/"failed/answer.wav").exists()
    assert json.loads((tmp_path/"failed/status.json").read_text())["status"]=="failed"
