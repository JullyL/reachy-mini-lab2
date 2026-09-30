# Commands and evidence provenance

All commands run from `/Users/pandora2/Documents/GitHub/reachy-mini-lab2` on the Mac unless a separate checkout is stated. Activate `.venv` first. No physical movement command was executed. The complete operational sequence is in [SECTION1_MAC.md](../../docs/SECTION1_MAC.md).

## Executed validation and analysis

```sh
.venv/bin/python scripts/verify_sources.py
.venv/bin/python -m pytest -q
.venv/bin/python scripts/validate_simulation.py --audio-device 2 --commissioning --out evidence/section1-2026-09-30/simulation
.venv/bin/python scripts/validate_simulation.py --audio-device 2 --commissioning --out evidence/section1-2026-09-30/recorded-simulation
MPLCONFIGDIR=/tmp/reachy-plots .venv/bin/python scripts/simulation_evidence.py --runs evidence/section1-2026-09-30/recorded-simulation --frames /tmp/section1-live-frames --out evidence/section1-2026-09-30/media
```

These are completed output directories; use new names for another run. Each validator-generated `*-command.json` records the exact absolute subprocess argv, cwd and exit code; matching `.txt` and UUID `.jsonl` files preserve output and measurements. The serial pytest result supersedes the explicitly retained controller-busy attempt. The first encoder summary failed on insufficient early-stop samples; the fixed final encoder pass succeeded.

## Simulator and Telepresence settings

Greeting capture used the live viewer, no media, `--record-dir /tmp/section1-live-frames`; Telepresence used the live viewer, `--media --video-only --log-level INFO`, unique robot name `lab2-simulation`, and `/tmp/section1-telepresence-live`. `scripts/simulate.py` makes `--sim`, no dataset preload and no sleep-on-stop unconditional. Capture used 640×480, a 15 fps target, external camera distance 0.8, azimuth 160°, elevation −20°, lookat [0, 0, 0.15]. Actual frame intervals and simulator times are in each capture receipt. The recording duration flag only bounds the observer, not the trial.

To repeat in fresh directories:

```sh
.venv/bin/mjpython scripts/simulate.py --viewer --record-dir /tmp/greeting-live-NEW --record-seconds 120
# Stop the local daemon after greeting trials. Then start Telepresence separately:
.venv/bin/mjpython scripts/simulate.py --viewer --media --video-only --log-level INFO --record-dir /tmp/telepresence-live-NEW --record-seconds 180
```

The official Telepresence checkout `/tmp/section1-telepresence` was pinned to revision `f33ba997b0c7aee479e8cb113315c912c6124f88`; `npm ci`, `npm run build`, and `npm run dev -- --host 127.0.0.1` succeeded with Node 24.19.0. Actual configured port: 5183. Local motion was not the evidence source. The recorded motion used the official hosted app, normal Hugging Face OAuth, and the verified simulator peer. UI gestures and capture intervals are recorded in `media/Telepresence-events.json`. No credential is retained here. Read-only daemon HTTP feedback was sampled during that session.

The standalone neutral-recovery code is reproduced verbatim as an operational recipe in the Mac guide, with a simulation default; its actual result is in `telepresence/standalone-neutral-recovery.json`. All task daemons and development servers were stopped afterward.

## Re-encoding and integrity

`media/raw-live-frames.tar.gz` retains every original JPEG used by the greeting, Telepresence environment and standalone recovery movies. Archive paths identify the original capture directory. `media/raw-live-frame-sha256.json` checks all 2,093 archived frames. Trial capture JSON identifies exact selected frames and source logs. Telepresence UI PNGs remain in `media/Telepresence-UI-frames/`. Timestamps determine MP4 presentation times; no trajectory reconstruction or synthetic audio is used.

The reusable capture-only CLI was also exercised on three actual captured JPEGs, completed successfully, and its result was decoded separately. It is available for future full-session capture:

```sh
MPLCONFIGDIR=/tmp/reachy-plots .venv/bin/python scripts/simulation_evidence.py --capture-only --frames /tmp/telepresence-live-NEW --out evidence/telepresence-NEW/media
```

`media/video-validation.json` contains decoded counts and durations for every delivered MP4. `package-qa.json` records archive and gallery-link checks. `manifest-sha256.json` covers the evidence files, revised report, operational documents and changed scripts, excluding itself.

## Report preservation

The revised report replaces only the Section 1 OOXML body span. `docx-preservation.json` records identical canonical body elements outside that span and identical other DOCX ZIP members. `document-qa.json` records all-page visual inspection and pixel-identical Section 3 onward after the two-page shift. The source report remains untouched. Render images and PDF are internal QA intermediates, not alternate deliverables.
