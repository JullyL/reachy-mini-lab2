---
title: Telepresence
emoji: 🤖
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 8080
pinned: false
hf_oauth: true
short_description: Control your robot from anywhere and see what it sees.
tags:
  - reachy_mini
  - reachy_mini_js_app
---

# Telepresence

A focused, mobile-first webapp that turns a Reachy Mini robot into a live
telepresence terminal:

- **Live camera feed** from the robot, 4:3, edge-to-edge.
- **Bidirectional audio** - your microphone goes out the robot's
  speakers, the robot's microphone comes back to your speakers.
- **On-screen joystick** to steer the head (yaw + pitch) and the base
  (body yaw spills over once the head reaches its mechanical edge).
- **No AI in the loop** - pure operator-to-robot link.

UX inspired by [`reachy_mini_mobile_app`](https://github.com/pollen-robotics/reachy_mini_mobile_app)
(MUI theme, joystick widget, audio card), audio pipeline borrowed from
[`reachy_mini_minimal_conversation`](../reachy_mini_minimal_conversation).

## Audio routing (operator ↔ robot)

```
 ┌──────────┐  getUserMedia + replaceTrack   ┌────────────┐  robot sender
 │ Browser  │ ──────────────────────────────►│  ReachyMini│ ──────────────► robot speakers
 │ (this)   │                                │   SDK PC   │
 │          │ ◄───────────────────────────── │            │ ◄────────────── robot mic
 └──────────┘    <video> srcObject           └────────────┘  robot receiver
```

The robot → operator path is "free": `attachVideo()` on a `<video>`
element pulls *both* video AND audio of the robot stream, and
unmuting the `<video>` (via `setAudioMuted(false)`) is enough.

The operator → robot path is owned by THIS app, not the SDK. The
SDK creates a silent 0-gain oscillator as a placeholder track on
the WebRTC audio sender so the `sendrecv` audio mline survives
SDP negotiation, but it never calls `getUserMedia` - the comment
in `reachy-mini.js` is explicit:

> `enableMicrophone` is intentionally NOT stored: the SDK no longer
> calls getUserMedia […]. Apps that still pass it for backward
> compatibility have their value silently ignored.

So `src/local-mic.ts`:

1. On the first "Mic on" tap (must be a user gesture for iOS),
   calls `navigator.mediaDevices.getUserMedia({audio:true})`.
2. Locates the audio `RTCRtpSender` on `reachy._pc` and calls
   `sender.replaceTrack(micTrack)` to swap the silent placeholder
   for the real mic. No SDP renegotiation - the encoder is
   re-routed transparently.
3. Subsequent mute toggles flip `micTrack.enabled` on the real
   track (the SDK's `setMicMuted()` now only touches the orphaned
   oscillator and is mirrored only to keep the `reachy.micMuted`
   flag in sync for UI consumers).
4. On `handle.onLeave` we stop the track to release the OS mic
   claim (and the orange iOS status-bar indicator).

Same pattern as `reachy_mini_minimal_conversation`'s
`routeOpenaiToRobot()` - the difference is the source: phone mic
here, OpenAI's WebRTC output there.

## Stack

- **React 19** + **TypeScript** + **Vite 7**
- **MUI 7** with the same theme tokens as `reachy_mini_mobile_app`
- **Reachy Mini JS SDK** loaded from jsDelivr (pinned to
  `feat/sdk-mobile-shell-handoff` for iframe-handoff + iOS ICE fixes)
- **Docker** for HF Space deployment (multi-stage build, tiny Node
  static server in `server.mjs` that injects HF OAuth env vars)

## Prerequisites

- Node.js 18+
- A Hugging Face account (for robot signaling - HF OAuth)
- A Reachy Mini robot online on the signaling server

### Hugging Face OAuth

Deployed on a Space, OAuth "just works" - HF auto-provisions an OAuth
app from the `hf_oauth: true` flag in this README and injects the
client ID into the page at serve time.

For **local dev** you have two options. Pick the one that matches
what you're working on:

#### Option A · Personal access token (recommended for most dev)

Skips the OAuth dance entirely. The dev server seeds the SDK's
auth cache from env vars at boot, so `authenticate()` resolves
without a redirect.

1. Create a token at <https://huggingface.co/settings/tokens>
   (read scope is enough).
2. `cp .env.example .env.local`, then fill in:

   ```
   VITE_HF_TOKEN=hf_xxx…
   VITE_HF_USERNAME=your-handle
   ```

3. Restart `npm run dev`. You'll be signed in on page load.

`.env.local` is gitignored. Never commit the token.

#### Option B · OAuth client ID (mirrors the production flow)

Use this when you specifically want to test the OAuth redirect
flow (e.g. you're touching the login / logout paths).

1. Go to <https://huggingface.co/settings/applications/new>.
2. Fill in:
   - **App name:** `Reachy Mini Telepresence (local)`.
   - **Homepage URL:** `http://localhost:5173`
   - **Scopes:** check at least `openid` and `profile`.
   - **Redirect URIs:** `http://localhost:5173`
3. Click **Create application**. Copy the **Client ID**.
4. Make the dev server pick it up - pick one:

   - `.env.local`: `VITE_HF_OAUTH_CLIENT_ID=…`, restart
     `npm run dev`.
   - Or open the app, hit the gear icon, paste into Settings.

The signed-out screen on `localhost` walks through option B
inline when no client ID is configured anywhere.

## Run

```bash
npm install
npm run dev
# → http://localhost:5173
```

Three taps to be live:

1. **Sign in with Hugging Face** (OAuth redirect, only once).
2. The app auto-connects to the central signaling server, lists
   available robots, and auto-picks the only one online (or shows a
   picker when several are visible).
3. The camera + joystick + audio card appear. Tap the **mic** /
   **speaker** buttons in the audio card to start streaming both
   ways - browsers require a user gesture before unmuting media.

## Build

```bash
npm run build
npm run preview
# → http://localhost:8080
```

This produces a static `dist/` folder. Locally, `vite preview` serves
it. On a Hugging Face Space, the `Dockerfile` runs this same build and
`server.mjs` serves the output (see below). `dist/` is gitignored and
never committed - HF rebuilds it from source on every push.

## Deploy to a Hugging Face Space

```bash
git remote add space git@hf.co:spaces/<your-username>/telepresence
git push space main
```

The Space is a **Docker** Space. Its frontmatter pins:

- `sdk: docker` + `app_port: 8080` - HF builds the `Dockerfile` on
  every push and serves the container. Docker builds are not gated
  (unlike static `app_build_command`, which HF now restricts to paid
  Team/Enterprise plans).
- `hf_oauth: true` - HF provisions an OAuth app and exposes its config
  as **environment variables** to the container.

Because `window.huggingface.variables` is injected natively only on
static Spaces, `server.mjs` re-creates it: at request time it splices a
`window.huggingface` bootstrap script into `index.html` from the
`OAUTH_CLIENT_ID` / `OAUTH_SCOPES` / `OPENID_PROVIDER_URL` /
`SPACE_HOST` env vars, so the SDK's `authenticate()` behaves exactly
like on a static Space. `OAUTH_CLIENT_SECRET` is never exposed to the
browser.

The Space must be **public**. Private Spaces can't be loaded in HF's
iframe wrapper because the `hf_jwt` auth cookie is SameSite-blocked
cross-origin.

## URL parameters (host iframe)

When this Space is embedded in another shell (e.g. the Reachy Mini
mobile app), the host can pass:

- `?theme=dark|light` - palette override; postMessage `{ source:
  'reachy-mini-shell', kind: 'theme', theme: 'dark'|'light' }`
  also works for runtime toggles.
- `?robot_peer_id=<id>` - skip the robot picker, jump straight to
  this peer once the central reports it online.
- `?signaling_url=<url>` - point the SDK at a custom signaling
  central (staging / self-hosted) without rebuilding.
- `#hf_token=<jwt>&hf_username=<handle>&hf_token_expires=<iso>` -
  fragment-only token hand-off (never sent over HTTP, kept in
  `sessionStorage` so the SDK's `authenticate()` picks it up).

## Limitations

- Bidirectional audio requires `micSupported: true` on the robot
  (recent daemon). Older daemons advertise no `sendrecv` audio
  mline, so the SDK creates no audio sender, so the local-mic
  `replaceTrack()` has nothing to swap onto. The camera + joystick
  still work; the mic toggle will surface a console warning on the
  first "Mic on" tap and stay off.
- The mic permission prompt only appears on the first "Mic on"
  tap (must be a user-gesture frame for iOS / WKWebView). If the
  user denies the prompt, the toggle snaps back to "off"; tap
  again to retry.
- The HF OAuth client ID is loaded from the HF runtime in production
  and from `VITE_HF_OAUTH_CLIENT_ID` / `localStorage` in dev. There
  is no shared backend.
- This app is read-only on the robot's motor envelope - it never
  triggers wake-up / sleep trajectories. The robot daemon's own
  policy decides what state it starts in.

## License

MIT for this glue code. The underlying SDKs keep their respective
licenses - see the pollen-robotics project.
