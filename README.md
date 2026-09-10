# Breeze TTS 2 — Pinokio launcher

A 1-click [Pinokio](https://pinokio.co) launcher for [Breeze TTS 2](https://huggingface.co/BreezeBlue/Breeze-TTS-2),
BreezeBlue's open-weight bilingual (English / Chinese) text-to-speech model.

The upstream repository ([breezeblue-ai/breeze-tts](https://github.com/breezeblue-ai/breeze-tts))
ships a CLI and a raw PCM streaming API but no web UI, so this launcher adds
`breeze_webui.py` — a Gradio interface driving the same runtime as `infer.py`.

## What it does

- **Voice Clone** — reproduces a speaker from clean reference audio plus its
  exact transcript, preserving timbre, rhythm, emotion, and style.
- **Voice Design** — creates a voice from a natural-language description, with
  no reference audio.
- **Voice Direction** — clones a voice from reference audio while steering tone,
  emotion, pace, and delivery via an instruction.
- **Vocal Events** — inline expressive events in the text: `(laugh)`, `(cough)`,
  `(clears throat)`, `(sigh)` in English; `[笑]`, `[咳嗽]`, `[清嗓子]`, `[叹气]`
  in Chinese.

## Requirements

- Windows or Linux with an **NVIDIA CUDA GPU**
- **~8 GiB VRAM** for eager inference (a 12 GB GPU is the recommended minimum)
- **~25 GB free disk** — 7.7 GB of model weights plus the venv and CUDA torch

## Install

In Pinokio, click **Install**. That runs `install.js`, which:

1. Clones `breezeblue-ai/breeze-tts` into `app/`
2. Copies `breeze_webui.py` into the checkout
3. Creates the `app/env` venv and installs `requirements.txt` plus `gradio`
4. Reinstalls torch/torchaudio 2.9.1 from the CUDA 12.8 index (`torch.js`) —
   the PyPI wheels pinned upstream are CPU-only on Windows
5. Downloads the checkpoint to `app/breeze-tts-2/` (~7.7 GB)

Then click **Start** and open the web UI.

Clicking **Install** again is safe: the clone is skipped when `app/` already
exists, so a re-run repairs a partial install (missing deps, an interrupted
weight download) without re-cloning. For routine upgrades use **Update**; to
start completely over use **Reset**, which deletes the weights too.

## Usage

1. Type the text to synthesize. Add inline vocal events if you want them.
2. Pick a mode:
   - *Voice Clone* — open **Reference audio**, upload a clean recording, and
     paste its **exact** transcript. Leave the instruction empty.
   - *Voice Design* — leave the reference empty and describe the voice in the
     **Instruction** box. Raise **CFG scale** to 4.
   - *Voice Direction* — supply both a reference and an instruction. CFG 4.
3. Click **Generate**. The first run loads the model and takes noticeably
   longer than subsequent ones.

Match the instruction language to the target text. Reference audio should be
clean speech with minimal background noise.

### Environment variables

Set these in Pinokio's **Configure** tab (they are stored in the launcher's
`ENVIRONMENT` file and imported automatically on every script run), then
restart via **Start**.

| Variable | Default | Purpose |
| --- | --- | --- |
| `BREEZE_TTS_MODEL` | `app/breeze-tts-2` | Path to the checkpoint directory |
| `BREEZE_TTS_FAST` | unset | Set to `1` to enable the CUDA-graph fast path (`--fast-all`). Needs ~14.4 GiB VRAM and adds cold-start time. |

## API

The running web UI exposes the Gradio API. Replace `http://127.0.0.1:7860`
with the URL Pinokio shows in the **Open Web UI** tab.

The endpoint takes `[text, instruction, ref_audio, ref_text, cfg_scale, seed,
randomize_seed]` and returns `[audio, seed_used]`. Pass `null` for `ref_audio`
and `""` for `ref_text` when you are not cloning.

### Python

```python
from gradio_client import Client, handle_file

client = Client("http://127.0.0.1:7860")

# Voice design — no reference audio
audio_path, seed_used = client.predict(
    "(sigh) Welcome aboard. Your journey begins now.",
    "A warm, thoughtful young woman with a clear voice and a calm delivery.",
    None,
    "",
    4,
    42,
    False,
    api_name="/generate",
)
print(audio_path, seed_used)

# Voice clone — reference audio plus its exact transcript
audio_path, seed_used = client.predict(
    "(laugh) It is good to hear your voice again.",
    "",
    handle_file("reference.wav"),
    "This is the exact transcript of the reference audio.",
    1,
    42,
    False,
    api_name="/generate",
)
```

Install the client with `pip install gradio_client`.

### JavaScript

```javascript
import { Client } from "@gradio/client";

const client = await Client.connect("http://127.0.0.1:7860");

const result = await client.predict("/generate", [
  "(sigh) Welcome aboard. Your journey begins now.",
  "A warm, thoughtful young woman with a clear voice and a calm delivery.",
  null,
  "",
  4,
  42,
  false,
]);

console.log(result.data); // [{ url, path, ... }, seedUsed]
```

Install the client with `npm install @gradio/client`.

### curl

Gradio's REST bridge is a two-step call — POST the inputs to get an event id,
then GET the result stream.

```bash
EVENT_ID=$(curl -s -X POST http://127.0.0.1:7860/gradio_api/call/generate \
  -H "Content-Type: application/json" \
  -d '{"data": ["(sigh) Welcome aboard. Your journey begins now.", "A warm, thoughtful young woman with a clear voice and a calm delivery.", null, "", 4, 42, false]}' \
  | python -c "import sys,json;print(json.load(sys.stdin)['event_id'])")

curl -N http://127.0.0.1:7860/gradio_api/call/generate/$EVENT_ID
```

The response stream ends with a `data:` line holding the output array; the
first element carries the generated audio file path/URL.

### Upstream streaming API

For low-latency streaming, the upstream FastAPI server is also available in the
installed checkout. From `app/`, with the `env` venv active:

```bash
python -m breeze_infer.api breeze-tts-2 --host 127.0.0.1 --port 7860
```

```bash
curl -X POST http://127.0.0.1:7860/v1/audio/speech \
  -F "cfg_scale=4" \
  -F "ref_audio=@reference.wav" \
  -F "ref_text=This is the exact transcript of the reference audio." \
  -F "text=(clears throat) We need to discuss what happened last night." \
  -F "instruction=Speak slowly with a restrained, serious tone." \
  -F "seed=42" \
  --output voice_direction.pcm
```

It returns streaming mono 24 kHz signed 16-bit little-endian PCM. Add
`--fast-all` at startup for the CUDA-graph fast path.

## Launcher scripts

| File | Purpose |
| --- | --- |
| `install.js` | Clone the code, build the venv, install torch, download weights |
| `start.js` | Launch the Gradio web UI and capture its URL |
| `update.js` | Pull the launcher and the upstream code, refresh the UI and deps |
| `reset.js` | Delete `app/` to revert to the pre-install state |
| `link.js` | Deduplicate venv libraries to save disk space |
| `torch.js` | Platform-specific torch/torchaudio install |
| `pinokio.js` | Dynamic launcher menu |
| `pinokio.json` | Launcher metadata (title, description, icon, GPU/platform) |
| `icon.png` | Launcher icon |
| `breeze_webui.py` | The Gradio UI, copied into `app/` at install time |

## License

The launcher scripts and `breeze_webui.py` follow the upstream code license,
[Apache 2.0](https://github.com/breezeblue-ai/breeze-tts/blob/main/LICENSE).

**The Breeze TTS 2 model weights are not Apache-licensed.** They are governed by
the [BreezeBlue Research and Non-Commercial License](https://huggingface.co/BreezeBlue/Breeze-TTS-2/blob/main/LICENSE):
weights, derivative models, and self-hosted outputs are for research and
non-commercial use only. Commercial use of outputs requires BreezeBlue's hosted
platform with a paid subscription.

You are responsible for obtaining the rights and consents for any reference
audio and voices you use. Unauthorized voice cloning, impersonation, and fraud
are prohibited.
