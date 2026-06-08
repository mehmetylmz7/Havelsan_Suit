# =============================================================================
# EVENTLET (Realtime için ZORUNLU)
# =============================================================================
import eventlet
eventlet.monkey_patch()

import base64
import csv
import io
import json
import os
import random
import re
import sqlite3
from pathlib import Path

import jiwer
import librosa
import numpy as np
import torch
from dotenv import load_dotenv
from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from pydub import AudioSegment
from transformers import WhisperForConditionalGeneration, WhisperProcessor

load_dotenv()

# =============================================================================
# Paths
# =============================================================================
BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
MODELS_DIR = ROOT_DIR / "models"
DATABASE_PATH = BASE_DIR / "database.db"
RECORDINGS_DIR = BASE_DIR / "recordings"
EXPORTS_DIR = BASE_DIR / "exports"

RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

# =============================================================================
# Flask setup
# =============================================================================
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "havelsan_suit_unified_web_secret")
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin")
SAMPLE_RATE = 16000
CHUNK_SECONDS = 0.5
COMMANDS = [
    "üç numaralı track designate edildi",
    "üç numaralı iz designate edildi",
    "üç numaralı tracki çiz",
    "track'lere angajman yap",
    "track'lara angajman yap",
    "track'lere engagement yap",
    "track'lara engagement yap",
    "izlere fix at",
    "tracklara fix at",
    "tracklere fix at",
    "kerterizlere fix yap",
    "engagement yap",
    "emergency moda geç",
    "track three designate yap",
    "battle short durumuna geç",
    "advent sistemi aktif",
]

models_cache = {}
audio_buffers = {}

# =============================================================================
# Database
# =============================================================================
def get_db_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS participants (
            participant_id TEXT PRIMARY KEY,
            age INTEGER,
            gender TEXT,
            education TEXT,
            english_level TEXT,
            selected_commands TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS recordings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            participant_id TEXT,
            command_index INTEGER,
            reference_text TEXT,
            audio_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(participant_id) REFERENCES participants(participant_id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS wer_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recording_id INTEGER,
            reference_text TEXT,
            prediction_text TEXT,
            wer REAL,
            insertion_count INTEGER,
            deletion_count INTEGER,
            substitution_count INTEGER,
            FOREIGN KEY(recording_id) REFERENCES recordings(id)
        )
    """)
    conn.commit()
    conn.close()


init_db()

# =============================================================================
# Model discovery / loading
# =============================================================================
def discover_models():
    models = []
    if not MODELS_DIR.exists():
        return models

    for model_dir in sorted(MODELS_DIR.iterdir()):
        if not model_dir.is_dir():
            continue

        has_config = (model_dir / "config.json").exists()
        has_weights = (
            (model_dir / "model.safetensors").exists()
            or (model_dir / "pytorch_model.bin").exists()
        )
        if not (has_config and has_weights):
            continue

        size_bytes = sum(f.stat().st_size for f in model_dir.rglob("*") if f.is_file())
        models.append({
            "id": f"local-{model_dir.name}",
            "name": model_dir.name,
            "path": str(model_dir),
            "type": "local",
            "size": f"{size_bytes / (1024 * 1024):.1f} MB",
        })

    return models


def get_model_info(model_id):
    return next((model for model in discover_models() if model["id"] == model_id), None)


def load_model(model_info):
    model_id = model_info["id"]
    if model_id in models_cache:
        return models_cache[model_id]

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model_path = model_info["path"]
    print(f"Loading model: {model_info['name']}")

    processor = WhisperProcessor.from_pretrained(
        model_path,
        language="turkish",
        task="transcribe",
    )
    model = WhisperForConditionalGeneration.from_pretrained(model_path)
    model.to(device)
    model.eval()

    forced_ids = processor.get_decoder_prompt_ids(
        language="turkish",
        task="transcribe",
    )
    model.generation_config.forced_decoder_ids = forced_ids
    model.generation_config.max_new_tokens = 32
    model.generation_config.do_sample = False
    model.generation_config.num_beams = 1
    model.generation_config.repetition_penalty = 1.15
    model.generation_config.no_repeat_ngram_size = 3

    models_cache[model_id] = (processor, model, device)
    return processor, model, device


def transcribe_audio_array(audio_data, sample_rate, model_info):
    processor, model, device = load_model(model_info)

    if sample_rate != SAMPLE_RATE:
        audio_data = librosa.resample(
            y=audio_data,
            orig_sr=sample_rate,
            target_sr=SAMPLE_RATE,
        )

    inputs = processor(
        audio_data,
        sampling_rate=SAMPLE_RATE,
        return_tensors="pt",
    )
    input_features = inputs.input_features.to(device).to(model.dtype)

    with torch.no_grad():
        predicted_ids = model.generate(
            input_features,
            max_new_tokens=32,
            do_sample=False,
            num_beams=1,
            repetition_penalty=1.15,
            no_repeat_ngram_size=3,
        )

    decoded = processor.batch_decode(predicted_ids, skip_special_tokens=True)[0]
    return sanitize_transcription(decoded)


def transcribe_audio_file(audio_path, model_info):
    audio_data, sr = librosa.load(audio_path, sr=SAMPLE_RATE, mono=True)
    return transcribe_audio_array(audio_data, sr, model_info)

# =============================================================================
# Text / WER helpers
# =============================================================================
WHISPER_CONTROL_TOKEN_RE = re.compile(r"<\|[^>]+?\|>")


def collapse_repeated_words(text):
    words = text.split()
    collapsed = []
    previous_key = None
    for word in words:
        key = turkish_lower(word.strip(".,;:!?()[]{}'’\""))
        if key and key == previous_key:
            continue
        collapsed.append(word)
        previous_key = key
    return " ".join(collapsed)


def sanitize_transcription(text):
    if not text:
        return ""
    text = WHISPER_CONTROL_TOKEN_RE.sub(" ", text)
    text = text.replace("<|", " ").replace("|>", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return collapse_repeated_words(text)


def turkish_lower(text):
    mapping = {
        "I": "ı",
        "İ": "i",
        "Ç": "ç",
        "Ş": "ş",
        "Ğ": "ğ",
        "Ü": "ü",
        "Ö": "ö",
    }
    for key, value in mapping.items():
        text = text.replace(key, value)
    return text.lower()


def clean_text(text):
    if not text:
        return ""
    text = sanitize_transcription(text)
    text = turkish_lower(text)
    text = text.replace("’", "").replace("'", "")
    text = re.sub(r"[.,\/#!$%\^&\*;:{}=\-_`~()?]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def generate_participant_id():
    conn = get_db_connection()
    rows = conn.execute("SELECT participant_id FROM participants").fetchall()
    conn.close()

    max_num = 0
    for row in rows:
        participant_id = row["participant_id"]
        if participant_id.startswith("participant_"):
            try:
                max_num = max(max_num, int(participant_id.split("_")[1]))
            except (ValueError, IndexError):
                pass
    return f"participant_{max_num + 1:03d}"

# =============================================================================
# Main routes
# =============================================================================
@app.route("/")
def index():
    return render_template("home.html")


@app.route("/demo")
def demo():
    return render_template("index.html")


@app.route("/models")
def get_models():
    return jsonify({"success": True, "models": discover_models()})


@app.route("/transcribe", methods=["POST"])
def transcribe():
    if "audio" not in request.files:
        return jsonify({"success": False, "error": "Ses dosyası bulunamadı"}), 400

    model_id = request.form.get("model_id")
    model_info = get_model_info(model_id)
    if not model_info:
        return jsonify({"success": False, "error": "Geçerli bir lokal model seçilmedi"}), 400

    audio_bytes = request.files["audio"].read()
    audio_data, sr = librosa.load(io.BytesIO(audio_bytes), sr=None, mono=True)
    text = transcribe_audio_array(audio_data, sr, model_info)

    return jsonify({
        "success": True,
        "model": model_info["name"],
        "transcription": text,
    })

# =============================================================================
# Participant test routes
# =============================================================================
@app.route("/participant", methods=["GET", "POST"])
def participant_start():
    models = discover_models()

    if request.method == "POST":
        model_id = request.form.get("model_id")
        model_info = get_model_info(model_id)
        if not model_info:
            return render_template(
                "participant_start.html",
                models=models,
                error="Lütfen geçerli bir lokal model seçin.",
            )

        session.clear()
        session["participant_model_id"] = model_id
        session["participant_model_name"] = model_info["name"]
        return redirect(url_for("consent"))

    return render_template("participant_start.html", models=models)


@app.route("/consent", methods=["GET", "POST"])
def consent():
    if not session.get("participant_model_id"):
        return redirect(url_for("participant_start"))

    if request.method == "POST":
        if request.form.get("consent_agreed") == "on":
            session["consent_agreed"] = True
            return redirect(url_for("demographics"))
    return render_template("consent.html")


@app.route("/demographics", methods=["GET", "POST"])
def demographics():
    if not session.get("participant_model_id"):
        return redirect(url_for("participant_start"))
    if not session.get("consent_agreed"):
        return redirect(url_for("consent"))

    if request.method == "POST":
        age = request.form.get("age")
        gender = request.form.get("gender")
        education = request.form.get("education")
        english_level = request.form.get("english_level")

        participant_id = generate_participant_id()
        selected_commands = random.sample(COMMANDS, 5)

        conn = get_db_connection()
        conn.execute(
            """
            INSERT INTO participants
                (participant_id, age, gender, education, english_level, selected_commands)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                participant_id,
                int(age),
                gender,
                education,
                english_level,
                json.dumps(selected_commands),
            ),
        )
        conn.commit()
        conn.close()

        session["participant_id"] = participant_id
        session["current_cmd_idx"] = 1
        return redirect(url_for("record"))

    return render_template("demographics.html", participant_id=generate_participant_id())


@app.route("/record", methods=["GET"])
def record():
    participant_id = session.get("participant_id")
    if not session.get("participant_model_id"):
        return redirect(url_for("participant_start"))
    if not participant_id:
        return redirect(url_for("demographics"))

    conn = get_db_connection()
    row = conn.execute(
        "SELECT selected_commands FROM participants WHERE participant_id = ?",
        (participant_id,),
    ).fetchone()
    conn.close()

    if not row:
        return redirect(url_for("demographics"))

    selected_commands = json.loads(row["selected_commands"])
    command_index = session.get("current_cmd_idx", 1)
    if command_index > 5:
        return redirect(url_for("result"))

    return render_template(
        "record.html",
        participant_id=participant_id,
        command_index=command_index,
        command_text=selected_commands[command_index - 1],
        selected_model_name=session.get("participant_model_name", "-"),
    )


@app.route("/upload_audio", methods=["POST"])
def upload_audio():
    participant_id = session.get("participant_id")
    model_info = get_model_info(session.get("participant_model_id"))

    if not participant_id:
        return jsonify({"success": False, "error": "Oturum bulunamadı"}), 400
    if not model_info:
        return jsonify({"success": False, "error": "Model seçimi bulunamadı"}), 400
    if "audio" not in request.files:
        return jsonify({"success": False, "error": "Ses verisi yüklenemedi"}), 400

    command_index = int(request.form.get("command_index", 1))

    conn = get_db_connection()
    row = conn.execute(
        "SELECT selected_commands FROM participants WHERE participant_id = ?",
        (participant_id,),
    ).fetchone()
    if not row:
        conn.close()
        return jsonify({"success": False, "error": "Katılımcı bulunamadı"}), 404

    selected_commands = json.loads(row["selected_commands"])
    reference_text = selected_commands[command_index - 1]
    wav_path = RECORDINGS_DIR / f"{participant_id}_cmd_{command_index:02d}.wav"

    try:
        audio_segment = AudioSegment.from_file(request.files["audio"])
        audio_segment = audio_segment.set_frame_rate(SAMPLE_RATE).set_channels(1).set_sample_width(2)
        audio_segment.export(wav_path, format="wav")
    except Exception as exc:
        conn.close()
        return jsonify({"success": False, "error": f"Ses dönüştürme hatası: {exc}"}), 500

    cursor = conn.cursor()
    existing = cursor.execute(
        """
        SELECT id FROM recordings
        WHERE participant_id = ? AND command_index = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (participant_id, command_index),
    ).fetchone()

    if existing:
        cursor.execute(
            """
            UPDATE recordings
            SET reference_text = ?, audio_path = ?, created_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (reference_text, str(wav_path), existing["id"]),
        )
        cursor.execute("DELETE FROM wer_results WHERE recording_id = ?", (existing["id"],))
    else:
        cursor.execute(
            """
            INSERT INTO recordings (participant_id, command_index, reference_text, audio_path)
            VALUES (?, ?, ?, ?)
            """,
            (participant_id, command_index, reference_text, str(wav_path)),
        )

    conn.commit()
    conn.close()

    session["current_cmd_idx"] = command_index + 1
    return jsonify({
        "success": True,
        "next_index": command_index + 1,
    })


def calculate_wer(reference_text, prediction_text):
    ref_norm = clean_text(reference_text)
    pred_norm = clean_text(prediction_text)
    try:
        if not ref_norm:
            return 0.0, 0, 0, 0

        wer_result = jiwer.process_words(ref_norm, pred_norm)
        return (
            wer_result.wer,
            wer_result.insertions,
            wer_result.deletions,
            wer_result.substitutions,
        )
    except Exception as exc:
        print(f"WER calculation error: {exc}")
        return 1.0, 0, 0, 0


def process_participant_predictions(participant_id, model_info):
    conn = get_db_connection()
    rows = conn.execute(
        """
        SELECT r.id, r.command_index, r.reference_text, r.audio_path,
               w.prediction_text, w.wer, w.insertion_count,
               w.deletion_count, w.substitution_count
        FROM recordings r
        LEFT JOIN wer_results w ON r.id = w.recording_id
        WHERE r.participant_id = ?
          AND r.id IN (
              SELECT MAX(id)
              FROM recordings
              WHERE participant_id = ?
              GROUP BY command_index
          )
        ORDER BY r.command_index ASC
        """,
        (participant_id, participant_id),
    ).fetchall()

    results = []
    for row in rows:
        prediction_text = transcribe_audio_file(row["audio_path"], model_info)
        wer, insertions, deletions, substitutions = calculate_wer(
            row["reference_text"],
            prediction_text,
        )
        conn.execute("DELETE FROM wer_results WHERE recording_id = ?", (row["id"],))
        conn.execute(
            """
            INSERT INTO wer_results
                (recording_id, reference_text, prediction_text, wer,
                 insertion_count, deletion_count, substitution_count)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["id"],
                row["reference_text"],
                prediction_text,
                wer,
                insertions,
                deletions,
                substitutions,
            ),
        )
        results.append({
            "command_index": row["command_index"],
            "reference_text": row["reference_text"],
            "prediction_text": prediction_text,
            "wer": wer,
            "insertion_count": insertions,
            "deletion_count": deletions,
            "substitution_count": substitutions,
        })

    conn.commit()
    conn.close()
    return results


@app.route("/result", methods=["GET"])
def result():
    participant_id = session.get("participant_id")
    if not participant_id:
        return redirect(url_for("index"))

    model_info = get_model_info(session.get("participant_model_id"))
    if not model_info:
        return redirect(url_for("participant_start"))

    try:
        results = process_participant_predictions(participant_id, model_info)
    except Exception as exc:
        return render_template(
            "result.html",
            participant_id=participant_id,
            selected_model_name=model_info["name"],
            results=[],
            error=f"Toplu ASR analizi sırasında hata oluştu: {exc}",
        ), 500

    return render_template(
        "result.html",
        participant_id=participant_id,
        selected_model_name=model_info["name"],
        results=results,
        error=None,
    )

# =============================================================================
# Admin routes
# =============================================================================
@app.route("/admin", methods=["GET", "POST"])
def admin_dashboard():
    if request.method == "POST":
        if request.form.get("password") == ADMIN_PASSWORD:
            session["admin_logged_in"] = True
            return redirect(url_for("admin_dashboard"))
        return render_template("admin.html", show_login=True, error="Hatalı şifre.")

    if not session.get("admin_logged_in"):
        return render_template("admin.html", show_login=True)

    conn = get_db_connection()
    total_participants = conn.execute("SELECT COUNT(*) FROM participants").fetchone()[0]
    total_recordings = conn.execute("SELECT COUNT(*) FROM recordings").fetchone()[0]
    avg_wer_row = conn.execute("SELECT AVG(wer) FROM wer_results").fetchone()
    avg_wer = avg_wer_row[0] if avg_wer_row[0] is not None else 0.0

    cmd_wers = [dict(row) for row in conn.execute("""
        SELECT reference_text, COUNT(*) as count, AVG(wer) as avg_wer
        FROM wer_results
        GROUP BY reference_text
        ORDER BY avg_wer DESC
    """).fetchall()]
    eng_dist = [dict(row) for row in conn.execute("""
        SELECT english_level, COUNT(*) as count
        FROM participants
        GROUP BY english_level
        ORDER BY english_level ASC
    """).fetchall()]
    gender_dist = [dict(row) for row in conn.execute("""
        SELECT gender, COUNT(*) as count
        FROM participants
        GROUP BY gender
    """).fetchall()]

    participants = [dict(row) for row in conn.execute("""
        SELECT p.participant_id, p.age, p.gender, p.education, p.english_level,
               p.created_at, COUNT(r.id) as recording_count,
               COUNT(w.id) as result_count, AVG(w.wer) as avg_wer
        FROM participants p
        LEFT JOIN recordings r ON p.participant_id = r.participant_id
        LEFT JOIN wer_results w ON r.id = w.recording_id
        GROUP BY p.participant_id
        ORDER BY p.created_at DESC, p.participant_id DESC
    """).fetchall()]

    selected_participant_id = request.args.get("participant_id")
    participant_results = []
    selected_participant = None
    if selected_participant_id:
        selected_participant = conn.execute(
            """
            SELECT participant_id, age, gender, education, english_level, created_at
            FROM participants
            WHERE participant_id = ?
            """,
            (selected_participant_id,),
        ).fetchone()
        if selected_participant:
            selected_participant = dict(selected_participant)
            participant_results = [dict(row) for row in conn.execute(
                """
                SELECT r.command_index, r.reference_text, w.prediction_text, w.wer,
                       w.insertion_count, w.deletion_count, w.substitution_count,
                       r.audio_path, r.created_at
                FROM recordings r
                LEFT JOIN wer_results w ON r.id = w.recording_id
                WHERE r.participant_id = ?
                  AND r.id IN (
                      SELECT MAX(id)
                      FROM recordings
                      WHERE participant_id = ?
                      GROUP BY command_index
                  )
                ORDER BY r.command_index ASC
                """,
                (selected_participant_id, selected_participant_id),
            ).fetchall()]
    conn.close()

    return render_template(
        "admin.html",
        show_login=False,
        total_participants=total_participants,
        total_recordings=total_recordings,
        avg_wer=round(avg_wer * 100, 2),
        cmd_wers=cmd_wers,
        most_failed=cmd_wers[:5],
        eng_dist=eng_dist,
        gender_dist=gender_dist,
        participants=participants,
        selected_participant_id=selected_participant_id,
        selected_participant=selected_participant,
        participant_results=participant_results,
    )


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("index"))


@app.route("/admin/export/<table_name>")
def export_csv(table_name):
    if not session.get("admin_logged_in"):
        return "Unauthorized", 401
    if table_name not in {"participants", "recordings", "wer_results"}:
        return "Not Found", 404

    csv_path = EXPORTS_DIR / f"{table_name}.csv"
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()
    headers = [description[0] for description in cursor.description] if rows else []

    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        for row in rows:
            writer.writerow(list(row))
    conn.close()

    return send_file(csv_path, as_attachment=True, download_name=csv_path.name)

# =============================================================================
# Realtime Socket.IO
# =============================================================================
@socketio.on("connect")
def on_connect():
    audio_buffers[request.sid] = np.array([], dtype=np.float32)
    emit("status", {"msg": "connected"})


@socketio.on("audio_chunk")
def on_audio_chunk(data):
    sid = request.sid
    audio_bytes = base64.b64decode(data["audio"])
    audio_np = np.frombuffer(audio_bytes, dtype=np.float32)
    audio_buffers[sid] = np.concatenate([audio_buffers[sid], audio_np])

    if len(audio_buffers[sid]) >= SAMPLE_RATE * CHUNK_SECONDS:
        chunk = audio_buffers[sid]
        audio_buffers[sid] = np.array([], dtype=np.float32)
        model_info = get_model_info(data.get("model_id"))
        if model_info:
            text = transcribe_audio_array(chunk, SAMPLE_RATE, model_info)
            emit("partial_transcript", {"text": text})


@socketio.on("disconnect")
def on_disconnect():
    audio_buffers.pop(request.sid, None)

# =============================================================================
# Main
# =============================================================================
if __name__ == "__main__":
    print("=" * 70)
    print(" Havelsan Suit Unified ASR Interface")
    print("=" * 70)
    print("Device:", "CUDA" if torch.cuda.is_available() else "CPU")
    print("Models dir:", MODELS_DIR)
    print("Available local models:", len(discover_models()))
    print("=" * 70)
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
