/**
 * Single entry point for both the host shell and the embedded app.
 * See `reachy_mini_emotions/src/dispatch.ts` for the shared rationale.
 *
 * Telepresence-specific: the host's iframe needs microphone access
 * (the audio chunks downstream into the WebRTC pipe) and the
 * connection should auto-grant it without prompting twice. We
 * pass `enableMicrophone: true` here so the host's SDK constructor
 * acquires the mic up-front; the embed inherits the resulting
 * stream via the existing SDK session.
 *
 * SDK bootstrapping
 * ─────────────────
 * The host shell and the embed client both consume `window.ReachyMini`
 * (constructor injected by the SDK). Historically that global was set
 * by a `<script type="module">` tag in `index.html` pointing at a
 * jsdelivr CDN URL; this file now statically imports the SDK from
 * the `@pollen-robotics/reachy-mini-sdk` npm package and assigns the
 * constructor onto `window` synchronously, BEFORE the dynamic import
 * of the host module resolves. We still dispatch the `reachymini:ready`
 * event so the embed's wait loop takes its fast path immediately.
 */

import { ReachyMini } from '@pollen-robotics/reachy-mini-sdk';

(window as unknown as { ReachyMini: typeof ReachyMini }).ReachyMini = ReachyMini;
window.dispatchEvent(new Event('reachymini:ready'));

const params = new URLSearchParams(window.location.search);
// Accept both `?embedded=1` (current) and the transient `?embed=1`
// used by an intermediate host refactor, so this app boots correctly
// against any combination of mobile build / vendored host dist.
const isEmbed =
  params.get('embedded') === '1' || params.get('embed') === '1';

if (isEmbed) {
  void import('./embed');
} else {
  void import('@pollen-robotics/reachy-mini-sdk/host/auto').then(({ mountHost }) => {
    mountHost({
      appName: 'Telepresence',
      appIconUrl: '/icon.svg',
      appEmoji: '🤖',
      enableMicrophone: true,
      devToken:
        import.meta.env.VITE_HF_TOKEN && import.meta.env.VITE_HF_USERNAME
          ? {
              token: import.meta.env.VITE_HF_TOKEN as string,
              userName: import.meta.env.VITE_HF_USERNAME as string,
            }
          : undefined,
      clientId: import.meta.env.VITE_HF_OAUTH_CLIENT_ID as string | undefined,
    });
  });
}
