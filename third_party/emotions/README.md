---
title: Emotions
emoji: 💜
colorFrom: yellow
colorTo: red
sdk: docker
app_port: 8080
pinned: false
hf_oauth: true
short_description: Play expressive emotions on your robot.
tags:
  - reachy_mini
  - reachy_mini_js_app
---

# Emotions

A focused, mobile-first webapp that lets you browse and play the full
Reachy Mini **emotion library** as a Plutchik-inspired wheel:

- **Plutchik wheel** with 8 colored sectors (Joy, Trust, Fear,
  Surprise, Sadness, Disgust, Anger, Anticipation) split into 3
  intensity rings.
- **Tap a sector** → bottom sheet with all the moves of that family,
  emoji + duration + description.
- **Tap a card** → the trajectory streams to the robot in real time
  (50-100 Hz `set_full_target` over the WebRTC data channel).
- **Center dice** → spin a random emotion across the whole wheel.
- **Companion sounds** play in the browser via Web Audio in sync with
  the move.
- **No AI in the loop** - pure dataset playback.

UX inspired by [`reachy_mini_mobile_app`](https://github.com/pollen-robotics/reachy_mini_mobile_app)
(MUI theme, host-shell embed protocol) and the desktop dashboard's
emotion wheel + dice random spin.

## How playback works

The 79 emotions live as plain JSON files in
[`pollen-robotics/reachy-mini-emotions-library`](https://huggingface.co/datasets/pollen-robotics/reachy-mini-emotions-library).
Each file contains `time[]` + `set_target_data[{ head: 4x4, antennas:
[r, l], body_yaw }]` frames sampled at 50-100 Hz.

This Space:

1. Fetches the JSON straight from the HF CDN (CORS-open) and caches it
   in `localStorage` so a second play is instant.
2. Walks the trajectory in a `requestAnimationFrame` loop, sending
   `set_full_target` over the SDK's data channel for each frame.
3. Plays the companion `.ogg` (when present) via Web Audio in
   parallel.

No daemon change is needed: the daemon already supports
`set_full_target` natively and interpolates between frames if the
network jitters. If a future daemon adds a `play_recorded_move` data
channel command we can switch to it transparently.

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

Three taps to play your first move:

1. **Sign in with Hugging Face** (OAuth redirect, only once).
2. The app auto-connects to the central signaling server, lists
   available robots, and auto-picks the only one online (or shows a
   picker when several are visible).
3. The Plutchik wheel appears. Tap a sector → bottom sheet → tap an
   emotion. Or tap the dice at the center for a random pick.

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
git remote add space git@hf.co:spaces/<your-username>/emotions
git push space main
```

The Space is a **Docker** Space. Its frontmatter pins:

- `sdk: docker` + `app_port: 8080` - HF builds the `Dockerfile` on
  every push and serves the container. Docker builds are not gated
  (unlike static `app_build_command`, which HF now restricts to paid
  Team/Enterprise plans and which left this Space stuck in
  `CONFIG_ERROR`).
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

- Mobile-first by design - the wheel scales to phone viewports, not
  to wide desktop displays. Same trade-off as the legacy mobile
  shell embed.
- Trajectory streaming is best-effort: a transient WebRTC stall will
  drop a few frames. The daemon interpolates, so the move keeps
  going but is briefly less smooth.
- The HF OAuth client ID is loaded from the HF runtime in production
  and from `VITE_HF_OAUTH_CLIENT_ID` / `localStorage` in dev. There
  is no shared backend.

## License

MIT for this glue code. The underlying SDKs keep their respective
licenses - see the pollen-robotics project.
