/**
 * Head joystick tuning constants - lifted verbatim from
 * `reachy_mini_mobile_app/src/ui/widgets/head-control/constants.ts`.
 *
 * Same hardware = same limits. Read that file's header for the full
 * sign-convention + atan2-wrap rationale; the values below are not
 * tunable without understanding it.
 */

/** Head yaw clamp RELATIVE to the base, ∈ [-LIMIT, +LIMIT]. The daemon
 *  IK enforces |head_yaw_world - body| ≤ 65°; 60° leaves a 5° margin. */
export const HEAD_YAW_LIMIT_DEG = 60;
export const HEAD_PITCH_MAX_DEG = 45.84; // 0.8 rad
export const HEAD_PITCH_MIN_DEG = -45.84; // -0.8 rad

/** Body yaw clamp. Tight enough that
 *  HEAD_YAW_LIMIT_DEG + BODY_YAW_LIMIT_DEG < 180° to avoid the daemon's
 *  atan2 wrap at the extremes. */
export const BODY_YAW_LIMIT_DEG = 115;

/**
 * Total reachable WORLD yaw = head-on-base + body spill. The controller
 * integrates a single world-yaw target into this range and then derives
 * the head/body split from it (head saturates first, body takes the
 * overflow). Kept < 180° so the daemon's atan2 never wraps. */
export const TOTAL_YAW_LIMIT_DEG = HEAD_YAW_LIMIT_DEG + BODY_YAW_LIMIT_DEG;

/** Velocity caps at full joystick deflection (post-quadratic curve). */
export const MAX_YAW_DEG_PER_SEC = 60;
export const MAX_PITCH_DEG_PER_SEC = 40;
export const MAX_BODY_YAW_DEG_PER_SEC = 50;

export const HEAD_YAW_SATURATION_MARGIN_DEG = 0.5;
export const JOYSTICK_DEADZONE = 0.1;

/** Radial deadzone for a physical game-controller stick. Looser than the
 *  touch joystick's: analog sticks rest with more drift than a finger, so
 *  a tighter zone would let a centred stick creep the head. */
export const GAMEPAD_DEADZONE = 0.15;

/** Integration tick + redundant-command threshold. */
export const CONTROL_TICK_MS = 50;
export const TARGET_DELTA_THRESHOLD_DEG = 0.3;

/** Past this world-yaw / pitch offset (deg) the head is considered
 *  "off neutral" and the recenter affordance becomes visible. */
export const OFF_CENTER_THRESHOLD_DEG = 1;

/** Recenter animation on unmount. */
export const RECENTER_DURATION_MS = 600;
export const RECENTER_FRAMES_PER_SEC = 30;

/**
 * Visual dimensions of the joystick widget.
 *
 * Tuned for an OVERLAY context (sits on top of the video feed in the
 * bottom-right corner), so a bit smaller than a centred control card
 * would be. Same ratio as the mobile app (96/32) but slightly larger
 * because the 4:3 video frame has more pixels to spare than the
 * mobile-app camera card.
 */
export const JOYSTICK_RING_DIAMETER_PX = 120;
export const JOYSTICK_THUMB_DIAMETER_PX = 40;
