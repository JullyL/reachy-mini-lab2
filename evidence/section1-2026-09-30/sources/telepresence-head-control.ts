/**
 * Head + body velocity controller (tank-style).
 *
 * Translates the joystick deflection (`[-1, 1]^2`, mutable ref) into a
 * stream of `setHeadRpyDeg` + `setBodyYawDeg` commands at 20 Hz.
 *
 * Yaw model - single WORLD-yaw integrator
 * ───────────────────────────────────────
 * The joystick X axis integrates ONE quantity: `totalYawRef`, the head's
 * yaw in the WORLD frame, clamped to `±TOTAL_YAW_LIMIT_DEG`. The head /
 * body split is then *derived* from it every tick:
 *
 *   headRel = clamp(totalYaw, ±HEAD_YAW_LIMIT_DEG)   // head saturates first
 *   body    = totalYaw - headRel                     // body takes the overflow
 *
 * This makes the motion fully *reversible*: the camera's world heading is
 * directly proportional to the joystick deflection both ways. Pushing out,
 * the head rotates until it saturates, then the body spills over. Coming
 * back, the body unwinds first while the head stays pinned, then the head
 * recentres - no "head whips across while the body stays rotated" artefact
 * that the old saturation-gated spill produced (which left the head and
 * body visibly out of sync when the user let go mid-return).
 *
 * Sign convention (see constants.ts header): push right (x > 0) → look
 * right → yaw DECREASES; push up (y < 0) → look up → pitch DECREASES.
 *
 * The hook returns a `recenter()` callback that eases head + body back to
 * neutral and resets the internal model so it stays in lock-step with the
 * robot (used by the on-screen "recenter" button and on unmount).
 */
import { useCallback, useEffect, useRef, useState } from 'react';

import {
  CONTROL_TICK_MS,
  HEAD_PITCH_MAX_DEG,
  HEAD_PITCH_MIN_DEG,
  HEAD_YAW_LIMIT_DEG,
  MAX_BODY_YAW_DEG_PER_SEC,
  MAX_PITCH_DEG_PER_SEC,
  MAX_YAW_DEG_PER_SEC,
  OFF_CENTER_THRESHOLD_DEG,
  RECENTER_DURATION_MS,
  RECENTER_FRAMES_PER_SEC,
  TARGET_DELTA_THRESHOLD_DEG,
  TOTAL_YAW_LIMIT_DEG,
} from './constants';

export type HeadCommand = (
  rollDeg: number,
  pitchDeg: number,
  yawDeg: number,
) => boolean;
export type BodyYawCommand = (yawDeg: number) => boolean;

export interface UseHeadVelocityControlOptions {
  deflectionRef: React.RefObject<{ x: number; y: number }>;
  setHeadRpyDeg: HeadCommand;
  setBodyYawDeg: BodyYawCommand;
  enabled: boolean;
}

export interface UseHeadVelocityControlResult {
  /**
   * Ease head + body back to neutral (world yaw 0, pitch 0) over
   * `RECENTER_DURATION_MS` and reset the internal model to 0. Safe to
   * call repeatedly; a no-op when already centred. Aborts gracefully if
   * the user grabs the joystick mid-animation.
   */
  recenter: () => void;
  /**
   * `true` when the head/body has drifted past `OFF_CENTER_THRESHOLD_DEG`
   * from neutral. Drives the visibility of the recenter affordance.
   * Updated only on transitions, not every control tick.
   */
  isOffCenter: boolean;
}

function quadratic(value: number): number {
  return value * Math.abs(value);
}

function clamp(value: number, min: number, max: number): number {
  if (value < min) return min;
  if (value > max) return max;
  return value;
}

/** Head-on-base yaw for a given world yaw (head saturates first). */
function headRelFor(totalYaw: number): number {
  return clamp(totalYaw, -HEAD_YAW_LIMIT_DEG, HEAD_YAW_LIMIT_DEG);
}

export function useHeadVelocityControl({
  deflectionRef,
  setHeadRpyDeg,
  setBodyYawDeg,
  enabled,
}: UseHeadVelocityControlOptions): UseHeadVelocityControlResult {
  const totalYawRef = useRef(0);
  const pitchRef = useRef(0);
  const recenteringRef = useRef(false);
  const lastCommandedHeadYawWorldRef = useRef(Number.POSITIVE_INFINITY);
  const lastCommandedPitchRef = useRef(Number.POSITIVE_INFINITY);
  const lastCommandedBodyYawRef = useRef(Number.POSITIVE_INFINITY);

  const [isOffCenter, setIsOffCenter] = useState(false);
  const offCenterRef = useRef(false);
  // Flip the React state only when the offset crosses the threshold, so
  // the 20 Hz control loop doesn't trigger a render every tick.
  const syncOffCenter = useCallback((totalYaw: number, pitch: number) => {
    const off =
      Math.abs(totalYaw) > OFF_CENTER_THRESHOLD_DEG ||
      Math.abs(pitch) > OFF_CENTER_THRESHOLD_DEG;
    if (off !== offCenterRef.current) {
      offCenterRef.current = off;
      setIsOffCenter(off);
    }
  }, []);

  const setHeadRpyDegRef = useRef(setHeadRpyDeg);
  const setBodyYawDegRef = useRef(setBodyYawDeg);
  useEffect(() => {
    setHeadRpyDegRef.current = setHeadRpyDeg;
  }, [setHeadRpyDeg]);
  useEffect(() => {
    setBodyYawDegRef.current = setBodyYawDeg;
  }, [setBodyYawDeg]);

  const recenter = useCallback(() => {
    if (recenteringRef.current) return;

    const startTotalYaw = totalYawRef.current;
    const startPitch = pitchRef.current;
    if (Math.abs(startTotalYaw) < 0.5 && Math.abs(startPitch) < 0.5) {
      // Already centred - snap the model to exact zero and bail.
      totalYawRef.current = 0;
      pitchRef.current = 0;
      syncOffCenter(0, 0);
      return;
    }

    recenteringRef.current = true;
    const headSetter = setHeadRpyDegRef.current;
    const bodySetter = setBodyYawDegRef.current;
    const startTime = performance.now();
    const frameInterval = 1000 / RECENTER_FRAMES_PER_SEC;
    let lastFrameTime = 0;

    const finish = () => {
      totalYawRef.current = 0;
      pitchRef.current = 0;
      lastCommandedHeadYawWorldRef.current = 0;
      lastCommandedPitchRef.current = 0;
      lastCommandedBodyYawRef.current = 0;
      recenteringRef.current = false;
      syncOffCenter(0, 0);
      bodySetter(0);
      headSetter(0, 0, 0);
    };

    const raf = (now: number) => {
      // The control tick clears this flag if the user grabs the
      // joystick mid-animation; bail and let live control take over
      // from wherever the ease left the model.
      if (!recenteringRef.current) return;

      if (now - lastFrameTime < frameInterval) {
        window.requestAnimationFrame(raf);
        return;
      }
      lastFrameTime = now;

      const elapsed = now - startTime;
      const t = Math.min(1, elapsed / RECENTER_DURATION_MS);
      if (t >= 1) {
        finish();
        return;
      }

      const eased = 1 - Math.pow(1 - t, 3);
      const totalYaw = startTotalYaw * (1 - eased);
      const pitch = startPitch * (1 - eased);
      const body = totalYaw - headRelFor(totalYaw);

      totalYawRef.current = totalYaw;
      pitchRef.current = pitch;
      lastCommandedHeadYawWorldRef.current = totalYaw;
      lastCommandedPitchRef.current = pitch;
      lastCommandedBodyYawRef.current = body;

      bodySetter(body);
      headSetter(0, pitch, totalYaw);

      window.requestAnimationFrame(raf);
    };
    window.requestAnimationFrame(raf);
  }, [syncOffCenter]);

  useEffect(() => {
    if (!enabled) {
      totalYawRef.current = 0;
      pitchRef.current = 0;
      recenteringRef.current = false;
      lastCommandedHeadYawWorldRef.current = Number.POSITIVE_INFINITY;
      lastCommandedPitchRef.current = Number.POSITIVE_INFINITY;
      lastCommandedBodyYawRef.current = Number.POSITIVE_INFINITY;
      syncOffCenter(0, 0);
      return undefined;
    }

    const dtSec = CONTROL_TICK_MS / 1000;

    const tick = () => {
      const def = deflectionRef.current;
      if (!def) return;

      // If a recenter animation is running, only the user grabbing the
      // joystick (non-trivial deflection) cancels it; otherwise skip the
      // tick so we don't fight the ease.
      if (recenteringRef.current) {
        if (Math.hypot(def.x, def.y) > 0.01) {
          recenteringRef.current = false;
        } else {
          return;
        }
      }

      const curveX = quadratic(def.x);
      const curveY = quadratic(def.y);

      // World-yaw integrator: the head slice runs at the head speed cap,
      // the body-spill slice at the (slower) body speed cap, so the feel
      // of "the whole robot swivels" once the head saturates is preserved.
      const inHeadRange = Math.abs(totalYawRef.current) < HEAD_YAW_LIMIT_DEG;
      const yawSpeed = inHeadRange
        ? MAX_YAW_DEG_PER_SEC
        : MAX_BODY_YAW_DEG_PER_SEC;
      const totalYawDelta = -curveX * yawSpeed * dtSec;
      const pitchDelta = curveY * MAX_PITCH_DEG_PER_SEC * dtSec;

      const nextTotalYaw = clamp(
        totalYawRef.current + totalYawDelta,
        -TOTAL_YAW_LIMIT_DEG,
        TOTAL_YAW_LIMIT_DEG,
      );
      const nextPitch = clamp(
        pitchRef.current + pitchDelta,
        HEAD_PITCH_MIN_DEG,
        HEAD_PITCH_MAX_DEG,
      );

      totalYawRef.current = nextTotalYaw;
      pitchRef.current = nextPitch;
      syncOffCenter(nextTotalYaw, nextPitch);

      // Derive the head/body split from the single world-yaw target.
      const nextHeadYawWorld = nextTotalYaw;
      const nextBodyYaw = nextTotalYaw - headRelFor(nextTotalYaw);

      const headYawWorldDiff = Math.abs(
        nextHeadYawWorld - lastCommandedHeadYawWorldRef.current,
      );
      const pitchDiff = Math.abs(nextPitch - lastCommandedPitchRef.current);
      const bodyYawDiff = Math.abs(
        nextBodyYaw - lastCommandedBodyYawRef.current,
      );

      const bodyChanged = bodyYawDiff >= TARGET_DELTA_THRESHOLD_DEG;
      const headChanged =
        headYawWorldDiff >= TARGET_DELTA_THRESHOLD_DEG ||
        pitchDiff >= TARGET_DELTA_THRESHOLD_DEG;

      if (bodyChanged) {
        lastCommandedBodyYawRef.current = nextBodyYaw;
        setBodyYawDegRef.current(nextBodyYaw);
      }
      if (headChanged) {
        lastCommandedHeadYawWorldRef.current = nextHeadYawWorld;
        lastCommandedPitchRef.current = nextPitch;
        setHeadRpyDegRef.current(0, nextPitch, nextHeadYawWorld);
      }
    };

    const interval = window.setInterval(tick, CONTROL_TICK_MS);
    return () => {
      window.clearInterval(interval);
    };
  }, [enabled, deflectionRef, syncOffCenter]);

  // Ease back to neutral on unmount (leaving the live view).
  useEffect(() => {
    return () => {
      recenter();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return { recenter, isOffCenter };
}
