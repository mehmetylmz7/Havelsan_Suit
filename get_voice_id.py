import os
# Yeni kütüphane yapısına uygun doğru içe aktarma
from elevenlabs.client import ElevenLabs 

from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

# API anahtarını ortam değişkeninden al
YOUR_API_KEY = os.getenv("ELEVENLABS_API_KEY")
# Buraya kendi API anahtarını gir
client = ElevenLabs(api_key=YOUR_API_KEY)

# Mevcut tüm sesleri listele
voices = client.voices.get_all()

# Rachel, Antoni, Domi, Elli seslerini bul
target_names = ["Rachel", "Antoni", "Domi", "Elli"]

for voice in voices.voices:
    if voice.name in target_names:
        print(f"{voice.name}: {voice.voice_id}")
