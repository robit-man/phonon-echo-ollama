"""Bake named reference speaker profiles into a self-contained hybrid checkpoint."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import torch

from phonon_echo.model import digest, read_audio
from phonon_echo.storage import load_ollama_model


def bake(*, models_directory, source_model, voices, output):
    model = load_ollama_model(models_directory, source_model)
    receipts = {}
    for name, recording in voices.items():
        audio, rate = read_audio(recording.read_bytes(), max_seconds=30)
        # Trim leading/trailing silence and standardize reference amplitude.
        active = np.flatnonzero(np.abs(audio) > max(float(np.max(np.abs(audio))) * 0.03, 0.0005))
        if not len(active):
            raise ValueError("reference has no active speech")
        padding = int(rate * 0.05)
        audio = audio[max(0, active[0] - padding):min(len(audio), active[-1] + padding + 1)]
        if len(audio) / rate < 0.25:
            raise ValueError("reference active speech is too short")
        audio = audio * (0.9 / float(np.max(np.abs(audio))))
        embedding = model.speaker_embedding(audio, rate)
        model.add_voice_profile(name, embedding)
        receipts[name] = {"reference_sha256": digest(recording), "active_seconds": len(audio) / rate,
                          "embedding_shape": list(embedding.shape), "embedding_norm": float(embedding.norm())}
        print(json.dumps({"baked_voice": name, "active_seconds": round(len(audio) / rate, 3)}), flush=True)
    manifest = model.save_pretrained(output)
    card = {"name": "Phonon Echo", "tag": "robit/phonon-echo:clone",
            "available_voices": model.voice_names(), "source_recordings_in_checkpoint": False,
            "requires_extension": "phonon-echo.2", "official_binary_supported": False,
            "setup": "https://github.com/robit-man/phonon-echo-ollama#cloning-and-asr-extension",
            "composition": ["Phonon", "Mimi", "OpenVoice V2", "Whisper tiny.en"], "jointly_trained": False}
    (output / "model-card.json").write_text(json.dumps(card, indent=2) + "\n")
    manifest["files"]["model-card.json"] = digest(output / "model-card.json")
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    receipt = {"schema": "phonon-echo.baked-voices.v1", "source_model": source_model,
               "profiles": receipts, "available_voices": model.voice_names(),
               "source_recordings_in_checkpoint": False, "cuda_initialized": torch.cuda.is_initialized(),
               "checkpoint_sha256": manifest["files"]["model.safetensors"]}
    if not all(math.isfinite(p["embedding_norm"]) for p in receipts.values()):
        raise ValueError("nonfinite speaker profile")
    (output.parent / "bake-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models-directory", type=Path, default=Path.home() / ".ollama/models")
    parser.add_argument("--source-model", default="robit/phonon-echo:clone")
    parser.add_argument("--voice", action="append", required=True, metavar="NAME=RECORDING")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    voices = {}
    for value in args.voice:
        if "=" not in value:
            parser.error("--voice requires NAME=RECORDING")
        name, recording = value.split("=", 1)
        if name in voices:
            parser.error("duplicate voice name")
        voices[name] = Path(recording)
    torch.set_num_threads(4)
    print(json.dumps(bake(models_directory=args.models_directory, source_model=args.source_model,
                          voices=voices, output=args.out), indent=2))


if __name__ == "__main__":
    main()
