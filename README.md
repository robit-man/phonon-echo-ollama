# Phonon Echo for Ollama

Standalone tools for [robit/phonon-echo](https://ollama.com/robit/phonon-echo):
native TTS preparation for the official Ollama binary, plus an optional
Ollama-managed reference-cloning and ASR runner.

| Model tag | Official Ollama 0.40.11 | This extension |
| --- | --- | --- |
| `robit/phonon-echo:tts-v1` | TTS | Not needed |
| `robit/phonon-echo:latest` | Same native TTS model | Not needed |
| `robit/phonon-echo:hybrid-v1` | Same native TTS model; compatibility alias | Not needed |
| `robit/phonon-echo:clone-asr-v2` | Unsupported composite architecture | TTS, baked female/robot/male profiles, reference cloning, English ASR |

[OLLAMA_README.md](OLLAMA_README.md) is the ready-to-publish model-page README.

## Official TTS

Use unmodified official Ollama 0.40.11 with its official MLX runtime:

```bash
ollama pull robit/phonon-echo:tts-v1
curl http://127.0.0.1:11434/v1/audio/speech \
  -H 'Content-Type: application/json' \
  -d '{"model":"robit/phonon-echo:tts-v1","input":"Hello from Phonon Echo.","voice":"default"}' \
  --output speech.wav
```

On Linux, the tested official speech implementation uses CUDA. Its additional
MLX payload is included in the
[official release assets](https://github.com/ollama/ollama/releases/tag/v0.40.11)
as `ollama-linux-amd64-mlx.tar.zst`. Follow the
[official speech documentation](https://docs.ollama.com/capabilities/speech).
The TTS tags require no Python inference worker or custom Ollama binary.

## Cloning and ASR extension

This optional adapter extends Ollama 0.40.11's importer and managed-runner path.
It builds a **separate executable** and leaves your installed official Ollama
binary alone. The new executable identifies itself as
`0.40.11+phonon-echo.2`. Stock TTS and the companion are separate model tags;
installing the companion does not make reference cloning or ASR native to the
unmodified official binary.

Ollama resolves the companion tag, schedules the model, and starts the local
CPU runner. That runner verifies SHA-256 digests and loads all neural weights
from the tag's Ollama tensor blobs. It does not call a remote speech service or
require source checkpoint folders. No weights, recordings, or private speaker
embeddings are stored in this repository.

### Install

Validated on Linux with Python 3.12. Install `git`, a C/C++ toolchain,
[uv](https://docs.astral.sh/uv/), and a Go toolchain supporting Ollama's
`go 1.26.10` directive.

```bash
git clone https://github.com/robit-man/phonon-echo-ollama.git
cd phonon-echo-ollama
bash scripts/setup.sh
bash scripts/build-ollama.sh
bash scripts/serve.sh
```

`setup.sh` creates `.venv`, installs CPU PyTorch and pinned runtime dependencies,
then installs the pinned OpenVoice architecture without its optional demo
dependencies. `build-ollama.sh` applies the checked-in patch to the exact
official v0.40.11 commit and writes `bin/ollama`. Source and build products are
kept in ignored `.cache/` and `bin/` directories.

The daemon listens on `127.0.0.1:11471`. From another terminal in this checkout:

```bash
OLLAMA_HOST=127.0.0.1:11471 bin/ollama pull robit/phonon-echo:clone-asr-v2
```

For an existing checkout, run `git pull`, repeat setup and build, then restart
the extension daemon. Patch revisions build in separate source directories, so
upgrading does not overwrite an older patched checkout. The older
`clone-asr-v1` model remains available without the new baked profiles.

The launch script supplies these runner settings automatically:

```bash
export OLLAMA_PHONON_HYBRID_PYTHON="$PWD/.venv/bin/python"
export OLLAMA_PHONON_HYBRID_ROOT="$PWD"
export OLLAMA_HOST=127.0.0.1:11471
```

It fences GPU visibility because this companion implementation runs on CPU.
Its model pull does not require MLX. The official CUDA TTS workload is separate;
on hosts using a GPU lease broker, reserve the exact GPU scope before starting
that official workload.

### Use the baked default profiles

`clone-asr-v2` ships `default`, `female`, `robot`, and `male`. The three cloned
profiles are registered model buffers and travel with the checkpoint. You do
not need the source recordings or a separate enrollment directory.

```bash
curl http://127.0.0.1:11471/v1/audio/speech \
  -H 'Content-Type: application/json' \
  -d '{"model":"robit/phonon-echo:clone-asr-v2","input":"The small robot speaks clearly.","voice":"robot"}' \
  --output robot.wav
```

Use `female`, `male`, or `default` in the same field. `/api/show` lists the
available names. Source recordings are not included in the model or this repo.

### Clone another reference voice

Create a request using a short mono `reference.wav`:

```bash
.venv/bin/python - <<'PY'
import base64
import json
from pathlib import Path

Path("request.json").write_text(json.dumps({
    "model": "robit/phonon-echo:clone-asr-v2",
    "input": "The small robot speaks clearly.",
    "voice": "default",
    "reference_audio": {
        "format": "wav",
        "data": base64.b64encode(Path("reference.wav").read_bytes()).decode(),
    },
}))
PY
curl http://127.0.0.1:11471/v1/audio/speech \
  -H 'Content-Type: application/json' --data-binary @request.json \
  --output cloned.wav
```

The trained reference encoder and OpenVoice converter condition the generated
speech on that recording. No reference transcript is needed. Omitting
`reference_audio` uses the public default Phonon voice. Inline references do not
create a persistent speaker profile.

### Transcribe

```bash
curl http://127.0.0.1:11471/v1/audio/transcriptions \
  -F model=robit/phonon-echo:clone-asr-v2 \
  -F file=@recording.wav
```

### Limits

- English speech and ASR; ASR recordings are limited to 30 seconds.
- Speech input: 1–4,096 characters; speed is 1 and instructions are empty.
- Output: 24 kHz mono PCM16; streaming WAV by default, or `response_format: pcm`.
- Streaming WAV headers have unknown lengths. Count received PCM samples when
  inspecting duration, or rewrite the header when saving a seekable WAV.
- Speech requests are limited to 1 MiB. Use short, clean mono reference WAVs.
- The companion's text output is ASR. It is not a general chat model.
- The exported companion combines pretrained Phonon, Mimi, OpenVoice V2, and
  Whisper tiny.en. It has 111.6 million unique parameters and was not jointly trained.

## Prepare models

The native TTS preparer downloads five pinned files, checks their SHA-256
digests, sets deterministic generation, and writes a Modelfile with licenses:

```bash
.venv/bin/python -m phonon_echo.native_tts prepare --out outputs/native-tts
ollama create my-phonon-tts -f outputs/native-tts/Modelfile
```

For companion training or export work, `phonon-echo download --out DIRECTORY`
downloads the pinned source components. `phonon-echo build --help` describes
composition into one safetensors export. Source revisions are recorded in
[phonon_echo/sources.py](phonon_echo/sources.py). Inference from the published
Ollama tag does not need this preparation step.

To bake additional named profiles from your own references into a new export:

```bash
.venv/bin/python -m phonon_echo.bake_voices \
  --models-directory "$HOME/.ollama/models" \
  --source-model robit/phonon-echo:clone-asr-v1 \
  --voice narrator=reference.wav --out outputs/my-voices
```

The source model must already be installed in that model store. Baking verifies
the source blobs, encodes the recordings on CPU, and saves the embeddings as
`voices.NAME` tensors. Recordings and source filenames are excluded from the
export; a separate local receipt records hashes. Import the exported directory
with the extension's `bin/ollama create` command.

## Validation

```bash
uv pip install --python .venv/bin/python -r requirements-dev.txt
CUDA_VISIBLE_DEVICES=-1 .venv/bin/python -m pytest -q
.venv/bin/python -m ruff check phonon_echo tests
```

The upstream implementation was tested with actual official-binary TTS and a
fresh registry pull, including WAV/PCM and three exact sentence checks after
case/punctuation normalization. Companion fixtures checked speech, ASR, and
default/A/B/A references; WavLM measured 0.872 similarity to reference A for the
first A output and 0.994 between repeated A outputs. These bounded synthetic
fixtures are not a general speaker benchmark. See [docs/validation.json](docs/validation.json).

## License and provenance

New extension code: Apache-2.0. The patch modifies MIT-licensed Ollama v0.40.11;
its full license is retained. Component licenses and source provenance are in
[NOTICE](NOTICE) and [phonon_echo/licenses](phonon_echo/licenses).
Phonon/Mimi use Apache-2.0, OpenVoice V2 uses MIT, and Whisper's model card uses
Apache-2.0 with MIT-licensed upstream code. This project is independent of the
upstream projects.
