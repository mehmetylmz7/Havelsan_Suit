import csv
import shutil
from pathlib import Path

# =========================
# CONFIG
# =========================
AUG_ROOT = Path("/home/wololoo/Havelsan_Suit/data/augmented_dataset")
OUT_ROOT = Path("/home/wololoo/Havelsan_Suit/data/full_augmented_dataset")
META_NAME = "metadata.csv"

# originals klasörünü dahil et
INCLUDE_ORIGINALS = True

# yöntem klasörlerindeki *_orig.wav varyantlarını dahil etme
SKIP_METHOD_ORIG_VARIANTS = True

METHOD_DIRS = [
    "pitchshift",
    "timestretch",
    "gain",
    "gaussian_noise",
    "lowpass",
    "highpass",
    "clipping",
]

# =========================
# HELPERS
# =========================
def read_metadata(meta_path: Path):
    rows = []
    with meta_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append((row["file"], row["text"]))
    return rows

def copy_with_parents(src: Path, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)

def is_method_orig_variant(rel_path: str) -> bool:
    return rel_path.endswith("_orig.wav")

# =========================
# MAIN
# =========================
def build_full_dataset():
    if not AUG_ROOT.exists():
        raise FileNotFoundError(f"AUG_ROOT yok: {AUG_ROOT}")

    OUT_ROOT.mkdir(parents=True, exist_ok=True)

    final_rows = []
    copied_count = 0
    skipped_count = 0

    # -------------------------
    # 1) originals
    # -------------------------
    if INCLUDE_ORIGINALS:
        orig_root = AUG_ROOT / "originals"
        orig_meta = orig_root / META_NAME

        if not orig_meta.exists():
            raise FileNotFoundError(f"originals metadata bulunamadı: {orig_meta}")

        orig_rows = read_metadata(orig_meta)

        for rel_path, text in orig_rows:
            src = orig_root / rel_path
            dst = OUT_ROOT / rel_path

            if not src.exists():
                print(f"[Uyarı] Eksik dosya: {src}")
                skipped_count += 1
                continue

            copy_with_parents(src, dst)
            final_rows.append((rel_path, text))
            copied_count += 1

    # -------------------------
    # 2) tüm augment klasörleri
    # -------------------------
    for method_name in METHOD_DIRS:
        method_root = AUG_ROOT / method_name
        method_meta = method_root / META_NAME

        if not method_meta.exists():
            print(f"[Uyarı] metadata yok, atlanıyor: {method_meta}")
            continue

        method_rows = read_metadata(method_meta)

        for rel_path, text in method_rows:
            if SKIP_METHOD_ORIG_VARIANTS and is_method_orig_variant(rel_path):
                skipped_count += 1
                continue

            src = method_root / rel_path
            dst = OUT_ROOT / rel_path

            if not src.exists():
                print(f"[Uyarı] Eksik dosya: {src}")
                skipped_count += 1
                continue

            copy_with_parents(src, dst)
            final_rows.append((rel_path, text))
            copied_count += 1

    # -------------------------
    # 3) final metadata.csv
    # -------------------------
    final_meta = OUT_ROOT / META_NAME
    with final_meta.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["file", "text"])
        writer.writerows(final_rows)

    print("\n=== FULL DATASET ÖZET ===")
    print(f"Kopyalanan dosya sayısı: {copied_count}")
    print(f"Atlanan dosya sayısı: {skipped_count}")
    print(f"Metadata satırı: {len(final_rows)}")
    print(f"Final metadata: {final_meta}")
    print(f"Final dataset root: {OUT_ROOT}")

if __name__ == "__main__":
    build_full_dataset()