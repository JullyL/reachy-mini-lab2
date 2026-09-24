"""Pre-opened local speaker stream with device-clock scheduled cached speech."""
import queue
import time


class AudioOutput:
    def __init__(self, rate, samples, silent=False):
        self.rate, self.samples, self.silent = rate, samples, silent
        self.events = queue.SimpleQueue()
        self.target = None
        self.sent = 0
        self.done = False
        self.stopped = False
        self.stream = None

    def open(self):
        if self.silent:
            return
        import sounddevice as sd
        self.stream = sd.OutputStream(samplerate=self.rate, channels=1,
                                      dtype="float32", blocksize=0, latency="low",
                                      callback=self._callback)
        self.stream.start()

    def arm(self, target):
        self.target = target

    def _callback(self, out, count, clock, status):
        now = time.perf_counter()
        out.fill(0)
        if status:
            self.events.put(("AUDIO_ERROR", now, {"error": str(status)}))
        if self.target is None or self.stopped or self.done:
            return
        # PortAudio's outputBufferDacTime is the predicted device presentation
        # time, not a microphone measurement. Convert to the monotonic clock.
        dac = now + (clock.outputBufferDacTime - clock.currentTime)
        if self.sent == 0:
            start = max(0, int(round((self.target - dac) * self.rate)))
            if start >= count:
                return
        else:
            start = 0
        n = min(count - start, len(self.samples) - self.sent)
        out[start:start + n, 0] = self.samples[self.sent:self.sent + n]
        if self.sent == 0 and n:
            self.events.put(("SPEECH_START", dac + start / self.rate,
                             {"basis": "PortAudio predicted DAC time; acoustic onset unmeasured"}))
        self.sent += n
        if self.sent == len(self.samples):
            self.done = True
            self.events.put(("SPEECH_END", dac + (start + n) / self.rate, {}))

    def poll_silent(self, now):
        if self.silent and self.target is not None and not self.stopped:
            if not self.sent and now >= self.target:
                self.sent = len(self.samples)
                self.events.put(("SPEECH_START", now, {"basis": "SILENT MOCK; no audio output"}))
            if self.sent and not self.done and now >= self.target + len(self.samples) / self.rate:
                self.done = True
                self.events.put(("SPEECH_END", now, {}))

    def stop(self):
        self.stopped = True
        if self.stream is not None:
            self.stream.abort()
            self.stream.close()
            self.stream = None

