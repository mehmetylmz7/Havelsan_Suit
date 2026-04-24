import csv
import shutil
from pathlib import Path

import numpy as np
import soundfile as sf
import librosa
from tqdm import tqdm

from audiomentations import (
    AddGaussianNoise,
    TimeStretch,
    PitchShift,
    Gain,
    LowPassFilter,
    HighPassFilter,
    ClippingDistortion,
)

# =========================
# CONFIG
# =========================
IN_ROOT = Path("/home/wololoo/Havelsan_Suit/data/preprocessed/wavs")
OUT_ROOT = Path("/home/wololoo/Havelsan_Suit/data/augmented_dataset")

SAMPLE_RATE = 16000
COPY_ORIGINALS = True
META_NAME = "metadata.csv"

# =========================
# CANONICAL TEXT MAPPING
# =========================
FOLDER_TO_TEXT = {
    "üç_numaralı_trak_designeyt_edildi": "üç numaralı track designate edildi",
    "üç_numaralı_iz_designeyt_edildi": "üç numaralı iz designate edildi",
    "üç_numaralı_traki_çiz": "üç numaralı track’i çiz",
    "treklere_angajman_yap": "track’lere angajman yap",
    "traklara_angajman_yap": "track’lara angajman yap",
    "treklere_engagement_yap": "track’lere engagement yap",
    "traklara_engagement_yap": "track’lara engagement yap",
    "izlere_fix_at": "izlere fix at",
    "traklara_fix_at": "track’lere fix at",
    "treklere_fix_at": "track’lere fix at",
    "kerterizlere_fix_yap": "kerterizlere fix yap",
    "engeyçment_yap": "engagement yap",
    "emercensi_moda_geç": "emergency moda geç",
    "track_three_designate_yap": "track three designate yap",
    "battleshort_durumuna_geç": "battleshort durumuna geç",
    "advent_sistemi_aktif": "advent sistemi aktif",
}

# =========================
# KONTROLLÜ AUGMENT VARYANTLARI
# Her yöntem için sabit 3 varyant
# =========================
AUGMENTATION_VARIANTS = {
    "pitchshift": [
        ("thin", PitchShift(min_semitones=3, max_semitones=4, p=1.0)),
        ("orig", None),
        ("thick", PitchShift(min_semitones=-4, max_semitones=-3, p=1.0)),
    ],
    "timestretch": [
        ("slow", TimeStretch(min_rate=0.84, max_rate=0.90, p=1.0)),
        ("orig", None),
        ("fast", TimeStretch(min_rate=1.10, max_rate=1.16, p=1.0)),
    ],
    "gain": [
        ("low", Gain(min_gain_db=-10, max_gain_db=-6, p=1.0)),
        ("orig", None),
        ("high", Gain(min_gain_db=6, max_gain_db=10, p=1.0)),
    ],
    "gaussian_noise": [
        ("light", AddGaussianNoise(min_amplitude=0.002, max_amplitude=0.006, p=1.0)),
        ("medium", AddGaussianNoise(min_amplitude=0.008, max_amplitude=0.015, p=1.0)),
        ("strong", AddGaussianNoise(min_amplitude=0.018, max_amplitude=0.030, p=1.0)),
    ],
    "lowpass": [
        ("mild", LowPassFilter(min_cutoff_freq=4500, max_cutoff_freq=5500, p=1.0)),
        ("medium", LowPassFilter(min_cutoff_freq=3000, max_cutoff_freq=4000, p=1.0)),
        ("strong", LowPassFilter(min_cutoff_freq=1800, max_cutoff_freq=2500, p=1.0)),
    ],
    "highpass": [
        ("mild", HighPassFilter(min_cutoff_freq=80, max_cutoff_freq=140, p=1.0)),
        ("medium", HighPassFilter(min_cutoff_freq=180, max_cutoff_freq=260, p=1.0)),
        ("strong", HighPassFilter(min_cutoff_freq=320, max_cutoff_freq=500, p=1.0)),
    ],
    "clipping": [
        ("mild", ClippingDistortion(min_percentile_threshold=1, max_percentile_threshold=4, p=1.0)),
        ("medium", ClippingDistortion(min_percentile_threshold=5, max_percentile_threshold=10, p=1.0)),
        ("strong", ClippingDistortion(min_percentile_threshold=12, max_percentile_threshold=20, p=1.0)),
    ],
}

# =========================
# HELPERS
# =========================
def is_augmented_filename(path: Path) -> bool:
    stem = path.stem.lower()
    return "__aug" in stem or "__orig" in stem

def load_wav_mono_16k(path: Path) -> np.ndarray:
    y, _ = librosa.load(str(path), sr=SAMPLE_RATE, mono=True)
    return y.astype(np.float32)

def save_wav(path: Path, y: np.ndarray):
    path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(path), y, SAMPLE_RATE)

def copy_file(src: Path, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)

def relative_to_method_root(method_root: Path, file_path: Path) -> str:
    return file_path.relative_to(method_root).as_posix()

def write_metadata_csv(meta_path: Path, rows):
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    with meta_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["file", "text"])
        writer.writerows(rows)

# =========================
# MAIN
# =========================
def build_augmented_dataset():
    if not IN_ROOT.exists():
        raise FileNotFoundError(f"Girdi dizini yok: {IN_ROOT}")

    OUT_ROOT.mkdir(parents=True, exist_ok=True)

    command_dirs = sorted([p for p in IN_ROOT.iterdir() if p.is_dir()])
    if not command_dirs:
        raise RuntimeError(f"Komut klasörü bulunamadı: {IN_ROOT}")

    print(f"Komut klasörü sayısı: {len(command_dirs)}")

    metadata_rows = {method_name: [] for method_name in AUGMENTATION_VARIANTS.keys()}
    if COPY_ORIGINALS:
        metadata_rows["originals"] = []

    total_originals = 0
    total_generated = {method_name: 0 for method_name in AUGMENTATION_VARIANTS.keys()}

    for cmd_dir in command_dirs:
        cmd_id = cmd_dir.name

        if cmd_id not in FOLDER_TO_TEXT:
            raise KeyError(f"FOLDER_TO_TEXT mapping eksik: '{cmd_id}'")

        clean_text = FOLDER_TO_TEXT[cmd_id]

        wavs = sorted([w for w in cmd_dir.glob("*.wav") if not is_augmented_filename(w)])
        if not wavs:
            print(f"[Uyarı] {cmd_id} içinde wav yok, atlanıyor.")
            continue

        for src_wav in tqdm(wavs, desc=cmd_id):
            total_originals += 1

            y = load_wav_mono_16k(src_wav)
            if y is None or len(y) == 0:
                print(f"[Uyarı] Boş/okunamayan dosya: {src_wav}")
                continue

            base = src_wav.stem

            # -------------------------
            # ORİJİNALLERİ AYRI KLASÖRE KOPYALA
            # -------------------------
            if COPY_ORIGINALS:
                orig_root = OUT_ROOT / "originals"
                dst_orig = orig_root / cmd_id / src_wav.name
                copy_file(src_wav, dst_orig)

                rel_path = relative_to_method_root(orig_root, dst_orig)
                metadata_rows["originals"].append((rel_path, clean_text))

            # -------------------------
            # HER YÖNTEM İÇİN SABİT VARYANTLAR
            # -------------------------
            for method_name, variants in AUGMENTATION_VARIANTS.items():
                method_root = OUT_ROOT / method_name

                for variant_name, augmenter in variants:
                    try:
                        if augmenter is None:
                            y_aug = y.copy()
                        else:
                            y_aug = augmenter(samples=y, sample_rate=SAMPLE_RATE)
                    except Exception as e:
                        print(f"[Hata] {method_name} | {variant_name} | {src_wav.name} | {e}")
                        continue

                    if y_aug is None or len(y_aug) == 0:
                        continue

                    out_name = f"{base}__{method_name}_{variant_name}.wav"
                    dst_aug = method_root / cmd_id / out_name
                    save_wav(dst_aug, y_aug)

                    rel_path = relative_to_method_root(method_root, dst_aug)
                    metadata_rows[method_name].append((rel_path, clean_text))
                    total_generated[method_name] += 1

    # =========================
    # METADATA YAZ
    # =========================
    if COPY_ORIGINALS:
        orig_meta = OUT_ROOT / "originals" / META_NAME
        write_metadata_csv(orig_meta, metadata_rows["originals"])

    for method_name in AUGMENTATION_VARIANTS.keys():
        meta_path = OUT_ROOT / method_name / META_NAME
        write_metadata_csv(meta_path, metadata_rows[method_name])

    # =========================
    # ÖZET
    # =========================
    print("\n=== ÖZET ===")
    print(f"Toplam orijinal dosya sayısı: {total_originals}")

    if COPY_ORIGINALS:
        print(f"[originals] metadata satırı: {len(metadata_rows['originals'])}")
        print(f"[originals] metadata: {OUT_ROOT / 'originals' / META_NAME}")

    for method_name in AUGMENTATION_VARIANTS.keys():
        print(f"[{method_name}] üretilen dosya sayısı: {total_generated[method_name]}")
        print(f"[{method_name}] metadata satırı: {len(metadata_rows[method_name])}")
        print(f"[{method_name}] metadata: {OUT_ROOT / method_name / META_NAME}")

    print(f"\nOUT_ROOT: {OUT_ROOT}")

if __name__ == "__main__":
    build_augmented_dataset()