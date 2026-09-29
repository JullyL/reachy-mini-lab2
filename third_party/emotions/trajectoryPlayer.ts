/**
 * Trajectory player - thin orchestration layer over the SDK's
 * `robot.playMove(...)` daemon-side recorded-move pipeline.
 *
 * Why daemon-side, and not a rAF stream of `setTarget` calls (the
 * previous design)?
 *
 *   - The daemon runs a hard real-time control loop (50 Hz on the
 *     wireless robot, higher on wired). It consumes the trajectory on
 *     its own clock, so a janky browser tab, a GC pause, a fluctuating
 *     WebRTC link, or a sluggish phone CPU never causes frame drops or
 *     visible motion glitches once playback has started.
 *   - Audio + motion stay in lock-step at the sample level: the SDK
 *     ships the companion sound alongside the trajectory, the daemon
 *     starts both with a configurable lead (`audioLeadMs`).
 *   - The smooth transition from the robot's current pose to the
 *     trajectory's first frame ("prelude") is now also handled by
 *     the daemon via `initialGotoDuration`, which routes through
 *     the same daemon-side goto that recently got the
 *     atomic-target-pin fix in PR #1138 (so torque-off → move-by-
 *     hand → play-an-emotion can never produce a brutal snap).
 *
 * What we still own client-side:
 *
 *   - Single-flight semantics: at most one `playMove` is in flight
 *     on the data channel at a time. A new `play()` call sends
 *     `cancelMove()` first, waits for the previous promise to
 *     settle, then uploads the new trajectory.
 *   - Status surface (`'idle' | 'loading' | 'playing' | 'done' |
 *     'error'`) and a single `onProgress({durationSec})` emission
 *     when the daemon acks `play_uploaded_move started`. The UI
 *     drives its CSS bar from that one duration value (a single
 *     GPU-paced `scaleX 0 → 1` animation), so we don't need per-
 *     frame React state churn.
 *   - Computing `initialGotoDuration` from the present `robotState`
 *     vs the first trajectory frame, using the same distance-scaled
 *     formula as `gotoBasePose` in the JS-best-practices Space
 *     (head magic-mm + antenna deg + body deg, slowest channel wins,
 *     clamped to [0.2 s, 1.5 s]).
 */

import { safelyReturnToPose } from '@pollen-robotics/reachy-mini-sdk/animation';

import type { ReachyMiniInstance } from '@/sdk-types';
import {
  loadAudioBlob,
  loadTrajectory,
  type Trajectory,
} from './emotionsLibrary';

export type PlayerStatus =
  | 'idle'
  | 'loading'
  | 'playing'
  | 'cancelling'
  | 'done'
  | 'error';

export interface PlayerProgress {
  /**
   * 0..1 fraction of the trajectory played. We only report 0 at
   * `playing` onset and 1 at `done`; intermediate values are not
   * emitted (the UI drives its bar from a single CSS animation
   * keyed off `durationSec`).
   */
  fraction: number;
  /** Seconds elapsed since playback started (excludes loading). */
  elapsedSec: number;
  /**
   * Total play duration in seconds as reported by the daemon's
   * `play_uploaded_move started` ack. Includes `initialGotoDuration`
   * + the trajectory itself, so the bar honestly reflects the full
   * thing the user is waiting on.
   */
  durationSec: number;
}

export interface PlayerCallbacks {
  onStatus?(status: PlayerStatus, error?: Error): void;
  onProgress?(progress: PlayerProgress): void;
}

// ─── Smooth-prelude tuning ───────────────────────────────────────
//
// Ports of the constants from `RemiFabre/reachy-mini-js-practices`.
// Each channel produces its own candidate duration; the slowest
// channel wins, then we clamp to [TRANSITION_MIN, TRANSITION_MAX].
// SKIP_BELOW is our local heuristic: if the slowest channel is below
// it, the robot is already at (or near) the first frame and we let
// the daemon kick off the trajectory immediately with `0` prelude.
const SCALE_HEAD = 0.02; // s per head "magic-mm" (trans_mm + rot_deg)
const SCALE_ANTENNA = 0.005; // s per degree of antenna delta
const SCALE_BODY = 0.015; // s per degree of body_yaw delta
const TRANSITION_MIN = 0.2;
const TRANSITION_MAX = 1.5;
const SKIP_BELOW = 0.15;

// ─── Daemon-side playback frequency ──────────────────────────────
//
// The wireless robot's motor control loop runs at 50 Hz
// (`control_loop_frequency = 50.0` in the daemon backend), so there's
// nothing to gain from evaluating the move any faster - a 100 Hz
// `playFrequency` just makes the daemon's async playback loop spin
// twice as often (each tick calling `move.evaluate` + three
// `set_target_*`) for frames the hardware can't apply, stealing CPU
// from the same event loop that drives WebRTC on an already-busy Pi.
// We upload trajectories pre-decimated to 50 Hz (see
// `emotionsLibrary.downsampleByHz`) and play them back at the matching
// rate. The daemon interpolates between frames, so motion is identical.
const PLAY_FREQUENCY = 50;

// ─── Start-ack timeout ───────────────────────────────────────────
//
// `playMove` waits for the daemon's `play_uploaded_move started` ack
// before it reports `playing`. That ack only fires AFTER the whole
// trajectory + companion audio have been uploaded over the WebRTC data
// channel. Over Wi-Fi (especially to the wireless robot, whose Pi has
// no rtpgccbwe congestion control and logs every 12 KB chunk) that
// upload was measured at 2-7 s; the SDK's 8 s default left almost no
// margin and turned a slow link into an outright "Daemon did not
// respond" failure. We give it a generous ceiling so a sluggish
// upload degrades to a longer loading spinner, never an error.
const START_TIMEOUT_MS = 30000;

/**
 * Single-flight controller over `robot.playMove`. At most one
 * trajectory is uploaded/playing on the data channel at a time;
 * a fresh `play()` cancels the in-flight one (best-effort via
 * `cancelMove`) and waits for it to settle before starting the new
 * upload, so we never race two `upload_move_chunk` streams.
 */
export class TrajectoryPlayer {
  private robot: ReachyMiniInstance;
  private status: PlayerStatus = 'idle';
  private callbacks: PlayerCallbacks = {};

  /**
   * Monotonic token bumped on every `play()` / `cancel()`. Async
   * continuations compare against the current value before mutating
   * status or emitting callbacks; a mismatch means a newer call has
   * superseded us and we silently exit.
   */
  private cancelToken = 0;

  /**
   * Promise of the currently-running (or just-cancelled) `playMove`
   * call. A new `play()` first awaits this to settle so the two
   * uploads don't fight over the data-channel's chunk stream.
   */
  private inflightPlay: Promise<unknown> | null = null;

  constructor(robot: ReachyMiniInstance) {
    this.robot = robot;
  }

  /**
   * Subscribe to status + progress updates. Returns an unsubscribe
   * function. Replaces any existing subscription (single-consumer
   * by design).
   */
  subscribe(callbacks: PlayerCallbacks): () => void {
    this.callbacks = callbacks;
    return () => {
      this.callbacks = {};
    };
  }

  /**
   * Fetch + play a trajectory by emotion id. Resolves when the
   * daemon reports `finished`, `cancelled`, or `error`. Safe to
   * `await`, but the UI normally fires-and-forgets and reacts to
   * `onStatus` callbacks instead.
   */
  async play(id: string): Promise<void> {
    const myToken = ++this.cancelToken;

    // Cancel anything already in flight on the daemon side, then
    // wait for its `playMove` promise to settle before we start
    // uploading the new trajectory. Without this two `upload_move_*`
    // streams would race on the data channel and the daemon would
    // reject one of them as out-of-order.
    if (this.inflightPlay) {
      try {
        this.robot.cancelMove();
      } catch {
        // Channel might already be closed; the playMove promise
        // will surface that for us.
      }
      try {
        await this.inflightPlay;
      } catch {
        // The previous play errored out; doesn't concern us.
      }
      if (myToken !== this.cancelToken) return;
    }

    this.setStatus('loading');

    let trajectory: Trajectory;
    let audioBlob: Blob | null;
    try {
      // Both fetches share a per-id in-memory cache, so a re-play
      // of the same emotion is upload-only.
      const result = await Promise.all([
        loadTrajectory(id),
        loadAudioBlob(id),
      ]);
      trajectory = result[0];
      audioBlob = result[1];
    } catch (err) {
      if (myToken !== this.cancelToken) return;
      this.setStatus('error', err as Error);
      return;
    }
    if (myToken !== this.cancelToken) return;

    // Compute the smooth-prelude duration from the present robot
    // pose vs the first frame of this trajectory. The daemon will
    // run this `goto` first (using `gotoTarget` semantics + the
    // PR #1138 atomic-target-pin), then start streaming frames.
    const initialGotoDuration = computeInitialGotoDuration(
      this.robot.robotState,
      trajectory.set_target_data[0],
    );

    let result: { finished?: boolean; cancelled?: boolean; error?: unknown };
    const playPromise = this.robot.playMove(
      {
        time: trajectory.time,
        set_target_data: trajectory.set_target_data,
      },
      {
        audioBlob,
        initialGotoDuration,
        playFrequency: PLAY_FREQUENCY,
        startTimeoutMs: START_TIMEOUT_MS,
        // Daemon acks `started` once the trajectory is actually
        // streaming on its control loop (so AFTER the prelude
        // upload + AFTER the initial-goto window). This is the
        // moment our bar should start counting; the duration we
        // get back already accounts for the prelude so the bar
        // never lies about how long the user is waiting.
        onStarted: ({ duration_s }) => {
          if (myToken !== this.cancelToken) return;
          this.setStatus('playing');
          this.callbacks.onProgress?.({
            fraction: 0,
            elapsedSec: 0,
            durationSec: duration_s,
          });
        },
      },
    );
    this.inflightPlay = playPromise;

    try {
      result = await playPromise;
    } catch (err) {
      if (this.inflightPlay === playPromise) this.inflightPlay = null;
      if (myToken !== this.cancelToken) return;
      this.setStatus('error', err as Error);
      return;
    }
    if (this.inflightPlay === playPromise) this.inflightPlay = null;
    if (myToken !== this.cancelToken) return;

    if (result.cancelled) {
      // Cancellation handler already moved status to 'idle'; if it
      // came from the daemon spontaneously (e.g. a higher-priority
      // command preempted us), make sure we surface it too.
      if (this.status !== 'idle') this.setStatus('idle');
      return;
    }
    if (result.error) {
      this.setStatus('error', new Error(String(result.error)));
      return;
    }
    this.setStatus('done');
  }

  /**
   * Stop the current playback. Idempotent. Sends `cancel_move` to
   * the daemon; the daemon stops the control loop and freezes the
   * motors at the present pose (it does NOT snap back to a neutral
   * pose - that's the caller's call, same contract as before).
   */
  cancel(): void {
    if (
      this.status === 'idle' ||
      this.status === 'done' ||
      this.status === 'error'
    ) {
      return;
    }
    this.cancelToken++;
    try {
      this.robot.cancelMove();
    } catch {
      // ignore - channel might already be closed
    }
    this.setStatus('idle');
  }

  /**
   * Smoothly drive the robot back to the canonical safe-rest pose
   * (`INIT_POSE`: head identity, antennas ~±10° outward, body yaw 0)
   * via the SDK's `safelyReturnToPose` helper. That helper enables
   * torque safely, reads the present pose, computes a distance-scaled
   * `gotoTarget` duration (the daemon-mirrored `scaledDuration`), and
   * dispatches the goto - so a small residual offset eases back
   * quickly while a fully-twisted pose takes the full window.
   *
   * We use the shared helper rather than hand-rolling the pose +
   * duration math on purpose: `INIT_POSE`'s ~±10° antenna offset is a
   * mechanical anti-resonance constant (PR #952) that must track the
   * daemon, and re-implementing `scaledDuration` per-app is the
   * documented anti-pattern (§14.6 of the JS App Creation Guide).
   *
   * Fire-and-forget: `safelyReturnToPose` returns synchronously after
   * dispatch (the daemon owns the interpolation) and swallows
   * "channel closed" errors, so this is safe to call mid-teardown.
   *
   * Not folded into `cancel()` on purpose: `cancel()` is also used
   * internally for single-flight chaining and by `dispose()` on
   * unmount, neither of which should re-pose a robot the user is
   * navigating away from. Callers decide when a return-to-base is
   * the right gesture (user-initiated stop, natural completion).
   */
  returnToBase(): void {
    safelyReturnToPose(this.robot);
  }

  /**
   * Best-effort dispose. Stops anything in flight. Safe to call
   * from a React effect cleanup.
   */
  dispose(): void {
    this.cancel();
  }

  // ─── Internals ───────────────────────────────────────────────

  private setStatus(status: PlayerStatus, error?: Error): void {
    this.status = status;
    this.callbacks.onStatus?.(status, error);
  }
}

// ─── Distance-scaled prelude duration ────────────────────────────
//
// Same formula as `gotoBasePose` in
// `RemiFabre/reachy-mini-js-practices`: each animated channel
// produces its own duration candidate (`distance × seconds_per_unit`),
// the slowest channel wins, the result is clamped to
// [TRANSITION_MIN, TRANSITION_MAX], and we short-circuit to `0`
// when the robot is already close enough (no daemon-side goto =
// the daemon kicks off the trajectory immediately, no extra
// latency).

interface PartialRobotState {
  head?: number[];
  antennas?: number[];
  body_yaw?: number;
}

interface RawFirstFrame {
  head?: unknown;
  antennas?: unknown;
  body_yaw?: unknown;
}

function computeInitialGotoDuration(
  state: PartialRobotState | undefined,
  firstFrame: object | undefined,
): number {
  if (!state || !firstFrame) return 0;
  const f = firstFrame as RawFirstFrame;

  let largestSec = 0;

  if (Array.isArray(state.head) && state.head.length === 16) {
    const target = flattenHead(f.head);
    if (target) {
      const magicMm = headMagicMm(state.head, target);
      largestSec = Math.max(largestSec, magicMm * SCALE_HEAD);
    }
  }

  if (
    Array.isArray(state.antennas) &&
    state.antennas.length === 2 &&
    Array.isArray(f.antennas) &&
    f.antennas.length === 2
  ) {
    const fa0 = typeof f.antennas[0] === 'number' ? f.antennas[0] : null;
    const fa1 = typeof f.antennas[1] === 'number' ? f.antennas[1] : null;
    if (
      fa0 != null &&
      fa1 != null &&
      typeof state.antennas[0] === 'number' &&
      typeof state.antennas[1] === 'number'
    ) {
      const dR = Math.abs(radToDeg(fa0 - state.antennas[0]));
      const dL = Math.abs(radToDeg(fa1 - state.antennas[1]));
      largestSec = Math.max(largestSec, Math.max(dR, dL) * SCALE_ANTENNA);
    }
  }

  if (typeof state.body_yaw === 'number' && typeof f.body_yaw === 'number') {
    const dB = Math.abs(radToDeg(f.body_yaw - state.body_yaw));
    largestSec = Math.max(largestSec, dB * SCALE_BODY);
  }

  // No channel produced a candidate: most often, the daemon hasn't
  // pushed a state event yet (we just connected) and we have no
  // reading to anchor the prelude on. Better to skip the goto than
  // to send a half-spec one that would snap unread channels to
  // default.
  if (largestSec === 0) return 0;

  // Already at the first frame (or close enough): skip the prelude
  // entirely so chained plays from the same neutral pose don't
  // accumulate visible "settle" pauses.
  if (largestSec < SKIP_BELOW) return 0;

  return Math.min(Math.max(largestSec, TRANSITION_MIN), TRANSITION_MAX);
}

/**
 * Flatten the first-frame `head` field to a 16-element row-major
 * 4×4. The dataset stores nested 4×4 (`[[…], [], [], [0,0,0,1]]`);
 * the SDK's `robotState.head` and our distance math both want flat.
 * Returns `null` if the field is missing or malformed.
 */
function flattenHead(h: unknown): number[] | null {
  if (!Array.isArray(h)) return null;
  if (h.length === 16 && h.every((n) => typeof n === 'number')) {
    return h as number[];
  }
  if (h.length === 4 && Array.isArray(h[0]) && (h[0] as unknown[]).length === 4) {
    const flat: number[] = [];
    for (let i = 0; i < 4; i++) {
      const row = h[i] as unknown[];
      for (let j = 0; j < 4; j++) {
        const v = row[j];
        flat.push(typeof v === 'number' && Number.isFinite(v) ? v : 0);
      }
    }
    return flat;
  }
  return null;
}

/**
 * "Magic-mm" head distance: translation in mm plus rotation in
 * degrees, fused into a single scalar so the slowest dimension
 * dominates the duration estimate. Mirrors the Python SDK's
 * `distance_between_poses` (utils/interpolation.py) and Rémi's
 * port in `reachy-mini-js-practices`.
 *
 * Both arguments are flat row-major 4×4 (index = row*4 + col).
 * Translation lives at indices 3, 7, 11 (column 3, rows 0..2);
 * the rotation block is the top-left 3×3.
 */
function headMagicMm(p1: number[], p2: number[]): number {
  const dx = (p1[3] ?? 0) - (p2[3] ?? 0);
  const dy = (p1[7] ?? 0) - (p2[7] ?? 0);
  const dz = (p1[11] ?? 0) - (p2[11] ?? 0);
  const transM = Math.hypot(dx, dy, dz);

  // R = P · Qᵀ → angle = arccos((trace(R) - 1) / 2). With both
  // matrices stored row-major, the trace simplifies to a per-element
  // dot product over the rotation 3×3 (rows 0..2, cols 0..2).
  const trace =
    (p1[0] ?? 0) * (p2[0] ?? 0) +
    (p1[1] ?? 0) * (p2[1] ?? 0) +
    (p1[2] ?? 0) * (p2[2] ?? 0) +
    (p1[4] ?? 0) * (p2[4] ?? 0) +
    (p1[5] ?? 0) * (p2[5] ?? 0) +
    (p1[6] ?? 0) * (p2[6] ?? 0) +
    (p1[8] ?? 0) * (p2[8] ?? 0) +
    (p1[9] ?? 0) * (p2[9] ?? 0) +
    (p1[10] ?? 0) * (p2[10] ?? 0);
  let cos = (trace - 1) / 2;
  if (cos > 1) cos = 1;
  if (cos < -1) cos = -1;
  const angRad = Math.acos(cos);

  // Translation in mm + rotation in degrees, summed.
  return transM * 1000 + (angRad * 180) / Math.PI;
}

function radToDeg(rad: number): number {
  return (rad * 180) / Math.PI;
}
