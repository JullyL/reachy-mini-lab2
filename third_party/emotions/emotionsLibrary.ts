/**
 * Loader + cache for the `pollen-robotics/reachy-mini-emotions-library`
 * dataset.
 *
 * Each emotion lives as a JSON file in the dataset's `main` branch:
 *   https://huggingface.co/datasets/<DATASET_ID>/resolve/main/<id>.json
 *
 * The HF CDN serves these with permissive CORS (verified manually
 * with `curl -i`), so we can fetch them straight from the browser
 * without a proxy.
 *
 * The optional companion sound is at:
 *   https://huggingface.co/datasets/<DATASET_ID>/resolve/main/<id>.ogg
 *
 * Trajectories are 50-100 KB each (and audio blobs are typically
 * 50-300 KB when present). We cache them in memory once fetched so
 * the second playback of an emotion is upload-only with no extra
 * roundtrip to the HF CDN. We don't bother with localStorage /
 * IndexedDB - re-loading the page will always re-warm from the CDN,
 * which is fast enough.
 *
 * ─── Format note ────────────────────────────────────────────────
 *
 * We deliberately keep `set_target_data` in the exact shape served
 * by the dataset (4×4 nested head matrices, `[r, l]` antennas,
 * `body_yaw` radians). The daemon's `playMove`/`upload_move_*`
 * pipeline understands that schema natively (it's the same one the
 * Python `reachy_mini.recorder` writes), so passing it through
 * verbatim is both more efficient (no per-frame transform) and more
 * robust (no chance of a re-encoding bug between us and the daemon).
 */

const DATASET_ID = 'pollen-robotics/reachy-mini-emotions-library';
const CDN_BASE = `https://huggingface.co/datasets/${DATASET_ID}/resolve/main`;

/**
 * Parsed trajectory. We only validate that `time` and
 * `set_target_data` are present + aligned; the inner frame shape is
 * passed through to the daemon untouched (see file header).
 */
export interface Trajectory {
  id: string;
  description?: string;
  /** Per-frame timestamps, in seconds, monotonic, starting at 0 (or near 0). */
  time: number[];
  /** Raw per-frame target spec, daemon-native schema. Opaque to us. */
  set_target_data: object[];
  /** Total duration in seconds (last timestamp). */
  durationSec: number;
}

const trajectoryCache = new Map<string, Promise<Trajectory>>();

/**
 * Sidecar synchronous cache of resolved trajectory durations.
 *
 * Promises can't expose their resolved value synchronously, but the
 * UI sometimes needs the duration on the very first render of a
 * component (e.g. the family panel wants to paint duration badges
 * with no fade-in flicker if the trajectory is already warm). We
 * populate this Map from the same async path as `trajectoryCache`,
 * right after a successful parse, and expose `getCachedDurationSec`
 * for components that want to seed `useState` with already-known
 * values. Never populated speculatively - if it's here, the full
 * trajectory has been fetched and parsed at least once this session.
 */
const durationsByIdSync = new Map<string, number>();

/**
 * Synchronously read a previously-resolved trajectory duration in
 * seconds. Returns `undefined` if the trajectory hasn't been
 * fetched + parsed yet in this session. Safe to call during render.
 */
export function getCachedDurationSec(id: string): number | undefined {
  return durationsByIdSync.get(id);
}

/**
 * Build the URL of an emotion's trajectory JSON.
 */
export function trajectoryUrl(id: string): string {
  return `${CDN_BASE}/${encodeURIComponent(id)}.json`;
}

/**
 * Build the URL of an emotion's companion sound. The dataset ships
 * OGG files (it migrated from WAV); some emotions don't have one
 * (the daemon plays nothing for those); the consumer is expected to
 * handle 404s gracefully.
 */
export function soundUrl(id: string): string {
  return `${CDN_BASE}/${encodeURIComponent(id)}.ogg`;
}

/**
 * Fetch + parse a trajectory. Cached per-id; concurrent calls share
 * the same in-flight promise.
 */
export function loadTrajectory(id: string): Promise<Trajectory> {
  const cached = trajectoryCache.get(id);
  if (cached) return cached;

  const promise = (async () => {
    const res = await fetch(trajectoryUrl(id));
    if (!res.ok) {
      throw new Error(
        `Failed to fetch trajectory '${id}': ${res.status} ${res.statusText}`,
      );
    }
    const raw = await res.json();
    const traj = parseTrajectory(id, raw);
    durationsByIdSync.set(id, traj.durationSec);
    return traj;
  })();

  // If the fetch fails, evict the cached rejected promise so the next
  // call gets a fresh attempt instead of always seeing the old error.
  promise.catch(() => trajectoryCache.delete(id));
  trajectoryCache.set(id, promise);
  return promise;
}

/**
 * Audio-blob cache (parallel to `trajectoryCache`). Each entry
 * resolves to either the audio `Blob` (passed to `robot.playMove`'s
 * `audioBlob` option for daemon-side lock-step playback) or `null`
 * when the emotion has no companion sound. Resolved promises are
 * cached; rejected ones evict so the next `play` retries from the
 * CDN. We DO `await audioBlob.arrayBuffer()` inside the SDK upload
 * path so the blob itself stays cheap to hold in memory.
 */
const audioBlobCache = new Map<string, Promise<Blob | null>>();

/**
 * Fetch the companion sound (if any). Resolves with the `Blob` on a
 * 2xx response, `null` on 404 / non-OK / network error. Promise
 * cached per-id, so a second play of the same emotion is upload-only.
 *
 * We expose this separately from `loadTrajectory` because the
 * trajectory and the audio share a single upload step in the SDK's
 * `playMove`, but the trajectory is also useful on its own (e.g.
 * for the duration badge in the family grid, which doesn't need the
 * audio).
 */
export function loadAudioBlob(id: string): Promise<Blob | null> {
  const cached = audioBlobCache.get(id);
  if (cached) return cached;

  const promise = (async (): Promise<Blob | null> => {
    try {
      const res = await fetch(soundUrl(id));
      if (!res.ok) return null;
      return await res.blob();
    } catch {
      return null;
    }
  })();

  audioBlobCache.set(id, promise);
  return promise;
}

/**
 * Translate the raw dataset JSON into our internal `Trajectory`
 * shape. The dataset schema we observed in the wild:
 *
 *   {
 *     "description": "loving emotion",
 *     "time": [0.0, 0.01, 0.02, …],
 *     "set_target_data": [
 *       { "head": [[…4×4…]], "antennas": [r, l], "body_yaw": 0.1 },
 *       …
 *     ]
 *   }
 *
 * We pass `set_target_data` through verbatim (see file header). The
 * only normalisation is on `time`: some recorder builds emit an
 * off-by-one length, which we trim/pad to match the frame count so
 * the daemon's strict length check in `playMove` doesn't reject.
 */
function parseTrajectory(id: string, raw: unknown): Trajectory {
  if (!raw || typeof raw !== 'object') {
    throw new Error(`Trajectory '${id}' is not a JSON object`);
  }
  const obj = raw as Record<string, unknown>;
  const description =
    typeof obj.description === 'string' ? obj.description : undefined;

  const time = Array.isArray(obj.time)
    ? (obj.time as unknown[]).filter((v): v is number => typeof v === 'number')
    : [];

  // Accept the canonical `set_target_data` plus the legacy `frames`
  // alias the older recorder used. Either is passed through as-is
  // to the daemon's upload path.
  const rawFrames: unknown[] =
    (Array.isArray(obj.set_target_data) && (obj.set_target_data as unknown[])) ||
    (Array.isArray(obj.frames) && (obj.frames as unknown[])) ||
    [];

  const setTargetData = rawFrames.filter(
    (f): f is object => typeof f === 'object' && f !== null,
  );

  if (setTargetData.length === 0) {
    throw new Error(
      `Trajectory '${id}' has no frames (expected 'set_target_data' or 'frames')`,
    );
  }
  if (time.length !== setTargetData.length) {
    // Some recorder builds emit `time` as an array of length
    // `frames.length + 1` (start + per-frame). Trim/pad as needed
    // rather than failing - the daemon's strict length check in
    // `playMove` will reject otherwise.
    if (time.length > setTargetData.length) time.length = setTargetData.length;
    while (time.length < setTargetData.length) {
      const last = time[time.length - 1] ?? 0;
      time.push(last + 0.01);
    }
  }

  // Downsample to UPLOAD_HZ before we ever hand this to the daemon.
  //
  // Why: the wireless robot's motor control loop runs at 50 Hz
  // (`control_loop_frequency = 50.0` in the daemon backend), and the
  // daemon's `RecordedMove.evaluate(t)` linearly interpolates between
  // frames (bisect + `linear_pose_interpolation`), so feeding it the
  // dataset's native 100 Hz buys zero motion fidelity on this
  // hardware - it just doubles the WebRTC upload payload (and the
  // daemon's per-chunk INFO logging) on a link where that upload is
  // the dominant tap-to-play latency. Halving the frame count roughly
  // halves the trajectory upload with no visible difference, since the
  // daemon re-interpolates on its own 50 Hz clock anyway.
  const { time: dsTime, frames: dsFrames } = downsampleByHz(
    time,
    setTargetData,
    UPLOAD_HZ,
  );

  const durationSec = dsTime[dsTime.length - 1] ?? 0;

  return {
    id,
    description,
    time: dsTime,
    set_target_data: dsFrames,
    durationSec,
  };
}

/**
 * Target sample rate for trajectories we upload to the daemon. Matches
 * the wireless backend's `control_loop_frequency` (50 Hz), so we never
 * ship frames the hardware can't act on. The daemon interpolates
 * between whatever frames we send, so this is purely an upload-size /
 * daemon-CPU optimisation, not a motion change.
 */
const UPLOAD_HZ = 50;

/**
 * Time-based decimation of a (time, frames) pair down to ~`targetHz`.
 *
 * Walks the timeline and keeps a frame only when at least `1/targetHz`
 * seconds have elapsed since the last kept frame. The first and last
 * frames are always kept so the trajectory's start pose (used for the
 * smooth-prelude `initialGotoDuration`) and total duration are exact.
 * Returns the inputs untouched when they're already at or below the
 * target rate, or too short to decimate safely.
 */
function downsampleByHz(
  time: number[],
  frames: object[],
  targetHz: number,
): { time: number[]; frames: object[] } {
  const n = frames.length;
  if (n <= 2 || time.length !== n) return { time, frames };

  const total = (time[n - 1] ?? 0) - (time[0] ?? 0);
  if (total <= 0) return { time, frames };

  const nativeHz = (n - 1) / total;
  if (nativeHz <= targetHz * 1.1) return { time, frames };

  const minGap = 1 / targetHz;
  const outTime: number[] = [];
  const outFrames: object[] = [];

  let lastKept = -Infinity;
  for (let i = 0; i < n; i++) {
    const t = time[i] ?? 0;
    const isFirst = i === 0;
    const isLast = i === n - 1;
    if (isFirst || isLast || t - lastKept >= minGap) {
      outTime.push(t);
      outFrames.push(frames[i]!);
      lastKept = t;
    }
  }

  // Guard: if the last frame collapsed onto the previous kept one
  // (tiny final gap), the loop above still pushed it, so time + frames
  // stay aligned. Nothing else to fix up.
  return { time: outTime, frames: outFrames };
}
