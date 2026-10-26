# Phonon Echo

English text-to-speech for Ollama, with an optional reference-voice-cloning and
speech-recognition companion.

| Tag | Capabilities | Runtime |
| --- | --- | --- |
| `tts-v1` | Text to speech, default voice | Unmodified official Ollama |
| `latest` | Alias of `tts-v1` | Unmodified official Ollama |
| `hybrid-v1` | Compatibility alias of `tts-v1` | Unmodified official Ollama |
| `clone-asr-v1` | Reference voice cloning, TTS, English ASR | Optional Phonon Echo extension |

## Text to speech

Validated with **official Ollama 0.40.11** and its official MLX runtime. TTS
executes the installed tag's Phonon/Mimi weights inside Ollama. No adapter is
required for the TTS tags.

```bash
ollama pull robit/phonon-echo:tts-v1

curl http://localhost:11434/v1/audio/speech \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "robit/phonon-echo:tts-v1",
    "input": "Hello from Phonon Echo.",
    "voice": "default"
  }' \
  --output speech.wav
```

Output is **24 kHz mono PCM16 WAV**. Add `"response_format":"pcm"` for raw
little-endian PCM. Audio streams as it is generated; WAV responses use an
unknown-length header. Input is limited to 4,096 characters.

The official MLX runtime must be installed. On Linux, the tested official
speech runtime uses CUDA and is available in the
[Ollama 0.40.11 release](https://github.com/ollama/ollama/releases/tag/v0.40.11)
as `ollama-linux-amd64-mlx.tar.zst`. See the
[official speech API documentation](https://docs.ollama.com/capabilities/speech).

## Optional voice cloning and ASR

Use **`robit/phonon-echo:clone-asr-v1`** with the public
[Phonon Echo adapter and runner extension](https://github.com/robit-man/phonon-echo-ollama#cloning-and-asr-extension).
This companion requires the extension; stock Ollama does not execute its
reference encoder, voice converter, or Whisper graph. The stock speech API has
no per-request reference-audio field.

After installing the extension and starting it on port 11471:

```bash
OLLAMA_HOST=127.0.0.1:11471 ./bin/ollama pull robit/phonon-echo:clone-asr-v1
```

Generate speech conditioned on a local reference WAV:

```python
import base64
import json
import urllib.request
from pathlib import Path

payload = {
    "model": "robit/phonon-echo:clone-asr-v1",
    "input": "The small robot speaks clearly.",
    "voice": "default",
    "reference_audio": {
        "format": "wav",
        "data": base64.b64encode(Path("reference.wav").read_bytes()).decode(),
    },
}
request = urllib.request.Request(
    "http://127.0.0.1:11471/v1/audio/speech",
    data=json.dumps(payload).encode(),
    headers={"Content-Type": "application/json"},
)
with urllib.request.urlopen(request, timeout=180) as response:
    Path("cloned.wav").write_bytes(response.read())
```

Transcribe English audio with the same companion tag:

```bash
curl http://127.0.0.1:11471/v1/audio/transcriptions \
  -F model=robit/phonon-echo:clone-asr-v1 \
  -F file=@recording.wav
```

The extension currently runs on CPU. Use short, clean mono references; the
speech request body is limited to 1 MiB. No reference transcript is required.
ASR accepts English recordings up to 30 seconds. Reference recordings and
derived speaker embeddings are processed locally and are not included in the
published weights.

## Models and validation

The native TTS tags package Gradium Phonon and its Mimi decoder, with the public
default voice and deterministic generation settings. The companion combines
Phonon, Mimi, OpenVoice V2 reference-conditioned voice conversion, and Whisper
tiny.en. These are pretrained components; the companion has not been jointly
trained. These models are for English speech, rather than general chat or Qwen
Omni's broader modalities.

An official-binary fresh-pull test passed WAV, PCM, and three held-out sentence
checks. The companion passed TTS, ASR, and alternating A/B/A reference checks.
Independent WavLM verification measured 0.872 cosine similarity to reference A
for the first A output, and 0.994 similarity between the repeated A outputs.
These are bounded synthetic-fixture results, not a general speaker benchmark.
[Validation details](https://github.com/robit-man/phonon-echo-ollama/blob/main/docs/validation.json).

## Sources and licenses

- [Gradium Phonon](https://huggingface.co/gradium/phonon-31m-en) and
  [Mimi](https://huggingface.co/gradium/phonon-mimi): Apache 2.0.
- [OpenVoice V2](https://huggingface.co/myshell-ai/OpenVoiceV2): MIT.
- [Whisper tiny.en](https://huggingface.co/openai/whisper-tiny.en): Apache 2.0
  model card; upstream Whisper code is MIT.

Component license texts are included in the model license layers. The optional
[extension source and setup instructions](https://github.com/robit-man/phonon-echo-ollama)
are public.
