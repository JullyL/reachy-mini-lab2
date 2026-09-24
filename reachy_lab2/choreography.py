"""Deterministic emotional performances built from the pinned Emotions library."""
import hashlib
import json
from pathlib import Path

import numpy as np

from .motion import parse_trajectory, rotation, rotvec
from .prosody import align_beats, load_alignment, TIMING_BASIS

ROOT = Path(__file__).resolve().parents[1]
HZ = 50
DEFAULT_SPEECH_MOTION = {
    "style": "emotion_prosody", "max_speed_deg_s": 65, "max_acceleration_deg_s2": 350,
    "blend_s": .5, "smoothing_s": .12, "head_accent_deg": 2.0, "antenna_accent_rad": .025,
}
STUDY_VERSION = "expressive-performance-v2"
STATES = {
    "attentive": "attentive1", "curious": "inquiring1", "thinking": "curious1",
    "explaining": "understanding1", "affirming": "yes1", "happy": "cheerful1",
    "enthusiastic": "enthusiastic1", "surprised": "surprised1",
}


def smooth(u):
    u = np.clip(u, 0, 1)
    return u**3 * (10 + u * (-15 + 6*u))


def vector(frame):
    head = np.asarray(frame["head"])
    return np.r_[head[:3, 3], rotvec(head[:3, :3]), frame["antennas"]]


def frame(values):
    head = np.eye(4)
    head[:3, :3] = rotation(values[3:6])
    head[:3, 3] = values[:3]
    return {"head": head.tolist(), "antennas": values[6:8].tolist(), "body_yaw": 0.0}


class EmotionLibrary:
    """Load, verify, cache and retime named source performances."""
    def __init__(self, root=ROOT):
        self.root = Path(root)
        directory = self.root / "assets/motion/emotions"
        manifest = json.loads((directory / "manifest.json").read_text())
        self.sources, self.hashes = {}, {}
        for entry in manifest["motions"]:
            raw = (directory / (entry["id"] + ".json")).read_bytes()
            if hashlib.sha256(raw).hexdigest() != entry["sha256"]:
                raise ValueError("Emotion source hash mismatch: " + entry["id"])
            times, frames = parse_trajectory(json.loads(raw))
            values = np.array([vector(f) for f in frames])
            times = np.asarray(times) - times[0]
            # Remove recorded setup offsets, retaining the source's relative performance.
            values -= values[0].copy()
            self.sources[entry["id"]] = (times / times[-1], values)
            self.hashes[entry["id"]] = entry["sha256"]

    def clip(self, state, duration, intensity=1.0):
        if state not in STATES or not .4 <= duration <= 30 or not 0 < intensity <= 1:
            raise ValueError("Unknown state or invalid clip duration/intensity")
        source_t, source = self.sources[STATES[state]]
        count = max(2, round(duration * HZ) + 1)
        t = np.linspace(0, 1, count)
        # Keep expressive excursions visible without normalizing noise into large movements.
        values = np.column_stack([np.interp(t, source_t, col) for col in source.T])
        limits = [(slice(0, 3), .008), (slice(3, 6), np.deg2rad(22)), (slice(6, 8), .65)]
        for section, limit in limits:
            peak = np.max(np.linalg.norm(values[:, section], axis=1))
            if peak > limit:
                values[:, section] *= limit / peak
        # Anticipation, a readable held pose, and eased release; no discontinuous cuts.
        ramp_s = min(.35, duration / 3)
        envelope = smooth(np.minimum(t, 1-t) * duration / ramp_s)
        values *= (envelope * intensity)[:, None]
        values[[0, -1]] = 0
        # Bound retiming speed, especially for long source recordings compressed into a phrase.
        for section, speed in [(slice(0, 3), .04), (slice(3, 6), 1.8), (slice(6, 8), 3.0)]:
            peak = np.max(np.linalg.norm(np.diff(values[:, section], axis=0), axis=1))*HZ
            if peak > speed:
                values[:, section] *= speed/peak
        return values


def _filter(values, sigma_s):
    radius = max(1, int(np.ceil(3*sigma_s*HZ)))
    offsets = np.arange(-radius, radius+1)
    kernel = np.exp(-.5*(offsets/(sigma_s*HZ))**2)
    kernel /= kernel.sum()
    padded = np.pad(values, ((radius, radius), (0,0)), mode="edge")
    return np.column_stack([np.convolve(col,kernel,mode="valid") for col in padded.T])


def speech_performance(library, beats, duration, settings=None, alignment=None):
    """Retimed full emotion recordings plus sparse head and light vowel-timed antenna accents."""
    settings = {**DEFAULT_SPEECH_MOTION, **(settings or {})}
    limits = {"max_speed_deg_s":(1,90), "max_acceleration_deg_s2":(10,500),
              "blend_s":(.2,1), "smoothing_s":(.08,.3), "head_accent_deg":(0,4),
              "antenna_accent_rad":(0,.06)}
    if settings["style"] != "emotion_prosody" or alignment is None:
        raise ValueError("Speech needs emotion_prosody settings and real audio alignment")
    for key,(low,high) in limits.items():
        if not np.isfinite(settings[key]) or not low <= settings[key] <= high:
            raise ValueError("Invalid speech setting: "+key)
    if duration <= 0 or abs(alignment["duration_s"]-duration) > .02:
        raise ValueError("Speech alignment duration mismatch")
    if not beats or any("accents" not in beat for beat in beats):
        raise ValueError("Speech requires aligned emotional beats")
    times = np.arange(int(np.ceil(duration*HZ))+1)/HZ
    values = np.zeros((len(times),8))
    weights = np.zeros(len(times))
    boundaries = [0.0]+[(a["end_s"]+b["start_s"])/2 for a,b in zip(beats,beats[1:])]+[duration]
    blend = settings["blend_s"]/2
    for i,beat in enumerate(beats):
        motion = beat.get("motion", STATES[beat["state"]])
        if motion not in library.sources:
            raise ValueError("Speech motion is not in the pinned library: "+motion)
        intensity = beat.get("intensity",1.0)
        if not 0 < intensity <= 1:
            raise ValueError("Speech intensity must be in (0,1]")
        source_t, raw = library.sources[motion]
        # Preserve the complete recorded head/antenna sequence, not one extracted pose.
        regular = np.linspace(0,1,201)
        source = np.column_stack([np.interp(regular,source_t,col) for col in raw.T])
        for section,limit in [(slice(0,3),.008),(slice(3,6),np.deg2rad(20)),(slice(6,8),.55)]:
            peak = np.max(np.linalg.norm(source[:,section],axis=1))
            if peak > limit:
                source[:,section] *= limit/peak
        start, end = max(0,boundaries[i]-blend), min(duration,boundaries[i+1]+blend)
        source_peak = np.clip(regular[np.argmax(np.linalg.norm(source[:,3:6],axis=1))],.15,.85)
        middle = (beat["start_s"]+beat["end_s"])/2
        eligible = [c for c in beat["accents"] if start+.3 < c["at_s"] < end-.3]
        stroke = min(eligible,key=lambda c:abs(c["at_s"]-middle))["at_s"] if eligible else middle
        stroke = np.clip(stroke,start+.1*(end-start),end-.1*(end-start))
        phase = np.interp(times,[start,stroke,end],[0,source_peak,1])
        track = np.column_stack([np.interp(phase,regular,col) for col in source.T])*intensity
        weight = ((times>=start)&(times<=end)).astype(float)
        if i:
            weight *= smooth((times-start)/(2*blend))
        if i+1<len(beats):
            weight *= smooth((end-times)/(2*blend))
        values += track*weight[:,None]
        weights += weight
    values /= np.maximum(weights,1e-9)[:,None]
    values = _filter(values,settings["smoothing_s"])
    # Sparse nod accents on salient words/endings; no head twitch for every syllable.
    for beat in beats:
        for accent in beat["accents"]:
            strength = .6 if accent["kind"] == "phrase_ending" else 1.0
            values[:,4] += np.deg2rad(settings["head_accent_deg"])*strength*np.exp(-.5*((times-accent["at_s"])/.18)**2)
    # Phoneme-aligned vowel centers are an estimate of syllable timing, not mouth animation.
    syllables = [s for w in alignment["words"] for s in w["syllables"]]
    energy = max((s["rms"] for s in syllables),default=1)
    for syllable in syllables:
        strength = .35+.65*syllable["rms"]/max(energy,1e-9)
        pulse = settings["antenna_accent_rad"]*strength*np.exp(-.5*((times-syllable["at_s"])/.09)**2)
        values[:,6] += pulse
        values[:,7] -= pulse
    envelope = smooth(np.minimum(times,np.maximum(0,duration-times))/.4)
    values *= envelope[:,None]
    values[[0,-1]]=0
    # Smooth all channels before limiting derivatives; bounds apply to the complete track.
    for section,limit,speed,acceleration in [
        (slice(0,3),.008,.04,.25),
        (slice(3,6),np.deg2rad(22),np.deg2rad(settings["max_speed_deg_s"]),np.deg2rad(settings["max_acceleration_deg_s2"])),
        (slice(6,8),.65,1.5,12.0),
    ]:
        peak = np.max(np.linalg.norm(values[:,section],axis=1))
        velocity = np.diff(values[:,section],axis=0)*HZ
        peak_speed = np.max(np.linalg.norm(velocity,axis=1))
        peak_acceleration = np.max(np.linalg.norm(np.diff(velocity,axis=0)*HZ,axis=1)) if len(velocity)>1 else 0
        scale = min(1,limit/max(peak,1e-12),speed/max(peak_speed,1e-12),acceleration/max(peak_acceleration,1e-12))
        values[:,section] *= scale
    return values


def compile_performance(question, config, root=ROOT):
    """Compile both conditions from one frozen answer-specific emotional score."""
    root = Path(root)
    score = json.loads((root / "config/choreography.json").read_text())
    duration = question["duration_s"]
    speech_start = config["speech_target_s"]
    total = speech_start + duration
    times = np.arange(int(np.ceil(total * HZ)) + 1) / HZ
    base = np.zeros((len(times), 8))
    original = json.loads((root / config["gesture"]).read_text())
    original_t, original_f = parse_trajectory(original)
    start = round(config["cue_start_s"] * HZ)
    baseline = np.array([vector(f) for f in original_f])
    for j in range(8):
        base[start:start+51, j] = np.interp(np.arange(51)/HZ, original_t, baseline[:, j])
    library = EmotionLibrary(root)
    expressive = np.zeros_like(base)
    cues = []

    def place(state, begin, end, phrase, intensity=1.0, head_pitch_deg=None):
        if end - begin < .4:
            raise ValueError("Choreography segment is too short")
        a, b = round(begin*HZ), round(end*HZ)
        values = library.clip(state, (b-a)/HZ, intensity)
        if head_pitch_deg is not None:
            if not np.isfinite(head_pitch_deg) or not 0 <= head_pitch_deg <= 18:
                raise ValueError("Thinking head pitch must be between 0 and 18 degrees downward")
            local_t = np.arange(len(values))/HZ
            envelope = smooth(np.minimum(local_t, (b-a)/HZ-local_t)/.35)
            # SDK axes: x forward, y left, z up. Positive Y pitch looks down.
            values[:, 3:6] = 0
            values[:, 4] = np.deg2rad(head_pitch_deg)*envelope
        expressive[a:b+1] = values
        cues.append({"start_s": a/HZ, "end_s": b/HZ, "state": state,
                     "phrase": phrase, "source_motion": STATES[state]})
        if head_pitch_deg is not None:
            cues[-1]["head_pitch_deg"] = head_pitch_deg

    selection = score["questions"].get(question["id"])
    thinking = (selection or {}).get("thinking", {})
    place("curious", config["cue_start_s"], 2.6, "Considering the question",
          head_pitch_deg=thinking.get("curious_head_pitch_deg"))
    place("thinking", 2.6, speech_start, "Searching, then ready to explain")
    if selection is None or selection["answer_text_sha256"] != hashlib.sha256(question["answer"].encode()).hexdigest() or selection["audio_sha256"] != question["sha256"]:
        raise ValueError("Answer has no matching reviewed choreography score; author a score for this exact text")
    timing_path = root/selection["alignment"]
    if hashlib.sha256(timing_path.read_bytes()).hexdigest() != selection["alignment_sha256"]:
        raise ValueError("Speech alignment hash mismatch; regenerate and review score")
    alignment = load_alignment(timing_path,root/question["audio"],question["answer"])
    beats = align_beats(selection["beats"],alignment)
    for beat in beats:
        if beat["phrase"] not in question["answer"]:
            raise ValueError("Choreography phrase is absent from answer")
        cues.append({"start_s":speech_start+beat["start_s"],
                     "end_s":speech_start+beat["end_s"], "state":beat["state"],
                     "phrase":beat["phrase"], "source_motion":beat.get("motion",STATES[beat["state"]]),
                     "accents":beat["accents"]})
    speech_settings = {**DEFAULT_SPEECH_MOTION, **score.get("speech_motion", {})}
    speech_values = speech_performance(library, beats, duration, speech_settings, alignment)
    speech_index = round(speech_start*HZ)
    expressive[speech_index:speech_index+len(speech_values)] = speech_values
    # A carries the original gesture. B replaces its interval with the expressive track.
    enabled = config["conditions"][config["selected_condition"]]
    values = expressive if enabled else base
    payload = {"time": times.tolist(), "set_target_data": [frame(v) for v in values],
               "cues": cues if enabled else [{"start_s": config["cue_start_s"],
                   "end_s": config["cue_start_s"]+1, "state": "brief_cue",
                   "phrase": "Baseline preparation cue", "source_motion": "processing.json"}],
               "source_hashes": library.hashes, "score": selection,
               "speech_motion":speech_settings,
               "timing_basis": TIMING_BASIS}
    payload["sha256"] = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    return payload
