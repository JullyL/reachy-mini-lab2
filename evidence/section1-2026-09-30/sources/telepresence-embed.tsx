/**
 * Embedded telepresence app entry point - mounted by the dispatcher
 * when the URL has `?embedded=1` (i.e. we're inside the host's iframe).
 *
 * Telepresence is a single-screen experience: once the host has
 * brought the session up, we render the joystick + video + audio
 * UI directly. The host stays responsible for sign-in, robot
 * picking, connecting overlays, and the leave-spinner.
 *
 * SDK state derivation
 * ────────────────────
 * `TelepresenceView` was designed against a fat `useReachyMini`
 * hook that exposed `isLive`, `isAwake`, mute booleans, and live
 * media streams. The host now owns the connection lifecycle, so
 * this file derives the same shape from the live handle:
 *  - `isLive` / `isAwake`: true at handle resolution time
 *    (`connectToHost()` resolves AFTER startSession + ensureAwake).
 *    Updated on `sessionStopped` / `motorStateChanged` events.
 *  - mute booleans: read from `reachy.micMuted` / `reachy.audioMuted`,
 *    refreshed when our setters fire (the SDK is sync on these).
 *  - media streams: pulled from `handle.media` (NOT `reachy._pc` /
 *    `reachy._micStream` / `reachy.attachVideo`). The host's
 *    `RobotMedia` surface replays the WebRTC tracks captured during
 *    boot, so this late-mounting React tree sees the camera + audio
 *    immediately rather than waiting for a one-shot `videoTrack`
 *    event that has already fired.
 *
 * Local microphone capture
 * ────────────────────────
 * The SDK no longer captures the operator's mic itself (the
 * vendored 1.8.x revision wires a 0-gain oscillator as a
 * placeholder on the WebRTC audio sender). The operator → robot
 * audio path is therefore owned by this app via `local-mic.ts`:
 * the first "Mic on" tap calls `getUserMedia({audio:true})` and
 * `replaceTrack()`s the real mic onto `reachy._pc`'s audio sender.
 * See `local-mic.ts` for the full rationale and the iOS / Android
 * gotchas.
 */
import { StrictMode, useCallback, useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { CssBaseline, ThemeProvider } from '@mui/material';

import { connectToHost, type ConnectedHandle } from '@pollen-robotics/reachy-mini-sdk/host/embed';

import TelepresenceView from './components/TelepresenceView';
import { attachLocalMic, type LocalMicHandle } from './local-mic';
import { darkTheme, lightTheme } from './theme';

interface AppConfig {
  /** Optional preset head pitch (degrees) to apply on mount. */
  headPitch?: number;
}

async function bootstrap(): Promise<void> {
  const handle = await connectToHost<AppConfig>();
  const container = document.getElementById('root');
  if (!container) throw new Error('Missing #root element');
  createRoot(container).render(
    <StrictMode>
      <EmbedRoot handle={handle} />
    </StrictMode>,
  );
}

interface EmbedRootProps {
  handle: ConnectedHandle<AppConfig>;
}

function EmbedRoot({ handle }: EmbedRootProps) {
  const [theme, setTheme] = useState<'dark' | 'light'>(handle.theme);

  useEffect(() => {
    const unsub = handle.onThemeChange((t) => setTheme(t));
    return () => unsub();
  }, [handle]);

  const muiTheme = theme === 'dark' ? darkTheme : lightTheme;

  return (
    <ThemeProvider theme={muiTheme}>
      <CssBaseline />
      <TelepresenceShell handle={handle} />
    </ThemeProvider>
  );
}

function TelepresenceShell({
  handle,
}: {
  handle: ConnectedHandle<AppConfig>;
}) {
  const { reachy, media } = handle;
  const [isLive, setIsLive] = useState(true);
  const [isAwake, setIsAwake] = useState(true);
  // Initial mute is the SDK's default (`true` - the user must tap
  // "Mic on" before any audio reaches the robot). The toggle below
  // both unmutes the SDK flag AND lazily captures the phone mic on
  // first unmute.
  const [micMuted, setMicMuted] = useState(reachy.micMuted);
  const [audioMuted, setAudioMuted] = useState(reachy.audioMuted);
  // Real mic stream (from `getUserMedia`), captured on first
  // "Mic on" tap and swapped onto the SDK's audio sender. Until
  // then we leave it `null` so the spectrum reads as "channel
  // dormant" instead of pretending to show audio from a silent
  // oscillator. See `local-mic.ts` for the full rationale.
  const [localMicStream, setLocalMicStream] = useState<MediaStream | null>(
    null,
  );
  // Stash the live handle in a ref so unmount / leave teardown
  // can call `dispose()` without a state read race.
  const localMicRef = useRef<LocalMicHandle | null>(null);

  useEffect(() => {
    const onSessionStopped = () => setIsLive(false);
    const onMotor = (e: Event) => {
      const detail = (e as CustomEvent<{ awake: boolean }>).detail;
      if (detail && typeof detail.awake === 'boolean') setIsAwake(detail.awake);
    };
    reachy.addEventListener('sessionStopped', onSessionStopped);
    reachy.addEventListener('motorStateChanged', onMotor);
    return () => {
      reachy.removeEventListener('sessionStopped', onSessionStopped);
      reachy.removeEventListener('motorStateChanged', onMotor);
    };
  }, [reachy]);

  // Release the OS mic claim (and the orange iOS indicator) the
  // moment the host asks us to leave, BEFORE the SDK tears the
  // peer connection down. `onLeave` fires once on `host:leaving`
  // or `pagehide`. We also stop the track on React unmount as a
  // belt-and-braces fallback for standalone (non-iframe) dev.
  useEffect(() => {
    const detach = handle.onLeave(async () => {
      const mic = localMicRef.current;
      if (!mic) return;
      localMicRef.current = null;
      await mic.dispose();
    });
    return () => {
      detach();
      const mic = localMicRef.current;
      if (!mic) return;
      localMicRef.current = null;
      void mic.dispose();
    };
  }, [handle]);

  const handleSetMicMuted = useCallback(
    async (muted: boolean): Promise<void> => {
      // Lazy mic capture. We can only call `getUserMedia` inside a
      // user-gesture frame on iOS/WKWebView - the "Mic on" tap is
      // that gesture. Doing it at boot would silently never prompt.
      if (!muted && !localMicRef.current) {
        try {
          const mic = await attachLocalMic(reachy, { initiallyMuted: false });
          localMicRef.current = mic;
          setLocalMicStream(mic.stream);
        } catch (err) {
          // Keep the channel reading as "off" so the user can
          // retry. Surfaced via the AudioControlCard's existing
          // mute styling - no extra UI needed for the v1 fix.
          console.warn('[telepresence] failed to capture local mic:', err);
          setMicMuted(true);
          // Best-effort: keep the SDK flag aligned so its own
          // bookkeeping (e.g. status pill) doesn't drift.
          reachy.setMicMuted(true);
          return;
        }
      } else if (localMicRef.current) {
        // Already captured - just toggle the real track. We don't
        // tear the stream down on mute so the user can re-enable
        // without a second permission prompt.
        localMicRef.current.setMuted(muted);
      }
      // Keep the SDK flag mirrored so any consumer reading
      // `reachy.micMuted` (status pills, video overlay) stays in
      // sync. Functionally this only toggles the orphaned
      // oscillator track now, which is harmless.
      reachy.setMicMuted(muted);
      setMicMuted(reachy.micMuted);
    },
    [reachy],
  );

  const handleSetAudioMuted = (m: boolean) => {
    reachy.setAudioMuted(m);
    setAudioMuted(reachy.audioMuted);
  };

  return (
    <TelepresenceView
      robot={reachy}
      isLive={isLive}
      isAwake={isAwake}
      micMuted={micMuted}
      audioMuted={audioMuted}
      attachVideo={media.attachVideo}
      // Prefer the real `getUserMedia` stream once captured so the
      // spectrum bars actually shimmer when the operator speaks.
      // Falls back to the SDK's placeholder (`media.micStream`,
      // a 0-gain oscillator) so the row isn't blank before the
      // first "Mic on" tap.
      micStream={localMicStream ?? media.micStream}
      robotStream={media.robotStream}
      onSetMicMuted={(m) => {
        void handleSetMicMuted(m);
      }}
      onSetAudioMuted={handleSetAudioMuted}
    />
  );
}

void bootstrap().catch((err) => {
  console.error('[telepresence/embed] bootstrap failed', err);
  try {
    window.parent.postMessage(
      {
        source: 'reachy-mini',
        type: 'embed:error',
        version: 1,
        message: err instanceof Error ? err.message : String(err),
        fatal: true,
      },
      window.location.origin,
    );
  } catch {
    /* swallow */
  }
});
