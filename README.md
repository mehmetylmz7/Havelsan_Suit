# Havelsan Suit - Whisper Fine-Tuning & ASR Web Interface

Sentetik Turkish military voice command verileri ile Whisper small model fine-tuning ve web tabanlı test arayüzü projesi.

## 🎯 Proje Hedefi

1. ElevenLabs API ile sentetik ses verileri üretme
2. 16kHz mono WAV formatına dönüştürme  
3. Whisper small modelini Türkçe askeri komutlar için fine-tune etme
4. Web arayüzünde model performansını test etme

## 📁 Proje Yapısı

```
Havelsan_Suit/
├── data/                          # Veri seti klasörü
│   ├── raw/outputs/              # Ham MP3 dosyaları (16 komut × 24)
│   ├── preprocessed/wavs/        # 16kHz mono WAV'lar
│   ├── transcriptions/           # Metadata ve eşleştirmeler
│   └── dataset/                  # Hugging Face dataset format
├── training/                      # Fine-tuning altyapısı
│   ├── prepare_dataset.py        # Dataset hazırlama
│   ├── train_whisper.py          # Model eğitimi
│   └── checkpoints/              # Model checkpoint'leri
├── web_app/                       # Web arayüzü
│   ├── app.py                    # Flask backend
│   ├── templates/                # HTML şablonlar
│   ├── static/                   # CSS, JS
│   └── models/                   # Fine-tuned model
├── scripts/                       # Yardımcı scriptler
│   ├── audio_generation/         # ElevenLabs ses üretimi
│   └── audio_conversion/         # MP3 → WAV dönüştürme
├── utils/                         # Utility fonksiyonlar
├── commands.json                  # 16 türkçe askeri komut
└── requirements.txt              # Python bağımlılıkları
```

## 🚀 Kurulum

### 1. Python Ortamı
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. FFmpeg (Ses işleme için gerekli)
```bash
sudo apt-get install -y ffmpeg
```

### 3. API Anahtarı (.env dosyası)
```bash
cp .env.example .env
# .env dosyasına ElevenLabs API anahtarınızı ekleyin
```

## 📊 Tam İş Akışı

### Adım 1: Ses Verileri Üretimi (İsteğe bağlı)
Veri zaten mevcut, ancak yeni veri üretmek için:

```bash
cd scripts/audio_generation
python generate_speech.py  # MP3 üretimi
cd ../audio_conversion
python converter.py         # WAV dönüşümü
```

### Adım 2: Dataset Hazırlama
```bash
cd training
python prepare_dataset.py
```

**Çıktı:**
- `data/transcriptions/metadata.csv` - Ses-metin eşleştirmeleri
- `data/dataset/` - Hugging Face Dataset (train/val split)

### Adım 3: Model Fine-Tuning
```bash
python train_whisper.py
```

**Parametreler** (script içinde düzenleyin):
- Model: `openai/whisper-small`
- Learning rate: `1e-5`
- Batch size: `8` (GPU'nuza göre ayarlayın)
- Epochs: `10`

**Çıktı:**
- `training/checkpoints/` - Training checkpoints
- `training/checkpoints/fine_tuned_whisper_small/` - Final model

### Adım 4: Modeli Web App'e Taşıma
```bash
cp -r training/checkpoints/fine_tuned_whisper_small web_app/models/
```

### Adım 5: Web Arayüzünü Başlatma
```bash
cd web_app
python app.py
```

Tarayıcıda: `http://localhost:5000`

## 🌐 Web Arayüzü Özellikleri

### 🎤 Mikrofon Kaydı
- Tarayıcıdan doğrudan ses kaydı
- Real-time playback

### 📁 Dosya Yükleme
- Drag & drop desteği
- WAV/MP3 formatları

### 🤖 Model Seçimi
- Original Whisper Small
- Fine-Tuned Model

### ⚖️ Karşılaştırma Modu
Aynı ses dosyasını her iki modelle test edip sonuçları yan yana görüntüle

## 📋 Komut Listesi

`commands.json` dosyasında 16 Türkçe askeri komut:
- "üç numaralı trak designeyt edildi"
- "traklara angajman yap"
- "treklere engagement yap"
- "izlere fix at"
- ve daha fazlası...

## 🔧 Konfigürasyon

### Fine-Tuning Parametreleri
`training/train_whisper.py` içinde:
```python
LEARNING_RATE = 1e-5
BATCH_SIZE = 8
EPOCHS = 10
```

### Model Path'leri
`web_app/app.py` içinde:
```python
ORIGINAL_MODEL = "openai/whisper-small"
FINETUNED_MODEL_PATH = Path("./models/fine_tuned_whisper_small")
```

## 📊 Değerlendirme

Model performansı **WER (Word Error Rate)** metriği ile ölçülür:
- Training sırasında validation WER
- Final evaluation sonuçları

## 💡 İpuçları

**GPU Kullanımı:**
- CUDA varsa otomatik kullanılır
- CPU'da da çalışır (daha yavaş)

**Memory Optimization:**
- Batch size'ı GPU memory'nize göre ayarlayın
- FP16 precision (GPU'da otomatik aktif)

**Dataset Split:**
- 80% training / 20% validation
- Stratified split (her komuttan dengeli)

## 🆘 Sorun Giderme

**"CUDA out of memory":**
```python
# train_whisper.py içinde batch size'ı düşürün
BATCH_SIZE = 4
```

**"ModuleNotFoundError":**
```bash
pip install -r requirements.txt --upgrade
```

**Web arayüzü mikrofon erişimi:**
- HTTPS veya localhost gerekli
- Tarayıcı izinlerini kontrol edin

## 📄 Lisans
MIT License

---

**Not:** Bu proje eğitim amaçlıdır. Production kullanımı için ek optimizasyonlar gerekebilir.
