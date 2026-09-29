"""Start only MuJoCo, with explicit GStreamer bootstrap for Python 3.12."""
import sys
import gstreamer_libs

gstreamer_libs.setup_python_environment()
from reachy_mini.daemon.app.main import main

sys.argv = [sys.argv[0], "--sim", "--headless", "--no-media", "--no-preload-datasets",
            "--no-goto-sleep-on-stop", "--log-level", "WARNING"]
main()
