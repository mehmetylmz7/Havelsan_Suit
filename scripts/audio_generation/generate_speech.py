import os
import json
from elevenlabs.client import ElevenLabs
from dotenv import load_dotenv

# .env dosyasını yükle
load_dotenv()

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

# 2. Komutları commands.json dosyasından oku
try:
    with open("commands.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        commands = data.get("commands", [])
    if not commands:
        print("Hata: commands.json dosyasında komut bulunamadı.")
        exit()
    print(f"✅ {len(commands)} komut başarıyla yüklendi.")
except FileNotFoundError:
    print("Hata: commands.json dosyası bulunamadı.")
    exit()
except json.JSONDecodeError as e:
    print(f"Hata: commands.json dosyası geçersiz JSON formatında. Detay: {e}")
    exit()

# 3. Proje Ayarları
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

print("=" * 80)
print(f"📋 Toplam {len(commands)} komut için ses üretilecek.")
print(f"🎙️  Her komut için {len(voices) * len(models)} farklı ses kombinasyonu oluşturulacak.")
print("=" * 80)

# 4. Her komut için ses üretme döngüsü
for cmd_index, command_text in enumerate(commands, start=1):
    
    # Her komut için ayrı klasör oluştur
    command_folder_name = command_text.lower().replace(" ", "_")[:50]  # İlk 50 karakter
    command_output_dir = os.path.join(output_dir, command_folder_name)
    os.makedirs(command_output_dir, exist_ok=True)
    
    print("\n" + "=" * 80)
    print(f"🎯 Komut {cmd_index}/{len(commands)}: '{command_text}'")
    print(f"📁 Klasör: {command_output_dir}")
    print("=" * 80)
    
    counter = 1  # Her komut için sayacı sıfırla
    total_combinations = len(voices) * len(models)
    
    for model_id in models:
        for voice_id in voices:
            
            # Dosya adını oluştur
            filename = f"{command_folder_name}_{counter:02d}.mp3"
            filepath = os.path.join(command_output_dir, filename)
            
            print(f"| Başlatılıyor ({counter}/{total_combinations}): Ses ID: {voice_id[:8]}..., Model: {model_id}")
            
            try:
                # API Çağrısı
                audio_stream = client.text_to_speech.convert(
                    text=command_text,
                    voice_id=voice_id,
                    model_id=model_id,
                    output_format="mp3_44100_128"
                )
                
                # Ses akışını alıp dosyaya kaydetme
                with open(filepath, 'wb') as f:
                    for chunk in audio_stream:
                        if chunk:
                            f.write(chunk)
                
                print(f"| ✅ BAŞARILI: Dosya kaydedildi -> {filename}")
                counter += 1
                
            except Exception as e:
                print(f"| ❌ HATA: Ses ID {voice_id[:8]}... / {model_id} kombinasyonunda sorun oluştu.")
                print(f"| Hata Detayı: {e}")
        
        print("-" * 80)

print("\n" + "=" * 80)
print("✅ Tüm işlemler tamamlandı!")
print(f"📂 Ses dosyalarını '{output_dir}' klasöründe bulabilirsiniz.")
print(f"📊 Toplam {len(commands)} komut işlendi.")
print("=" * 80)