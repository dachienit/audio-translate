"""
Meeting Translator — Real-time meeting transcription & translation
Captures system audio (WASAPI loopback) → Whisper transcription → Google Translate
"""

import sys
import os

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    os.environ['PYTHONIOENCODING'] = 'utf-8'

import soundcard as sc
import numpy as np
import threading
import time

from faster_whisper import WhisperModel
from deep_translator import GoogleTranslator
from flask import Flask, jsonify
from flask_socketio import SocketIO

# ===== Flask App =====
app = Flask(__name__, static_url_path='', static_folder='.')
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# ===== Global State =====
model = None
is_recording = False
source_lang = 'en'
target_lang = 'vi'

SAMPLE_RATE = 16000
CHUNK_SECONDS = 3  # Reduce from 6s to 3s for ~50% lower latency


def load_model():
    """Load Whisper model at startup"""
    global model
    print("[*] Loading Whisper model (tiny)... This may take a moment on first run.")
    model = WhisperModel("tiny", device="cpu", compute_type="int8")

    # Warm-up run to avoid cold-start latency
    dummy = np.zeros(SAMPLE_RATE, dtype=np.float32)
    _ = list(model.transcribe(dummy)[0])
    print("[OK] Whisper model loaded and ready!")


def get_loopback_devices():
    """Get list of available loopback microphones for capturing system audio"""
    try:
        # Get all microphones including loopback (virtual mics that capture speaker output)
        mics = sc.all_microphones(include_loopback=True)
        loopback_mics = [m for m in mics if m.isloopback]
        return [{'id': i, 'name': m.name} for i, m in enumerate(loopback_mics)]
    except Exception as e:
        print(f"Error listing devices: {e}")
        return []


def capture_and_transcribe(device_index=None):
    """Main audio capture + transcription + translation loop"""
    global is_recording

    try:
        # Get loopback microphones (capture what speakers are playing)
        all_loopback = [m for m in sc.all_microphones(include_loopback=True) if m.isloopback]

        if not all_loopback:
            raise Exception("Khong tim thay loopback device. Kiem tra audio driver.")

        if device_index is not None and device_index < len(all_loopback):
            loopback_mic = all_loopback[device_index]
        else:
            # Default: get loopback for the default speaker
            default_speaker = sc.default_speaker()
            loopback_mic = sc.get_microphone(id=str(default_speaker.id), include_loopback=True)

        device_name = loopback_mic.name
        print(f"[REC] Recording from: {device_name}")
        socketio.emit('status', {
            'message': f'\ud83c\udfa7 \u0110ang l\u1eafng nghe: {device_name}',
            'recording': True
        })

        with loopback_mic.recorder(samplerate=SAMPLE_RATE, channels=1) as recorder:
            while is_recording:
                # Record a chunk of audio
                audio = recorder.record(numframes=SAMPLE_RATE * CHUNK_SECONDS)
                audio = audio.flatten().astype(np.float32)

                # Skip silence / very quiet audio
                rms = np.sqrt(np.mean(audio ** 2))
                if rms < 0.003:
                    continue

                # Transcribe with Whisper
                try:
                    segments, info = model.transcribe(
                        audio,
                        language=source_lang if source_lang != 'auto' else None,
                        beam_size=1,  # Reduced from 5 to 1 for faster inference
                        vad_filter=True,
                        vad_parameters=dict(
                            min_silence_duration_ms=200,  # Lower threshold to trigger transcription earlier
                        ),
                    )
                    text = " ".join([seg.text for seg in segments]).strip()
                except Exception as e:
                    print(f"Transcription error: {e}")
                    continue

                # Skip empty or noise-only results
                if not text:
                    continue
                # Skip common Whisper hallucinations
                hallucinations = [
                    '', '.', '...', 'you', 'thank you.', 'thanks.',
                    'bye.', 'thank you for watching.', 'thanks for watching.',
                    'subscribe', 'like and subscribe',
                ]
                if text.lower().strip('.').strip() in hallucinations:
                    continue

                # Translate
                translated = text
                if source_lang != target_lang:
                    try:
                        translator = GoogleTranslator(
                            source=source_lang if source_lang != 'auto' else 'auto',
                            target=target_lang
                        )
                        translated = translator.translate(text)
                        if not translated:
                            translated = text
                    except Exception as e:
                        print(f"Translation error: {e}")
                        translated = f"[Lỗi dịch] {text}"

                timestamp = time.strftime('%H:%M:%S')
                print(f"  [{timestamp}] {text}")
                print(f"  [{timestamp}] -> {translated}")

                socketio.emit('transcript', {
                    'original': text,
                    'translated': translated,
                    'timestamp': timestamp,
                })

    except Exception as e:
        error_msg = str(e)
        print(f"[ERROR] {error_msg}")
        socketio.emit('error', {'message': error_msg})
    finally:
        is_recording = False
        socketio.emit('status', {'message': '\u0110\u00e3 d\u1eebng.', 'recording': False})


# ===== Routes =====
@app.route('/')
def index():
    return app.send_static_file('index.html')


@app.route('/api/devices')
def api_devices():
    """Return available audio output devices for loopback capture"""
    devices = get_loopback_devices()
    return jsonify(devices)


# ===== Socket.IO Events =====
@socketio.on('connect')
def handle_connect():
    print("[+] Client connected")
    socketio.emit('status', {
        'message': '\u0110\u00e3 k\u1ebft n\u1ed1i. Ch\u1ecdn thi\u1ebft b\u1ecb v\u00e0 nh\u1ea5n B\u1eaft \u0111\u1ea7u.',
        'recording': False
    })


@socketio.on('start')
def handle_start(data=None):
    global is_recording, source_lang, target_lang

    if is_recording:
        socketio.emit('status', {'message': '\u0110ang ghi r\u1ed3i.', 'recording': True})
        return

    # Parse settings from client
    device_index = None
    if data:
        source_lang = data.get('sourceLang', 'en')
        target_lang = data.get('targetLang', 'vi')
        dev_idx = data.get('deviceIndex')
        if dev_idx is not None and dev_idx != '':
            try:
                device_index = int(dev_idx)
            except (ValueError, TypeError):
                device_index = None

    is_recording = True
    thread = threading.Thread(
        target=capture_and_transcribe,
        args=(device_index,),
        daemon=True
    )
    thread.start()


@socketio.on('stop')
def handle_stop():
    global is_recording
    is_recording = False
    print("[STOP] Recording stopped by client")


@socketio.on('disconnect')
def handle_disconnect():
    global is_recording
    is_recording = False
    print("[-] Client disconnected")


# ===== Main =====
if __name__ == '__main__':
    print("=" * 50)
    print("  Meeting Translator")
    print("=" * 50)

    load_model()

    print(f"")
    print(f"  Server running at http://localhost:3000")
    print(f"  Open this URL in your browser.")
    print(f"")

    socketio.run(
        app,
        host='0.0.0.0',
        port=3000,
        debug=False,
        allow_unsafe_werkzeug=True
    )
