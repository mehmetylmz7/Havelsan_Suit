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
 

def get_all_voice_ids(api_key: str):
    """ElevenLabs API'sinden hesaptaki tüm seslerin ID'lerini çeker."""
    
    print("=========================================")
    print("🔎 ElevenLabs Hesabınızdaki TÜM Ses ID'leri Aranıyor...")
    print("=========================================")

    try:
        # 1. İstemciyi başlat
        client = ElevenLabs(api_key=api_key)
        
        # 2. Tüm sesleri API'den çek
        all_voices = client.voices.get_all()
        
        # 3. Sonuçları listele
        print(f"\n✅ BAŞARILI: Hesabınızda toplam {len(all_voices.voices)} adet ses bulundu.")
        print("-----------------------------------------")
        
        voice_map = {}
        for voice in all_voices.voices:
            voice_map[voice.name] = voice.voice_id
            print(f"  - Ses Adı: {voice.name.ljust(15)} ID: '{voice.voice_id}'")
            
        print("-----------------------------------------")
        print("\nNOT: Bu ID'lerden herhangi birini 'generate_speech.py' dosyanızda kullanabilirsiniz.")
        return voice_map
            
    except Exception as e:
        print(f"\n❌ HATA: Ses ID'lerini çekerken bir sorun oluştu.")
        if "401 Unauthorized" in str(e):
             print("Hata Detayı: API Anahtarı GEÇERSİZ veya YETKİSİZ.")
        elif "failure in name resolution" in str(e):
             print("Hata Detayı: Ağ bağlantısı veya DNS çözünürlüğü hatası.")
             print("Lütfen internet bağlantınızı ve DNS ayarlarınızı kontrol edin.")
        else:
             print(f"Hata Detayı: {e}")
        return {}

if __name__ == "__main__":
    get_all_voice_ids(YOUR_API_KEY)