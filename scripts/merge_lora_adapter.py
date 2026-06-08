#!/usr/bin/env python3
"""Merge a PEFT LoRA Whisper adapter into a standalone local model.

Example:
    python scripts/merge_lora_adapter.py \
        --lora-path models/whisper-advent-track \
        --output-dir models/whisper-advent-track-merged
"""
from __future__ import annotations

import argparse
from pathlib import Path

import torch
from peft import PeftModel
from transformers import WhisperForConditionalGeneration, WhisperProcessor


DEFAULT_BASE_MODEL = "sgangireddy/whisper-small-tr"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Merge a Whisper LoRA adapter into a full local Whisper model."
    )
    parser.add_argument(
        "--base-model",
        default=DEFAULT_BASE_MODEL,
        help=f"Base Whisper model name/path. Default: {DEFAULT_BASE_MODEL}",
    )
    parser.add_argument(
        "--lora-path",
        type=Path,
        required=True,
        help="Path to the PEFT LoRA adapter directory containing adapter_config.json.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="Directory where the merged standalone model will be saved.",
    )
    parser.add_argument(
        "--dtype",
        choices=["auto", "float16", "float32"],
        default="auto",
        help="Model load dtype. Default auto uses float16 on CUDA and float32 on CPU.",
    )
    parser.add_argument(
        "--device-map",
        default=None,
        help="Optional Transformers device_map value, for example 'auto'. Default is None.",
    )
    return parser.parse_args()


def resolve_dtype(dtype_arg: str) -> torch.dtype:
    if dtype_arg == "float16":
        return torch.float16
    if dtype_arg == "float32":
        return torch.float32
    return torch.float16 if torch.cuda.is_available() else torch.float32


def validate_lora_path(lora_path: Path) -> None:
    if not lora_path.exists():
        raise FileNotFoundError(f"LoRA adapter directory not found: {lora_path}")
    if not (lora_path / "adapter_config.json").exists():
        raise FileNotFoundError(f"Missing adapter_config.json in: {lora_path}")
    has_weights = (lora_path / "adapter_model.safetensors").exists() or (
        lora_path / "adapter_model.bin"
    ).exists()
    if not has_weights:
        raise FileNotFoundError(
            f"Missing adapter weights in {lora_path}. Expected adapter_model.safetensors or adapter_model.bin."
        )


def main() -> None:
    args = parse_args()
    lora_path = args.lora_path.expanduser().resolve()
    output_dir = args.output_dir.expanduser().resolve()
    validate_lora_path(lora_path)

    dtype = resolve_dtype(args.dtype)
    print("=" * 72)
    print("Whisper LoRA Adapter Merge")
    print("=" * 72)
    print(f"Base model : {args.base_model}")
    print(f"LoRA path  : {lora_path}")
    print(f"Output dir : {output_dir}")
    print(f"CUDA       : {torch.cuda.is_available()}")
    print(f"dtype      : {dtype}")
    print(f"device_map : {args.device_map or 'None'}")
    print("=" * 72)

    output_dir.mkdir(parents=True, exist_ok=True)

    load_kwargs = {"torch_dtype": dtype}
    if args.device_map:
        load_kwargs["device_map"] = args.device_map

    print("Base model yukleniyor...")
    base_model = WhisperForConditionalGeneration.from_pretrained(
        args.base_model,
        **load_kwargs,
    )

    if not args.device_map:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        base_model.to(device)

    print("LoRA adapter yukleniyor...")
    model = PeftModel.from_pretrained(base_model, str(lora_path))

    print("Merge ediliyor...")
    merged_model = model.merge_and_unload()

    print("Model kaydediliyor...")
    merged_model.save_pretrained(output_dir, safe_serialization=True)

    print("Processor kaydediliyor...")
    processor = WhisperProcessor.from_pretrained(args.base_model)
    processor.save_pretrained(output_dir)

    print("=" * 72)
    print(f"MERGE TAMAMLANDI: {output_dir}")
    print("Bu klasor artik web_app model seciminde lokal tam model olarak gorunebilir.")
    print("=" * 72)


if __name__ == "__main__":
    main()
