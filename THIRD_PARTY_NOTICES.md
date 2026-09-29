# Third-party notices

## Active antenna-greeting-v1 components

The [Pollen Robotics Reachy Mini Conversation App](https://github.com/pollen-robotics/reachy_mini_conversation_app) uses Apache License 2.0. The original license is retained at `third_party/conversation/LICENSE`. `reachy_lab2/conversation_audio.py` adapts `audio_to_float32` from pinned revision b9f58a3587d79a3275d4402d1a8d210649d62d50; the original `streaming.py` is retained for comparison. The complete Conversation App is not a runtime dependency of this greeting study.

The [Pollen Robotics Emotions app](https://huggingface.co/spaces/pollen-robotics/emotions) declares its glue code MIT in its README. The fetched revision did not expose a standalone LICENSE in the root listing. Its README and original source files are retained under `third_party/emotions/`; no absent upstream copyright notice has been invented. `motion.py` ports the trajectory parser/decimator; `emotion_player.py` ports its transition calculation. Python SDK transport, the greeting trajectory, validation and recovery adaptations are custom. Exact revisions, URLs, hashes and runtime mappings are recorded in `third_party/provenance.json` and `SOURCE_INTEGRATION.md`.

The MIT permission and warranty terms are reproduced here:

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

The current greeting WAV was generated once locally by macOS `say` using Samantha, then frozen. The command, transcript and hash are in `assets/greeting/manifest.json`. It is not attributed to the Conversation App backend, and no voice model is redistributed. Other installed dependencies retain their own package licenses.
