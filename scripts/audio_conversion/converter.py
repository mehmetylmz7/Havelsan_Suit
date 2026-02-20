from pydub import AudioSegment
import os
import glob
from pathlib import Path

# --- YAPILANDIRMA ---
# Çıktı dosyalarının kaydedileceği ana klasör (kaynak klasörden bağımsız)
OUTPUT_BASE_DIR = "/home/wololoo/Havelsan_Suit/wavs"
TARGET_RATE = 16000 # 16 kHz
TARGET_CHANNELS = 1 # Mono

def mp3_to_16khz_mono_wav(input_mp3_path, output_wav_path):
    """
    Tek bir MP3 dosyasını 16 kHz, mono, PCM WAV formatına dönüştürür.
    """
    try:
        # 1. MP3 dosyasını yükle
        audio = AudioSegment.from_mp3(input_mp3_path)
        
        # 2. Örnekleme hızını (Sample Rate) 16000 Hz'e ayarla
        audio = audio.set_frame_rate(TARGET_RATE)
        
        # 3. Kanal sayısını 1'e ayarla (Mono)
        audio = audio.set_channels(TARGET_CHANNELS)
        
        # 4. WAV formatında dışa aktar (PCM 16-bit Little Endian)
        audio.export(
            output_wav_path, 
            format="wav", 
            parameters=["-acodec", "pcm_s16le"] 
        )
        return True
    except FileNotFoundError:
        print("\n❌ HATA: FFmpeg veya Libav bulunamadı. Lütfen kurun ve sistem PATH'ine ekleyin.")
        # Hata durumunda, toplu işlemi durdurmak için False döndür
        return False 
    except Exception as e:
        print(f"❌ Dönüşüm hatası ({Path(input_mp3_path).name}): {e}")
        return False

def batch_convert_mp3s(source_directory):
    """
    Belirtilen klasördeki tüm MP3 dosyalarını dönüştürür.
    Tüm WAV dosyaları kaynak klasörün adıyla oluşturulan tek bir klasöre kaydedilir.
    Örnek: outputs/komut_adi/*.mp3 -> wavs/komut_adi/*.wav
    """
    source_path = Path(source_directory)
    
    if not source_path.is_dir():
        print(f"❌ Hata: Belirtilen yol bir klasör değil veya bulunamadı: {source_directory}")
        return

    # Kaynak klasörün adını al (örn: "traklara_angajman_yap")
    command_name = source_path.name
    
    # Çıktı klasörünü oluştur: wavs/komut_adi/
    output_dir = Path(OUTPUT_BASE_DIR) / command_name
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"📂 Kaynak klasör: {source_path}")
    print(f"📂 Çıktı klasörü: {output_dir}")

    # Klasördeki tüm MP3 dosyalarını bul
    mp3_files = list(source_path.glob("*.mp3"))
    
    if not mp3_files:
        print(f"⚠️ Uyarı: '{source_directory}' klasöründe hiçbir MP3 dosyası bulunamadı.")
        return

    print(f"\nToplam {len(mp3_files)} dosya bulundu. Dönüşüm başlıyor...")
    
    success_count = 0
    
    for input_file_path in mp3_files:
        file_name_stem = input_file_path.stem
        
        # WAV dosyasını doğrudan komut klasörüne kaydet
        output_file_path = output_dir / f"{file_name_stem}.wav"
        
        print(f"\n🔄 Dönüştürülüyor: {input_file_path.name}")

        # Dönüşüm fonksiyonunu çağır
        if mp3_to_16khz_mono_wav(str(input_file_path), str(output_file_path)):
            # Eğer FFmpeg hatası almışsak (False dönmüşse), döngüden çık
            if not os.path.exists(output_file_path): 
                break
            print(f"   ✅ Başarılı -> {command_name}/{output_file_path.name}")
            success_count += 1
        else:
            print(f"   ❌ Başarısız. Bu dosya atlanıyor.")
            # FFmpeg hatası durumunda, diğer dosyaları denemek anlamsızdır.
            if not os.path.exists(output_file_path): 
                break


    print(f"\n--- İŞLEM BİTTİ ---")
    print(f"Toplam dosya: {len(mp3_files)}")
    print(f"Başarılı dönüştürülen: {success_count}")
    print(f"Kaydedilen klasör: {output_dir}")


# --- KULLANIM: KAYNAK KLASÖR YOLUNUZ BURADA ---
# MP3 dosyalarının bulunduğu ana klasör (alt klasörler otomatik işlenir)
source_dir = "/home/wololoo/Havelsan_Suit/outputs"

# NOT: Çıktılar OUTPUT_BASE_DIR değişkeninde belirtilen konuma kaydedilir (satır 8)
# Varsayılan: /home/wololoo/Havelsan_Suit/wavs/
# Yapı: wavs/komut_adi/*.wav (her komutun tüm varyantları tek klasörde)

if __name__ == "__main__":
    source_path = Path(source_dir)
    
    # Eğer outputs klasörüyse, tüm alt klasörleri işle
    if source_path.name == "outputs" or "outputs" in str(source_path):
        print(f"🔍 '{source_path}' içindeki tüm alt klasörler taranacak...")
        subdirs = [d for d in source_path.iterdir() if d.is_dir()]
        
        if not subdirs:
            print("⚠️ Alt klasör bulunamadı.")
        else:
            print(f"📁 Toplam {len(subdirs)} alt klasör bulundu.\n")
            for subdir in subdirs:
                print(f"\n{'='*80}")
                print(f"📂 İşleniyor: {subdir.name}")
                print(f"{'='*80}")
                batch_convert_mp3s(str(subdir))
    else:
        # Tek klasör işle
        batch_convert_mp3s(source_dir)