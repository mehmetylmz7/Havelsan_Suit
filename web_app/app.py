# =============================================================================
# EVENTLET (Realtime için ZORUNLU)
# =============================================================================
import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import torch
from transformers import WhisperProcessor, WhisperForConditionalGeneration
import librosa
from pathlib import Path
import io
import numpy as np
import base64

# =============================================================================
# Flask setup
# =============================================================================
app = Flask(__name__)
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# =============================================================================
# PATHS
# =============================================================================
BASE_DIR = Path(__file__).resolve().parent          # Havelsan_Suit/web_app
MODELS_DIR = BASE_DIR.parent / "models"             # Havelsan_Suit/models

BASE_MODEL_FALLBACK = "sgangireddy/whisper-small-tr"

# =============================================================================
# Global model cache
# =============================================================================
models_cache = {}

# =============================================================================
# Realtime audio buffers
# =============================================================================
audio_buffers = {}          # sid -> np.array
SAMPLE_RATE = 16000
CHUNK_SECONDS = 0.5          # 0.5 saniyelik chunk

# =============================================================================
# Model discovery
# =============================================================================
def discover_models():
    models = []

    models.append({
        "id": "huggingface-base",
        "name": "Whisper Small TR (HuggingFace)",
        "path": BASE_MODEL_FALLBACK,
        "type": "huggingface",
        "size": "N/A"
    })

    if not MODELS_DIR.exists():
        return models

    for model_dir in MODELS_DIR.iterdir():
        if not model_dir.is_dir():
            continue

        if (model_dir / "config.json").exists() and (
            (model_dir / "model.safetensors").exists() or
            (model_dir / "pytorch_model.bin").exists()
        ):
            size_bytes = sum(
                f.stat().st_size for f in model_dir.rglob("*") if f.is_file()
            )
            size_mb = size_bytes / (1024 * 1024)

            models.append({
                "id": f"local-{model_dir.name}",
                "name": model_dir.name,
                "path": str(model_dir),
                "type": "local",
                "size": f"{size_mb:.1f} MB"
            })

    return models

# =============================================================================
# Model loader
# =============================================================================
def load_model(model_info):
    model_id = model_info["id"]

    if model_id in models_cache:
        return models_cache[model_id]

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model_path = model_info["path"]

    print(f"📥 Loading model: {model_info['name']}")

    processor = WhisperProcessor.from_pretrained(
        model_path,
        language="turkish",
        task="transcribe"
    )

    model = WhisperForConditionalGeneration.from_pretrained(model_path)
    model.to(device)
    model.eval()

    forced_ids = processor.get_decoder_prompt_ids(
        language="turkish",
        task="transcribe"
    )
    model.generation_config.forced_decoder_ids = forced_ids

    models_cache[model_id] = (processor, model, device)
    return processor, model, device

# =============================================================================
# Transcription
# =============================================================================
def transcribe_audio(audio_data, sample_rate, model_info):
    processor, model, device = load_model(model_info)

    if sample_rate != SAMPLE_RATE:
        audio_data = librosa.resample(
            y=audio_data,
            orig_sr=sample_rate,
            target_sr=SAMPLE_RATE
        )

    inputs = processor(
        audio_data,
        sampling_rate=SAMPLE_RATE,
        return_tensors="pt"
    )

    input_features = inputs.input_features.to(device)

    with torch.no_grad():
        predicted_ids = model.generate(input_features)

    return processor.batch_decode(
        predicted_ids,
        skip_special_tokens=True
    )[0]

# =============================================================================
# HTTP Routes
# =============================================================================
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/models")
def get_models():
    return jsonify({"success": True, "models": discover_models()})

@app.route("/transcribe", methods=["POST"])
def transcribe():
    if "audio" not in request.files:
        return jsonify({"error": "Ses dosyası bulunamadı"}), 400

    model_id = request.form.get("model_id", "huggingface-base")
    model_info = next(
        (m for m in discover_models() if m["id"] == model_id),
        None
    )

    audio_bytes = request.files["audio"].read()
    audio_data, sr = librosa.load(io.BytesIO(audio_bytes), sr=None, mono=True)

    text = transcribe_audio(audio_data, sr, model_info)

    return jsonify({
        "success": True,
        "model": model_info["name"],
        "transcription": text
    })

# =============================================================================
# REALTIME SOCKET.IO
# =============================================================================
@socketio.on("connect")
def on_connect():
    audio_buffers[request.sid] = np.array([], dtype=np.float32)
    emit("status", {"msg": "connected"})

@socketio.on("audio_chunk")
def on_audio_chunk(data):
    sid = request.sid

    # 🔑 base64 → float32
    audio_bytes = base64.b64decode(data["audio"])
    audio_np = np.frombuffer(audio_bytes, dtype=np.float32)

    audio_buffers[sid] = np.concatenate([audio_buffers[sid], audio_np])

    if len(audio_buffers[sid]) >= SAMPLE_RATE * CHUNK_SECONDS:
        chunk = audio_buffers[sid]
        audio_buffers[sid] = np.array([], dtype=np.float32)

        model_id = data.get("model_id", "huggingface-base")
        model_info = next(
            m for m in discover_models() if m["id"] == model_id
        )

        text = transcribe_audio(chunk, SAMPLE_RATE, model_info)
        emit("partial_transcript", {"text": text})

    print("Realtime samples:", len(audio_buffers[sid]))


@socketio.on("disconnect")
def on_disconnect():
    audio_buffers.pop(request.sid, None)

# =============================================================================
# Main
# =============================================================================
if __name__ == "__main__":
    print("=" * 70)
    print(" Whisper ASR Web Interface (NORMAL + REALTIME FIXED)")
    print("=" * 70)
    print("Device:", "CUDA" if torch.cuda.is_available() else "CPU")
    print("Models dir:", MODELS_DIR)
    print("=" * 70)

    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
