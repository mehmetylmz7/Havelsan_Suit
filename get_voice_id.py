import os
# Yeni kütüphane yapısına uygun doğru içe aktarma
from elevenlabs.client import ElevenLabs 
# Buraya kendi API anahtarını gir
client = ElevenLabs(api_key="3a59981d712e9a7357489c9b2cd8058ba34157b9b0061468790ca349b8e66d05")

# Mevcut tüm sesleri listele
voices = client.voices.get_all()

# Rachel, Antoni, Domi, Elli seslerini bul
target_names = ["Rachel", "Antoni", "Domi", "Elli"]

for voice in voices.voices:
    if voice.name in target_names:
        print(f"{voice.name}: {voice.voice_id}")
