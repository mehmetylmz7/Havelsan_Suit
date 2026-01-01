# Havelsan Suit - ElevenLabs Ses Üretim ve Dönüştürme Araçları

ElevenLabs API kullanarak Türkçe komutlar için ses dosyaları üreten ve MP3'leri WAV formatına dönüştüren kapsamlı araç seti.

## 🚀 Kurulum

### 1. Python Sanal Ortamını Aktif Edin
```bash
source venv/bin/activate
```

### 2. Bağımlılıkları Kurun
```bash
pip install -r requirements.txt
```

### 3. FFmpeg Kurulumu (converter.py için gerekli)
```bash
sudo apt-get install -y ffmpeg
```

### 4. API Anahtarını Ayarlayın
`.env.example` dosyasını `.env` olarak kopyalayın:
```bash
cp .env.example .env
```

`.env` dosyasını düzenleyin ve kendi ElevenLabs API anahtarınızı ekleyin:
```env
ELEVENLABS_API_KEY=gerçek_api_anahtarınız_buraya
```

## 📋 Kullanılabilir Scriptler

### 1. `check_api.py` - API Anahtarı Kontrolü
API anahtarınızın geçerli olup olmadığını kontrol eder.

**Kullanım:**
```bash
python check_api.py
```

**Çıktı:**
- API anahtarı geçerliyse: Hesaptaki ses sayısı ve ilk 3 ses
- API anahtarı geçersizse: Hata mesajı

---

### 2. `find_voices.py` - Ses ID'lerini Bulma
Hesabınızdaki tüm seslerin ID'lerini ve isimlerini listeler.

**Kullanım:**
```bash
python find_voices.py
```

**Çıktı:**
- Tüm seslerin adları ve ID'leri
- Bu ID'leri `generate_speech.py` içinde kullanabilirsiniz

---

### 3. `generate_speech.py` - Toplu Ses Üretimi
`commands.json` dosyasındaki tüm komutlar için ses dosyaları üretir.

**Kullanım:**
```bash
python generate_speech.py
```

**Özellikler:**
- `commands.json` dosyasından komutları okur (şu anda 16 komut)
- Her komut için 30 farklı varyasyon oluşturur (10 ses × 3 model)
- Toplam ~480 ses dosyası üretir
- Çıktılar `outputs/` klasöründe komut bazlı organize edilir

**Çıktı Yapısı:**
```
outputs/
├── üç_numaralı_trak_designeyt_edildi/
│   ├── üç_numaralı_trak_designeyt_edildi_01.mp3
│   ├── üç_numaralı_trak_designeyt_edildi_02.mp3
│   └── ...
├── traklara_angajman_yap/
│   ├── traklara_angajman_yap_01.mp3
│   └── ...
└── ...
```

---

### 4. `converter.py` - MP3 → WAV Dönüştürücü
MP3 dosyalarını 16kHz mono PCM WAV formatına toplu dönüştürür.

**Kullanım:**
```bash
python converter.py
```

**Özellikler:**
- `outputs/` klasöründeki tüm alt klasörleri otomatik tarar
- Her MP3'ü 16kHz, mono, PCM WAV formatına dönüştürür
- Çıktılar `wavs/` klasöründe komut bazlı organize edilir
- FFmpeg kullanır (kurulu olmalı)

**Çıktı Yapısı:**
```
wavs/
├── üç_numaralı_trak_designeyt_edildi/
│   ├── üç_numaralı_trak_designeyt_edildi_01.wav
│   ├── üç_numaralı_trak_designeyt_edildi_02.wav
│   └── ...
├── traklara_angajman_yap/
│   ├── traklara_angajman_yap_01.wav
│   └── ...
└── ...
```

**Yapılandırma:**
`converter.py` dosyasındaki bu değişkenleri düzenleyebilirsiniz:
- `OUTPUT_BASE_DIR`: Çıktı klasörü (varsayılan: `/home/wololoo/Havelsan_Suit/wavs`)
- `TARGET_RATE`: Örnekleme hızı (varsayılan: 16000 Hz)
- `TARGET_CHANNELS`: Kanal sayısı (varsayılan: 1 - Mono)

---

## 📁 Proje Yapısı
```
Havelsan_Suit/
├── .env                    # API anahtarı (GİZLİ - git'e eklenmez)
├── .env.example            # .env şablonu
├── commands.json           # Komut listesi (16 komut)
├── check_api.py            # API test scripti
├── find_voices.py          # Ses ID bulma scripti
├── generate_speech.py      # Ana ses üretim scripti
├── converter.py            # MP3 → WAV dönüştürücü
├── requirements.txt        # Python bağımlılıkları
├── outputs/                # Üretilen MP3 dosyaları
│   ├── komut_1/
│   └── komut_2/
└── wavs/                   # Dönüştürülen WAV dosyaları
    ├── komut_1/
    └── komut_2/
```

## 🔄 Tam İş Akışı

### Adım 1: Sesleri Kontrol Edin
```bash
python find_voices.py
```

### Adım 2: Ses Dosyaları Üretin
```bash
python generate_speech.py
```

### Adım 3: MP3'leri WAV'a Dönüştürün
```bash
python converter.py
```

## ⚙️ Yapılandırma

### Komut Listesini Düzenleme
`commands.json` dosyasını düzenleyerek yeni komutlar ekleyebilir veya mevcut komutları değiştirebilirsiniz:

```json
{
    "commands": [
        "yeni komut 1",
        "yeni komut 2"
    ]
}
```

### Ses ve Model Seçimi
`generate_speech.py` dosyasındaki `voices` ve `models` listelerini düzenleyerek kullanılacak sesleri ve modelleri değiştirebilirsiniz.

## ⚠️ Önemli Notlar
- `.env` dosyasını **asla** git'e yüklemeyin
- API anahtarınızı kimseyle paylaşmayın
- Ses üretimi API kullanım kotanızı tüketir
- FFmpeg, MP3 → WAV dönüşümü için gereklidir
- Tüm scriptler `.env` dosyasından API anahtarını okur

## 📦 Bağımlılıklar
- `elevenlabs` - ElevenLabs API istemcisi
- `python-dotenv` - Ortam değişkeni yönetimi
- `pydub` - Ses dosyası işleme
- `ffmpeg` - Ses formatı dönüştürme (sistem paketi)

## 🆘 Sorun Giderme

### "ModuleNotFoundError: No module named 'pydub'"
```bash
pip install pydub
```

### "Couldn't find ffmpeg or avconv"
```bash
sudo apt-get install -y ffmpeg
```

### "ELEVENLABS_API_KEY ortam değişkeni ayarlı değil"
`.env` dosyasını oluşturun ve API anahtarınızı ekleyin.

## 📄 Lisans
Bu proje MIT lisansı altında lisanslanmıştır.
