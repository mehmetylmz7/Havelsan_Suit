#!/usr/bin/env python3
"""
Ses Augmentasyon Scripti
========================
Her komut klasöründeki mevcut sesleri augmentasyon teknikleriyle çoğaltır.

Mevcut: 24 ses/komut
Hedef : 150 ses/komut (varsayılan)

Augmentasyon teknikleri:
  1. Gürültü ekleme (Gaussian noise)
  2. Hız değiştirme (time stretching)
  3. Pitch kaydırma
  4. Ses seviyesi değiştirme (gain)
  5. Room impulse response (oda yankısı)
  6. Low-pass / High-pass filtre
"""

import os
import shutil
import random
import argparse
import numpy as np
import librosa
import soundfile as sf
from pathlib import Path
from audiomentations import (
    Compose,
    AddGaussianNoise,
    TimeStretch,
    PitchShift,
    Gain,
    LowPassFilter,
    HighPassFilter,
    Shift,
    ClippingDistortion,
)

# ─────────────────────────────────────────────
# Augmentasyon pipeline'ları
# ─────────────────────────────────────────────

def make_pipelines():
    """Farklı augmentasyon kombinasyonlarından oluşan pipeline listesi döndürür."""
    pipelines = [
        # 1. Hafif gürültü
        Compose([AddGaussianNoise(min_amplitude=0.001, max_amplitude=0.010, p=1.0)]),
        # 2. Orta gürültü
        Compose([AddGaussianNoise(min_amplitude=0.010, max_amplitude=0.025, p=1.0)]),
        # 3. Yavaş konuşma
        Compose([TimeStretch(min_rate=0.85, max_rate=0.95, p=1.0)]),
        # 4. Hızlı konuşma
        Compose([TimeStretch(min_rate=1.05, max_rate=1.15, p=1.0)]),
        # 5. Düşük pitch
        Compose([PitchShift(min_semitones=-3, max_semitones=-1, p=1.0)]),
        # 6. Yüksek pitch
        Compose([PitchShift(min_semitones=1, max_semitones=3, p=1.0)]),
        # 7. Ses seviyesi düşük
        Compose([Gain(min_gain_db=-8, max_gain_db=-3, p=1.0)]),
        # 8. Ses seviyesi yüksek
        Compose([Gain(min_gain_db=3, max_gain_db=8, p=1.0)]),
        # 9. Low-pass filtre (bulanık ses)
        Compose([LowPassFilter(min_cutoff_freq=2000, max_cutoff_freq=4000, p=1.0)]),
        # 10. High-pass filtre (ince ses)
        Compose([HighPassFilter(min_cutoff_freq=200, max_cutoff_freq=600, p=1.0)]),
        # 11. Zaman kaydırma
        Compose([Shift(min_shift=-0.1, max_shift=0.1, p=1.0)]),
        # 12. Gürültü + hız
        Compose([
            AddGaussianNoise(min_amplitude=0.003, max_amplitude=0.012, p=1.0),
            TimeStretch(min_rate=0.90, max_rate=1.10, p=1.0),
        ]),
        # 13. Gürültü + pitch kaydırma
        Compose([
            AddGaussianNoise(min_amplitude=0.003, max_amplitude=0.012, p=1.0),
            PitchShift(min_semitones=-2, max_semitones=2, p=1.0),
        ]),
        # 14. Hafif distortion
        Compose([ClippingDistortion(min_percentile_threshold=90, max_percentile_threshold=97, p=1.0)]),
        # 15. Kompleks kombinasyon
        Compose([
            AddGaussianNoise(min_amplitude=0.002, max_amplitude=0.008, p=0.8),
            TimeStretch(min_rate=0.92, max_rate=1.08, p=0.8),
            PitchShift(min_semitones=-1, max_semitones=1, p=0.8),
            Gain(min_gain_db=-4, max_gain_db=4, p=0.8),
        ]),
    ]
    return pipelines


def load_audio(path: Path, target_sr: int = 16000):
    """MP3/WAV ses dosyasını yükler, mono + hedef SR'ye dönüştürür."""
    audio, sr = librosa.load(str(path), sr=target_sr, mono=True)
    return audio, sr


def save_audio(audio: np.ndarray, sr: int, out_path: Path):
    """Ses verisini WAV olarak kaydeder."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(out_path), audio, sr, subtype="PCM_16")


def augment_directory(
    input_dir: Path,
    output_dir: Path,
    target_count: int = 150,
    target_sr: int = 16000,
    seed: int = 42,
):
    """
    Bir komut klasöründeki sesleri augmentasyon ile `target_count` adede çıkartır.

    Orijinal dosyalar olduğu gibi kopyalanır, ardından eksik kalan sayı kadar
    augmente kopya oluşturulur.
    """
    random.seed(seed)
    np.random.seed(seed)

    src_files = sorted(input_dir.glob("*.mp3")) + sorted(input_dir.glob("*.wav"))
    if not src_files:
        print(f"  [UYARI] Ses dosyası bulunamadı: {input_dir}")
        return

    cmd_name = input_dir.name
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Orijinalleri kopyala (WAV'a dönüştür)
    originals_out = []
    for i, src in enumerate(src_files, start=1):
        audio, sr = load_audio(src, target_sr)
        dst = output_dir / f"{cmd_name}_{i:03d}.wav"
        save_audio(audio, sr, dst)
        originals_out.append((audio, sr, i))
    
    existing_count = len(originals_out)
    print(f"  Orijinal: {existing_count} dosya kopyalandı")

    if existing_count >= target_count:
        print(f"  Zaten {existing_count} dosya var, augmentasyon gerekmez.")
        return

    # 2. Augmentasyon ile doldurun
    pipelines = make_pipelines()
    needed = target_count - existing_count
    aug_idx = existing_count + 1

    pipeline_cycle = 0
    while needed > 0:
        # Kaynak ses rastgele seç
        audio, sr, _ = random.choice(originals_out)
        
        # Pipeline döngüsel seç
        pipeline = pipelines[pipeline_cycle % len(pipelines)]
        pipeline_cycle += 1

        try:
            aug_audio = pipeline(samples=audio.copy(), sample_rate=sr)
        except Exception as e:
            print(f"    [HATA] Augmentasyon başarısız: {e}, atlanıyor...")
            continue

        dst = output_dir / f"{cmd_name}_{aug_idx:03d}_aug.wav"
        save_audio(aug_audio, sr, dst)
        aug_idx += 1
        needed -= 1

    total = len(list(output_dir.glob("*.wav")))
    print(f"  Augmentasyon tamamlandı → toplam {total} dosya")


def main():
    parser = argparse.ArgumentParser(
        description="Ses augmentasyon scripti – komut seslerini çoğaltır"
    )
    parser.add_argument(
        "--input_dir",
        type=str,
        default="/home/wololoo/Havelsan_Suit/data/raw/outputs",
        help="Komut klasörlerinin bulunduğu ana dizin",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="/home/wololoo/Havelsan_Suit/data/augmented",
        help="Augmente edilmiş seslerin kaydedileceği dizin",
    )
    parser.add_argument(
        "--target",
        type=int,
        default=150,
        help="Her komut için hedef ses sayısı (varsayılan: 150)",
    )
    parser.add_argument(
        "--sr",
        type=int,
        default=16000,
        help="Hedef örnekleme frekansı Hz (varsayılan: 16000)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Rastgelelik tohumu (varsayılan: 42)",
    )
    args = parser.parse_args()

    input_root = Path(args.input_dir)
    output_root = Path(args.output_dir)

    cmd_dirs = sorted([d for d in input_root.iterdir() if d.is_dir()])
    if not cmd_dirs:
        print("Komut klasörü bulunamadı!")
        return

    print(f"\n{'='*55}")
    print(f"  Augmentasyon Başlıyor")
    print(f"  Giriş : {input_root}")
    print(f"  Çıkış : {output_root}")
    print(f"  Hedef : {args.target} ses/komut")
    print(f"  SR    : {args.sr} Hz")
    print(f"{'='*55}\n")

    for cmd_dir in cmd_dirs:
        print(f"[{cmd_dir.name}]")
        augment_directory(
            input_dir=cmd_dir,
            output_dir=output_root / cmd_dir.name,
            target_count=args.target,
            target_sr=args.sr,
            seed=args.seed,
        )
        print()

    print("✅ Tüm komutlar işlendi!")
    print(f"   Sonuçlar: {output_root}\n")


if __name__ == "__main__":
    main()
