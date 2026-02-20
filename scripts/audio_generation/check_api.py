import os
from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

# API anahtarını ortam değişkeninden al
YOUR_API_KEY = os.getenv("ELEVENLABS_API_KEY")
if not YOUR_API_KEY:
    print("❌ HATA: ELEVENLABS_API_KEY ortam değişkeni ayarlı değil.")
    print("Lütfen .env dosyasında ELEVENLABS_API_KEY değişkenini tanımlayın.")
    exit(1)
 

print("=========================================")
print("ElevenLabs API Anahtarı Kontrol Ediliyor...")
print("=========================================")

try:
    # 1. İstemciyi API Anahtarı ile başlat
    client = ElevenLabs(api_key=YOUR_API_KEY)
    
    # 2. Sesleri Listeleme API çağrısı yap
    # Bu, API anahtarının geçerli olup olmadığını kontrol etmenin en kolay yoludur.
    voices = client.voices.get_all()
    
    # 3. Sonuçları yazdır
    print(f"✅ BAŞARILI: API Anahtarı geçerli.")
    print(f"Toplam {len(voices.voices)} ses bulundu.")
    print("İlk 3 ses:")
    for i, voice in enumerate(voices.voices[:3]):
        print(f"  - {voice.name} (ID: {voice.voice_id[:8]}...)")

except Exception as e:
    # Hata, genellikle 401 Unauthorized (Yetkisiz) olacaktır.
    if "401 Unauthorized" in str(e):
        print("❌ HATA: API Anahtarı GEÇERSİZ veya YETKİSİZ.")
        print("Lütfen API anahtarınızı kontrol edin ve doğru olduğundan emin olun.")
    else:
        print(f"❌ BEKLENMEDİK HATA OLUŞTU:")
        print(f"Hata Detayı: {e}")

print("=========================================")