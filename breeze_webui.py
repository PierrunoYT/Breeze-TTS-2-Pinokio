"""Gradio web UI for Breeze TTS 2.

The upstream repository ships a CLI (`infer.py`) and a raw PCM streaming API
only, so this launcher supplies its own UI. It runs from inside the cloned
`breeze-tts` checkout and drives exactly the same runtime as `infer.py`.
"""

from __future__ import annotations

import os
import random
import threading
import uuid
from dataclasses import replace
from pathlib import Path

import gradio as gr
import numpy as np
from transformers import AutoTokenizer, GemmaTokenizerFast

from breeze_infer.runtime import (
    load_runtime,
    resolve_device,
    set_all_seeds,
    update_generation_config_for_breeze,
)
from breeze_infer.templates import get_template, prepare_inputs, select_template_name
from models.breeze_config import BreezeConfig
from models.fast_streaming import FastBreezeStreamingRuntime, FastStreamingConfig
from models.warmup_profile import load_warmup_profile

# Register the tokenizer for the custom config so AutoTokenizer does not have
# to rely solely on the checkpoint metadata to resolve it.
AutoTokenizer.register(
    BreezeConfig, fast_tokenizer_class=GemmaTokenizerFast, exist_ok=True
)

REPO_ROOT = Path(__file__).resolve().parent
FAST_CONFIG = REPO_ROOT / "configs" / "fast.json"
MODEL_DIR = Path(os.environ.get("BREEZE_TTS_MODEL", REPO_ROOT / "breeze-tts-2"))

# Mirrors the constants in infer.py
MAX_NEW_TOKENS = 1500
MAX_SEQ_LEN = 2048
REPETITION_PENALTY = 1.1

FAST_ALL = os.environ.get("BREEZE_TTS_FAST", "").lower() in {"1", "true", "yes"}

_runtime_lock = threading.Lock()
_runtime_state = {}


def _get_runtime():
    """Load the model on first use so the Gradio URL is printed immediately."""
    if _runtime_state:
        return _runtime_state

    if not MODEL_DIR.is_dir():
        raise gr.Error(
            f"Breeze TTS 2 checkpoint not found at {MODEL_DIR}. "
            "Re-run the Install step in the launcher to download it."
        )

    print(f"loading Breeze TTS 2 from {MODEL_DIR} ...", flush=True)
    tokenizer, model, audio_tokenizer = load_runtime(
        MODEL_DIR,
        device=resolve_device(),
        attn_implementation="eager",
    )
    update_generation_config_for_breeze(model)

    config = FastStreamingConfig(
        max_new_tokens=MAX_NEW_TOKENS,
        max_seq_len=MAX_SEQ_LEN,
        # Set the per-stage flags to match fast_all rather than pinning them to
        # False, so the result does not depend on which of the two wins when
        # they disagree.
        fast_all=True if FAST_ALL else None,
        fast_text_encoder=FAST_ALL,
        fast_backbone_prefill=FAST_ALL,
        fast_backbone_decode=FAST_ALL,
        fast_depth_decoder=FAST_ALL,
        fast_codec=FAST_ALL,
        repetition_penalty=REPETITION_PENALTY,
    )
    runtime = FastBreezeStreamingRuntime(
        model, audio_tokenizer, config, tokenizer=tokenizer
    )
    if runtime.fast_enabled:
        profile = load_warmup_profile(FAST_CONFIG)
        profile = replace(profile, codec_chunk_frames=runtime.codec_chunk_frames)
        manifest = runtime.warmup_from_profile(profile)
        print(f"fast warmup: {manifest['total_elapsed_ms']:.2f} ms", flush=True)

    _runtime_state.update(
        tokenizer=tokenizer,
        model=model,
        audio_tokenizer=audio_tokenizer,
        runtime=runtime,
    )
    print("model ready", flush=True)
    return _runtime_state


def generate(text, instruction, ref_audio, ref_text, cfg_scale, seed, randomize_seed):
    text = (text or "").strip()
    if not text:
        raise gr.Error("Enter some text to synthesize.")

    instruction = (instruction or "").strip()
    ref_text = (ref_text or "").strip()

    has_ref_audio = bool(ref_audio)
    if has_ref_audio != bool(ref_text):
        raise gr.Error(
            "Reference audio and its exact transcript must be provided together. "
            "Leave both empty for Voice Design."
        )

    cfg_scale = float(cfg_scale)
    if not np.isfinite(cfg_scale) or cfg_scale <= 0:
        raise gr.Error("CFG scale must be greater than 0.")

    if randomize_seed:
        seed = random.randint(0, 2**31 - 1)
    # gr.Number yields None when the box is cleared, and int(None) would
    # surface as a bare TypeError instead of a readable message.
    if seed is None:
        raise gr.Error("Enter a seed, or tick Randomize.")
    seed = int(seed)
    # set_all_seeds feeds np.random.seed, which rejects anything outside this.
    if not 0 <= seed < 2**32:
        raise gr.Error("Seed must be between 0 and 4294967295.")

    with _runtime_lock:
        state = _get_runtime()
        runtime = state["runtime"]

        request_id = f"webui-{uuid.uuid4().hex}"
        request = {
            "id": request_id,
            "text": text,
            "speaker": "S0",
        }
        # Like infer.py, only send an instruction when one was given: an empty
        # box selects the plain / voice-clone templates, a filled one selects
        # voice design / voice direction.
        if instruction:
            request["instruction"] = instruction
        if has_ref_audio:
            request["ref_audio_path"] = str(ref_audio)
            request["ref_text"] = ref_text
        template_name = select_template_name(request)

        set_all_seeds(seed)
        inputs = prepare_inputs(
            state["tokenizer"],
            state["audio_tokenizer"],
            state["model"],
            [request],
            get_template(template_name),
            guidance_scale=cfg_scale,
            guidance_scale_ref=None,
            guidance_scale_ins=None,
        )

        chunks = [
            chunk.audio
            for chunk in runtime.iter_audio_chunks(
                inputs, request_id=request_id, seed=seed
            )
        ]

    if not chunks:
        raise gr.Error("The model returned no audio. Try a different seed or text.")

    # chunk.audio is float32 in [-1, 1]; convert the same way the upstream API
    # does so Gradio does not have to infer the range.
    audio = np.clip(np.concatenate(chunks).astype(np.float32), -1.0, 1.0)
    return (runtime.sample_rate, (audio * 32767.0).astype(np.int16)), seed


with gr.Blocks(title="Breeze TTS 2") as demo:
    gr.Markdown(
        "# Breeze TTS 2\n"
        "Bilingual (English / Chinese) text-to-speech from "
        "[BreezeBlue](https://breezeblue.ai/breeze-tts-2).\n\n"
        "- **Voice Clone** - upload reference audio and its exact transcript, "
        "and leave the instruction empty.\n"
        "- **Voice Design** - leave the reference empty and describe the voice "
        "in the instruction. Use CFG 4.\n"
        "- **Voice Direction** - reference audio *and* an instruction, to keep "
        "the speaker but steer the delivery. Use CFG 4.\n\n"
        "Inline vocal events: `(laugh)`, `(sigh)`, `(cough)`, `(clears throat)` "
        "in English; the square-bracket equivalents such as `[笑]` and "
        "`[叹气]` in Chinese."
    )

    with gr.Row():
        with gr.Column(scale=3):
            text = gr.Textbox(
                label="Text",
                lines=4,
                placeholder="(sigh) It is good to hear your voice again after all this time.",
            )
            instruction = gr.Textbox(
                label="Instruction (voice design / voice direction)",
                lines=2,
                placeholder="A warm, thoughtful young woman with a clear voice "
                "and a calm delivery.",
                info="Describe the voice or the delivery. Match the instruction "
                "language to the target text. Leave empty for Voice Clone or a "
                "plain read.",
            )
            with gr.Accordion(
                "Reference audio (voice clone / voice direction)", open=False
            ):
                ref_audio = gr.Audio(
                    label="Reference audio",
                    type="filepath",
                    sources=["upload", "microphone"],
                )
                ref_text = gr.Textbox(
                    label="Reference transcript",
                    lines=2,
                    info="Must be the exact transcript of the reference audio. "
                    "Use clean speech with minimal background noise.",
                )
        with gr.Column(scale=2):
            cfg_scale = gr.Slider(
                label="CFG scale",
                minimum=1.0,
                maximum=8.0,
                step=0.5,
                value=1.0,
                info="1 for plain voice clone. 4 strengthens instruction-following.",
            )
            with gr.Row():
                seed = gr.Number(label="Seed", value=42, precision=0)
                randomize_seed = gr.Checkbox(label="Randomize", value=False)
            generate_button = gr.Button("Generate", variant="primary")
            output_audio = gr.Audio(label="Output", type="numpy")
            used_seed = gr.Number(label="Seed used", interactive=False)

    gr.Markdown(
        "The model is loaded on the first generation, so the first run takes "
        "noticeably longer. Model weights are licensed for research and "
        "non-commercial use only."
    )

    generate_button.click(
        fn=generate,
        inputs=[
            text,
            instruction,
            ref_audio,
            ref_text,
            cfg_scale,
            seed,
            randomize_seed,
        ],
        outputs=[output_audio, used_seed],
    )


if __name__ == "__main__":
    demo.queue().launch()
