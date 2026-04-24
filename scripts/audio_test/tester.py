import re
from pathlib import Path

import numpy as np
import pandas as pd
import soundfile as sf
import librosa
import torch
from tqdm import tqdm

from transformers import WhisperProcessor, WhisperForConditionalGeneration
from peft import PeftModel

# =========================
# ✅ PATHS
# =========================
BASE_MODEL  = "sgangireddy/whisper-small-tr"

ADAPTER_DIR = Path("/home/wololoo/Havelsan_Suit/models/whisper_cmd_lora_adapter/whisper_cmd_lora_adapter")
DATA_ROOT   = Path("/home/wololoo/Havelsan_Suit/data/augmented_dataset")
META_PATH   = DATA_ROOT / "metadata.csv"

# =========================
# ✅ SUBSET AYARLARI
# =========================
SAMPLES_PER_COMMAND = 30     # her komuttan kaç örnek?
SEED = 42                   # aynı subset tekrar gelsin diye
SHOW_EXAMPLES = 10          # kaç örnekte TOP-5 yazdırsın

SAMPLE_RATE = 16000

# =========================
# HELPERS
# =========================
def norm_text(s: str) -> str:
    s = (s or "").strip().lower()
    s = s.replace("’", "'")
    s = re.sub(r"\s+", " ", s)
    return s

def load_audio_fast(wav_path: Path) -> np.ndarray:
    y, sr = sf.read(str(wav_path), always_2d=False)
    if isinstance(y, np.ndarray) and y.ndim > 1:
        y = y.mean(axis=1)
    y = np.asarray(y, dtype=np.float32)
    if sr != SAMPLE_RATE:
        y = librosa.resample(y, orig_sr=sr, target_sr=SAMPLE_RATE)
    return y

@torch.no_grad()
def rank_commands_for_audio(model, processor, device, y: np.ndarray, label_bank, commands, topk: int = 5):
    inputs = processor(y, sampling_rate=SAMPLE_RATE, return_tensors="pt")
    input_features = inputs["input_features"].to(device)

    scored = []
    for cmd_text, cmd_ids in zip(commands, label_bank):
        labels = cmd_ids.unsqueeze(0).to(device)
        out = model(input_features=input_features, labels=labels)
        loss = float(out.loss.detach().cpu().item())
        scored.append((cmd_text, loss))

    scored.sort(key=lambda x: x[1])
    return scored[:topk]

def main():
    if not ADAPTER_DIR.exists():
        raise FileNotFoundError(f"ADAPTER_DIR yok: {ADAPTER_DIR}")
    if not DATA_ROOT.exists():
        raise FileNotFoundError(f"DATA_ROOT yok: {DATA_ROOT}")
    if not META_PATH.exists():
        raise FileNotFoundError(f"META_PATH yok: {META_PATH}")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print("Device:", device)

    processor = WhisperProcessor.from_pretrained(str(ADAPTER_DIR))
    base = WhisperForConditionalGeneration.from_pretrained(BASE_MODEL).to(device)
    model = PeftModel.from_pretrained(base, str(ADAPTER_DIR)).to(device)
    model.eval()
    model.config.use_cache = False

    df = pd.read_csv(META_PATH)
    if "file" not in df.columns or "text" not in df.columns:
        raise ValueError("metadata.csv formatı 'file,text' olmalı.")

    # Komut listesi (unique text)
    commands = sorted(df["text"].astype(str).unique().tolist(), key=lambda x: x.lower())
    print("Unique command count:", len(commands))

    # Label bank
    label_bank = [torch.tensor(processor.tokenizer(t).input_ids, dtype=torch.long) for t in commands]

    # ✅ Her komuttan N örnek seç
    df = df.sample(frac=1.0, random_state=SEED).reset_index(drop=True)  # shuffle
    picked = (
        df.groupby("text", group_keys=False)
          .head(SAMPLES_PER_COMMAND)
          .reset_index(drop=True)
    )

    print(f"Seçilen örnek sayısı: {len(picked)} (her komuttan ~{SAMPLES_PER_COMMAND})")

    top1 = top3 = top5 = 0
    shown = 0
    show_n = min(SHOW_EXAMPLES, len(picked))

    for i in tqdm(range(len(picked)), desc="Evaluating subset"):
        rel_file = str(picked.loc[i, "file"])
        gt_text  = str(picked.loc[i, "text"])

        wav_path = DATA_ROOT / rel_file
        if not wav_path.exists():
            alt = Path(rel_file)
            if alt.exists():
                wav_path = alt
            else:
                continue

        y = load_audio_fast(wav_path)
        top_list = rank_commands_for_audio(model, processor, device, y, label_bank, commands, topk=5)

        preds = [norm_text(t) for (t, loss) in top_list]
        gt = norm_text(gt_text)

        if preds and preds[0] == gt:
            top1 += 1
        if gt in preds[:3]:
            top3 += 1
        if gt in preds[:5]:
            top5 += 1

        if shown < show_n:
            shown += 1
            print("\nFILE:", rel_file)
            print("GT  :", gt_text)
            print("TOP-5:")
            for t, loss in top_list:
                print(f"  {loss:.4f} -> {t}")

    n = max(1, len(picked))
    print("\n=== RESULTS (SUBSET) ===")
    print("N        :", len(picked))
    print("Top-1 acc:", top1 / n)
    print("Top-3 acc:", top3 / n)
    print("Top-5 acc:", top5 / n)

if __name__ == "__main__":
    main()