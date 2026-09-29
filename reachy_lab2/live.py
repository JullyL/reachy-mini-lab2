"""One live conversational turn with emotional motion, separate from controlled study replay."""
import asyncio
import contextlib
import json
import re
import time
from pathlib import Path

from .audio import AudioOutput
from .choreography import EmotionLibrary, frame, HZ, ROOT, speech_performance
from .conversation import capture_turn
from .conversation_audio import read_wav
from .prosody import align_audio, align_beats, TIMING_BASIS
from .trial import TrialLog


def draft_beats(answer):
    """Suggest sentence-level emotion choices; new answers require listening review before study use."""
    phrases = [s.strip() for s in re.split(r"(?<=[.!?;])\s+", answer) if s.strip()]
    beats = []
    for i, phrase in enumerate(phrases):
        lower = phrase.lower()
        state = "explaining"
        if any(word in lower for word in ("different", "changes", "orbit", "bends")):
            state = "curious"
        if any(word in lower for word in ("faster", "surpris", "instantly")):
            state = "surprised"
        if i == len(phrases)-1:
            state = "affirming"
        beats.append({"state":state, "phrase":phrase})
    return beats


async def live_turn(robot, control, destination, *, text=None, input_device=None, input_wav=None, seconds=6,
                    expressive=True, capture_only=False):
    """Use actual microphone/text and backend output with one exclusive motor scheduler."""
    destination = Path(destination)
    library = EmotionLibrary()
    log = TrialLog(destination.parent/"live-logs", {"mode":"live-demo", "technically_valid":False,
                  "input_mode":"text" if text is not None else ("wav-upload" if input_wav else "microphone"), "expressive_motion":int(expressive)})
    phase, phase_start = "connecting", time.perf_counter()
    def change_phase(value):
        nonlocal phase, phase_start
        phase, phase_start = value, time.perf_counter()
        log.event("CONVERSATION_PHASE", phase=value)
    initial = robot.neutral(control.stop)
    if not initial["succeeded"]:
        log.close()
        raise RuntimeError("Initial neutral not confirmed")
    task = asyncio.create_task(capture_turn(robot.mini, control, destination, text=text,
                    input_device=input_device, input_wav=input_wav, seconds=seconds, on_phase=change_phase))
    output = None
    status = "failed"
    clips = {name: library.clip(name, 3.0) for name in ("attentive", "curious", "thinking")}
    try:
        while not task.done():
            if control.stop.is_set():
                raise InterruptedError("Operator stop")
            elapsed = time.perf_counter()-phase_start
            if expressive and phase in {"listening", "thinking"}:
                state = "attentive" if phase == "listening" else ("curious" if int(elapsed/3)%2 == 0 else "thinking")
                robot.send(frame(clips[state][int(elapsed*HZ) % (len(clips[state])-1)]))
            await asyncio.sleep(1/HZ)
        receipt = await task
        recovery = robot.neutral()
        if not recovery["succeeded"]:
            raise RuntimeError("Failed to settle before captured-answer playback")
        if not capture_only:
            beats = draft_beats(receipt["answer"])
            duration = receipt["duration_s"]
            alignment = await asyncio.to_thread(align_audio, destination/"answer.wav", receipt["answer"])
            if control.stop.is_set():
                raise InterruptedError("Operator stop during speech alignment")
            (destination/"alignment.json").write_text(json.dumps(alignment,indent=2)+"\n")
            beats = align_beats(beats,alignment)
            (destination/"draft_choreography.json").write_text(json.dumps({"reviewed":False,
                "timing_basis":TIMING_BASIS, "beats":beats},indent=2)+"\n")
            settings = json.loads((ROOT/"config/choreography.json").read_text()).get("speech_motion",{})
            values = speech_performance(library,beats,duration,settings,alignment)
            rate, samples = read_wav(destination/"answer.wav")
            output = AudioOutput(rate, samples)
            output.open()
            start = time.perf_counter()+.2
            output.arm(start)
            log.event("LIVE_RESPONSE_READY", answer=receipt["answer"], answer_sha256=receipt["sha256"],
                      choreography_basis=TIMING_BASIS)
            end = None
            next_frame, beat_index = 0, 0
            while end is None or time.perf_counter()<end:
                if control.stop.is_set():
                    raise InterruptedError("Operator stop during speech")
                now = time.perf_counter()
                while not output.events.empty():
                    marker, at, info = output.events.get()
                    log.event(marker, at=at, **info)
                    if marker == "AUDIO_ERROR":
                        raise RuntimeError("Live playback audio error")
                    if marker == "SPEECH_END":
                        end = at
                elapsed = now-start
                if elapsed > duration+3:
                    raise TimeoutError("Live answer playback timed out")
                if expressive and elapsed >= 0:
                    index = min(int(elapsed*HZ),len(values)-1)
                    if index >= next_frame:
                        robot.send(frame(values[index]))
                        next_frame = index+1
                    if beat_index<len(beats) and elapsed>=beats[beat_index]["at"]*duration:
                        log.event("EXPRESSION_STATE", **beats[beat_index])
                        beat_index += 1
                await asyncio.sleep(.005)
        status = "completed"
        print(f"Genuine Conversation App capture: {destination}",flush=True)
        return receipt
    except (InterruptedError, asyncio.CancelledError, KeyboardInterrupt):
        status = "interrupted"
        raise
    finally:
        control.stop.set()
        if not task.done():
            task.cancel()
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await task
        if output:
            try:
                output.stop()
            except Exception as exc:
                status = "failed"
                log.event("ERROR", error="Audio shutdown: "+type(exc).__name__)
        try:
            recovery = robot.neutral()
        except Exception as exc:
            recovery = {"succeeded":False,"error":type(exc).__name__}
        try:
            log.event("LIVE_END", completion_status=status if recovery["succeeded"] else "failed",
                      neutral_recovery_succeeded=recovery["succeeded"], recovery=recovery)
        finally:
            log.close()
