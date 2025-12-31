from pydub import AudioSegment
import os
import glob
from pathlib import Path

# --- YAPILANDIRMA ---
OUTPUT_SUBFOLDER_NAME = "16khz_mono_WAV_Cikti"
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
    Belirtilen klasördeki tüm MP3 dosyalarını dönüştürür ve alt klasöre kaydeder.
    """
    source_path = Path(source_directory)
    
    if not source_path.is_dir():
        print(f"❌ Hata: Belirtilen yol bir klasör değil veya bulunamadı: {source_directory}")
        return

    # Çıktı klasörünü oluştur
    output_path = source_path / OUTPUT_SUBFOLDER_NAME
    output_path.mkdir(exist_ok=True)
    print(f"📂 Çıktılar bu klasöre kaydedilecek: {output_path}")

    # Klasördeki tüm MP3 dosyalarını bul
    mp3_files = list(source_path.glob("*.mp3"))
    
    if not mp3_files:
        print(f"⚠️ Uyarı: '{source_directory}' klasöründe hiçbir MP3 dosyası bulunamadı.")
        return

    print(f"\nToplam {len(mp3_files)} dosya bulundu. Dönüşüm başlıyor...")
    
    success_count = 0
    
    for input_file_path in mp3_files:
        file_name_stem = input_file_path.stem
        output_file_path = output_path / f"{file_name_stem}.wav"
        
        print(f"\n🔄 Dönüştürülüyor: {input_file_path.name}")

        # Dönüşüm fonksiyonunu çağır
        if mp3_to_16khz_mono_wav(str(input_file_path), str(output_file_path)):
            # Eğer FFmpeg hatası almışsak (False dönmüşse), döngüden çık
            if not os.path.exists(output_file_path): 
                break
            print(f"   ✅ Başarılı -> {output_file_path.name}")
            success_count += 1
        else:
            print(f"   ❌ Başarısız. Bu dosya atlanıyor.")
            # FFmpeg hatası durumunda, diğer dosyaları denemek anlamsızdır.
            if not os.path.exists(output_file_path): 
                break


    print(f"\n--- İŞLEM BİTTİ ---")
    print(f"Toplam dosya: {len(mp3_files)}")
    print(f"Başarılı dönüştürülen: {success_count}")
    print(f"Kaydedilen klasör: {output_path}")


# --- KULLANIM: DOSYA YOLUNUZ BURADA ---
source_dir = "/home/didim_mehmet/Desktop/veri_seti/hedefi_track_ediyorum"

batch_convert_mp3s(source_dir)