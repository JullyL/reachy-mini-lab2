"""Start only MuJoCo; optional live rendering capture, never log replay."""
import argparse
import json
from pathlib import Path
import sys
from threading import Thread
import time
import gstreamer_libs

gstreamer_libs.setup_python_environment()
from reachy_mini.daemon.app.main import main

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--viewer", action="store_true", help="Show MuJoCo; on macOS launch with .venv/bin/mjpython")
parser.add_argument("--media", action="store_true", help="Enable simulator media for Telepresence; requires HF login for central signaling")
parser.add_argument("--video-only", action="store_true", help="With --media, omit Mac microphone capture; teleoperation/video only")
parser.add_argument("--record-dir", type=Path, help="New directory for timestamped live MuJoCo frames (no acoustic recording)")
parser.add_argument("--record-seconds", type=float, default=90)
parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="WARNING")
args = parser.parse_args()
if args.video_only:
    if not args.media:
        parser.error("--video-only requires --media")
    from reachy_mini.media.media_server import GstMediaServer
    GstMediaServer._build_audio_source = lambda self: None
if args.record_dir:
    args.record_dir.mkdir(parents=True, exist_ok=False)
    # Observe the running simulator's real model/data. No commanded-trajectory
    # reconstruction, physics stepping, or SDK files are changed by this observer.
    import mujoco
    from PIL import Image
    from reachy_mini.daemon.backend.mujoco.backend import MujocoBackend
    original_run = MujocoBackend.run

    def capture(backend):
        try:
            camera = mujoco.MjvCamera()
            camera.type = mujoco.mjtCamera.mjCAMERA_FREE
            camera.distance, camera.azimuth, camera.elevation = .8, 160, -20
            camera.lookat[:] = [0, 0, .15]
            with mujoco.Renderer(backend.model, height=480, width=640) as renderer:
                start, index = time.monotonic(), 0
                with (args.record_dir / "frames.jsonl").open("w") as receipt:
                    while not backend.should_stop.is_set() and time.monotonic()-start < args.record_seconds:
                        tick = time.monotonic()
                        utc = time.time()
                        renderer.update_scene(backend.data, camera=camera)
                        rgb = renderer.render()
                        filename = f"{index:06d}.jpg"
                        Image.fromarray(rgb).save(args.record_dir / filename, quality=90)
                        receipt.write(json.dumps({"file":filename,"utc_s":utc,"monotonic_s":tick,
                            "simulation_time_s":float(backend.data.time),"basis":"live MuJoCo renderer"})+"\n")
                        receipt.flush()
                        index += 1
                        backend.should_stop.wait(max(0, 1/15-(time.monotonic()-tick)))
        except Exception as exc:
            (args.record_dir / "ERROR.txt").write_text(repr(exc)+"\n")
            print(f"Live recording failed: {exc}", file=sys.stderr, flush=True)

    def observed_run(backend):
        recorder = Thread(target=capture, args=(backend,), daemon=True)
        recorder.start()
        try:
            original_run(backend)
        finally:
            backend.should_stop.set()
            recorder.join(timeout=5)
    MujocoBackend.run = observed_run

sys.argv = [sys.argv[0], "--sim", "--no-preload-datasets",
            "--no-goto-sleep-on-stop", "--robot-name", "lab2-simulation", "--log-level", args.log_level]
if not args.media:
    sys.argv.append("--no-media")
if not args.viewer:
    sys.argv.append("--headless")
main()
