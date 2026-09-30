/**
 * Live telepresence column.
 *
 *   ┌────────────────────────────────┐
 *   │   <VideoFeed, 4:3>             │
 *   │                                │
 *   │                                │
 *   │                                │  ← puck sits MOSTLY below the
 *   │   ──────────────────────────   │     video (≈ 33 % inside,
 *   │              ╭──╮              │     67 % protruding into the
 *   │              │··│              │     spacer below) - the video
 *   │              ╰──╯              │     stays the dominant surface
 *   │              Drag to look      │  ← micro-label below, in the
 *   │                                │     gap between video & card
 *   │   <AudioControlCard>           │
 *   └────────────────────────────────┘
 *
 * The wrapping `<Box>` is `position: relative` so the joystick can
 * anchor absolutely against the video's bottom edge using a
 * negative `bottom` offset.
 *
 * `pb` on that wrapper reserves vertical space for the part of the
 * joystick that pokes below the video frame, so the protruding
 * puck + label don't collide with the audio card sitting under it.
 */
import { Box, Stack, useTheme } from '@mui/material';

import type { ReachyMiniInstance } from '@/sdk-types';
import HeadJoystick from './joystick/HeadJoystick';
import VideoFeed from './VideoFeed';
import AudioControlCard from './AudioControlCard';

interface TelepresenceViewProps {
  robot: ReachyMiniInstance;
  isLive: boolean;
  /**
   * `true` only after the wake-up trajectory has completed and
   * the Feetech bus is idle. Gates the joystick - sending an RPY
   * command while the daemon is mid-trajectory contends on the
   * serial bus and surfaces as "Motor communication error" from
   * the daemon side.
   */
  isAwake: boolean;
  micMuted: boolean;
  audioMuted: boolean;
  /** Cache-aware attach helper from `useReachyMini`. */
  attachVideo: (el: HTMLVideoElement) => () => void;
  /** Local mic stream (passes through to the VU meters). */
  micStream: MediaStream | null;
  /** Remote robot stream (passes through to the VU meters). */
  robotStream: MediaStream | null;
  onSetMicMuted(muted: boolean): void;
  onSetAudioMuted(muted: boolean): void;
}

/**
 * How far the joystick's BOTTOM EDGE sits below the video frame.
 *
 * Combined with the joystick's total height (puck 120 + gap + label
 * ≈ 140 px), this yields roughly 67 % of the puck protruding below
 * the video and 33 % inside, plus the label sitting fully below in
 * the spacer. The video stays the dominant surface; the puck just
 * "kisses" the bottom edge instead of swallowing it. Tweak in one
 * place.
 */
const JOYSTICK_PROTRUSION_PX = 100;

/** Vertical breathing room reserved under the video for the
 *  protruding joystick + its label before the audio card starts. */
const VIDEO_BOTTOM_SPACER_PX = JOYSTICK_PROTRUSION_PX + 8;

export default function TelepresenceView({
  robot,
  isLive,
  isAwake,
  micMuted,
  audioMuted,
  attachVideo,
  micStream,
  robotStream,
  onSetMicMuted,
  onSetAudioMuted,
}: TelepresenceViewProps) {
  const theme = useTheme();
  return (
    <Box
      sx={{
        // Fill the iframe (or the viewport in standalone) so the
        // flex centering below has a stable axis to anchor against.
        minHeight: '100vh',
        // Vertical centering when the content fits in the viewport;
        // graceful overflow into a normal body scroll when it
        // doesn't (e.g. narrow phone in landscape, or window
        // shrunk vertically on desktop). `min-height` (not
        // `height`) lets the wrapper grow taller than the
        // viewport, which is what triggers the scroll.
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        // A whisker of vertical padding so the video and audio card
        // never sit flush against the edges when the viewport just
        // barely fits.
        py: 2,
      }}
    >
      <Stack
        spacing={2}
        sx={{
          px: 2,
          py: 2,
          // Honour the iOS safe area at the bottom so the audio card
          // doesn't sit under the home-indicator zone in a PWA install.
          pb: `calc(${theme.spacing(2)} + env(safe-area-inset-bottom, 0px))`,
          // Cap the column on desktop so the 4:3 video and audio card
          // don't stretch into a billboard on wide viewports. 560 px
          // gives the video a comfortable 560×420 frame while keeping
          // the joystick puck a thumb-friendly diameter. Mobile is
          // unaffected (mx: auto collapses to 0 when the viewport is
          // narrower).
          maxWidth: 560,
          width: '100%',
          // Prevent the flex parent from shrinking the column when
          // the content is taller than the viewport - we want the
          // overflow to push the body scroll, not compress the
          // video.
          flexShrink: 0,
        }}
      >
      <Box
        sx={{
          position: 'relative',
          // Reserve space for the protruding joystick + label so the
          // audio card below doesn't visually collide with it.
          pb: `${VIDEO_BOTTOM_SPACER_PX}px`,
        }}
      >
        <VideoFeed
          attachVideo={attachVideo}
          micMuted={micMuted}
          audioMuted={audioMuted}
        />
        <HeadJoystick
          setHeadRpyDeg={(roll, pitch, yaw) =>
            robot.setHeadRpyDeg(roll, pitch, yaw)
          }
          setBodyYawDeg={(yawDeg) => robot.setBodyYawDeg(yawDeg)}
          // Gate on BOTH `isLive` (WebRTC up) AND `isAwake` (motor
          // bus is idle, wake trajectory complete). Sending RPY
          // during wake_up / goto_sleep collides on the Feetech
          // bus -> daemon-side "Motor communication error".
          enabled={isLive && isAwake}
          // Status caption while we're streaming-but-not-yet-awake
          // (~1-2 s wake window). Skipped once awake, so the
          // normal "Drag to look" hint comes back.
          disabledLabel={isLive && !isAwake ? 'Waking up…' : undefined}
          sx={{
            position: 'absolute',
            left: '50%',
            transform: 'translateX(-50%)',
            // The joystick BOX (puck + gap + label, ≈ 140 px tall)
            // has its bottom anchored JOYSTICK_PROTRUSION_PX below
            // the video frame. With a 120 px puck at the top of the
            // box and JOYSTICK_PROTRUSION_PX = 100 px, this yields:
            //   - puck top    ≈ video-bottom - 40 px (33 % inside)
            //   - puck bottom ≈ video-bottom + 80 px (67 % out)
            //   - label       ≈ video-bottom + 84 to + 100 px
            //
            // Because `bottom` is measured from the wrapping Box's
            // bottom (which has the extra `pb` spacer), we subtract
            // the spacer to find the value that puts the joystick
            // bottom at `video-bottom + JOYSTICK_PROTRUSION_PX`.
            bottom: `${VIDEO_BOTTOM_SPACER_PX - JOYSTICK_PROTRUSION_PX}px`,
            zIndex: 4,
            // Forbid pointer events from leaking past the joystick
            // to the video element below (which doesn't take
            // pointers today, but might in the future).
            pointerEvents: 'auto',
          }}
        />
      </Box>
      <AudioControlCard
        robot={robot}
        micMuted={micMuted}
        audioMuted={audioMuted}
        micStream={micStream}
        robotStream={robotStream}
        onSetMicMuted={onSetMicMuted}
        onSetAudioMuted={onSetAudioMuted}
      />
      </Stack>
    </Box>
  );
}
