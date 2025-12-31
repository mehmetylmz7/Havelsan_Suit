import os
from elevenlabs.client import ElevenLabs 

# API anahtarı ortam değişkeninden okunur (güvenli kullanım)
YOUR_API_KEY = os.getenv("ELEVENLABS_API_KEY")
if not YOUR_API_KEY:
    print("Hata: ELEVENLABS_API_KEY ortam değişkeni ayarlı değil. `.env` veya çevresel değişken olarak ayarlayın.")
    exit()

# 1. API İstemcisini Başlatma
try:
    client = ElevenLabs(api_key=YOUR_API_KEY)
except Exception as e:
    print(f"Hata: ElevenLabs istemcisi başlatılamadı. Detay: {e}")
    exit()

# 2. Proje Ayarları
voices = [
    "pa0LgEk5MjYFGCuG6I3V",  
    "Q5n6GDIjpN0pLOlycRFT",  
    "Hvrobr8BhLPfiaSv2cHi",  
    "Xb7hH8MSUJpSbSDYk0k2",   
    "pqHfZKP75CvOlQylNhV4",
    "nPczCjzI2devNBz1zQrb",
    "N2lVS1w4EtoT3dr4eOWO",
    "IKne3meq5aSn9XLyUdCD",
    "iP95p4xoKVk53GoZ742B",
    "2EiwWnXFnvU5JabPnv8n",
]
models = ["eleven_multilingual_v2", "eleven_turbo_v2_5", "eleven_flash_v2_5"]

# Çıktı klasörünü oluştur
output_dir = "outputs"
os.makedirs(output_dir, exist_ok=True)

# GÜNCEL METİN
TEXT_TO_CONVERT = "hedefi track ediyorum"

# Dosya adının temelini oluştur (boşlukları _ ile değiştir)
BASE_FILENAME = TEXT_TO_CONVERT.lower().replace(" ", "_")

print("=" * 60)
print(f"Metin: '{TEXT_TO_CONVERT}' Sese çevriliyor.")
print(f"Denenecek Kombinasyon Sayısı: {len(voices) * len(models)}")
print("Dosyalar şöyle adlandırılacak: {BASE_FILENAME}_01.mp3, {BASE_FILENAME}_02.mp3, ...")
print("=" * 60)

# 3. Ses Üretme Döngüsü
counter = 1 # Ardışık numaralandırma sayacı
total_combinations = len(voices) * len(models)

for model_id in models:
    for voice_id in voices: # Değişken ismini voice_id olarak değiştirdik, daha doğru
        
        # Dosya adını oluştur: BASE_FILENAME + Ardışık Numara (01, 02, 03...)
        # {:02d} formatı, sayıyı iki haneli (01, 02) yapar.
        filename = f"{BASE_FILENAME}_{counter:02d}.mp3"
        filepath = os.path.join(output_dir, filename)

        print(f"| Başlatılıyor ({counter}/{total_combinations}): Ses ID: {voice_id[:8]}..., Model: {model_id}")

        try:
            # API Çağrısı
            audio_stream = client.text_to_speech.convert(
                text=TEXT_TO_CONVERT,
                voice_id=voice_id,
                model_id=model_id,
                output_format="mp3_44100_128" 
            )

            # Ses akışını alıp dosyaya kaydetme
            with open(filepath, 'wb') as f:
                for chunk in audio_stream:
                    if chunk:
                        f.write(chunk)
            
            print(f"| ✅ BAŞARILI: Dosya kaydedildi -> {filepath}")
            counter += 1 # Başarılı kayıttan sonra sayacı artır

        except Exception as e:
            # Hata oluşsa bile, döngü devam etmeli, ancak sayaç artmamalı.
            print(f"| ❌ HATA: Ses ID {voice_id[:8]}... / {model_id} kombinasyonunda sorun oluştu.")
            print(f"| Hata Detayı: {e}")
            
    print("-" * 60)

print("✅ Tüm işlemler tamamlandı.")
print(f"Ses dosyalarını '{output_dir}' klasöründe bulabilirsiniz.")