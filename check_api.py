import os
from elevenlabs.client import ElevenLabs

# API ANAHTARINIZ (Kod içinde güvensiz kullanım)
YOUR_API_KEY = "3a59981d712e9a7357489c9b2cd8058ba34157b9b0061468790ca349b8e66d05" 

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