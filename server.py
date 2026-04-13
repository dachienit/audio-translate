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
import queue

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
audio_queue = queue.Queue()

SAMPLE_RATE = 16000
CHUNK_SECONDS = 0.5  # Capture audio in fast 0.5s chunks


def load_model():
    """Load Whisper model at startup"""
    global model
    # Upgraded from 'tiny' to 'base' for much better accuracy, still fast enough for CPU
    print("[*] Loading Whisper model (base)... This may take a moment on first run.")
    model = WhisperModel("base", device="cpu", compute_type="int8")

    # Warm-up run to avoid cold-start latency
    dummy = np.zeros(SAMPLE_RATE, dtype=np.float32)
    _ = list(model.transcribe(dummy)[0])
    print("[OK] Whisper model loaded and ready!")


def get_loopback_devices():
    """Get list of available loopback microphones for capturing system audio"""
    try:
        mics = sc.all_microphones(include_loopback=True)
        loopback_mics = [m for m in mics if m.isloopback]
        return [{'id': i, 'name': m.name} for i, m in enumerate(loopback_mics)]
    except Exception as e:
        print(f"Error listing devices: {e}")
        return []


def process_audio_worker():
    """Background worker that continuously pulls audio from queue and transcribes"""
    global is_recording
    
    audio_buffer = []
    silence_frames = 0
    
    while is_recording:
        try:
            chunk = audio_queue.get(timeout=0.5)
        except queue.Empty:
            continue
            
        # Check volume (RMS)
        rms = np.sqrt(np.mean(chunk ** 2))
        is_silence = rms < 0.003
        
        if not is_silence:
            audio_buffer.extend(chunk)
            silence_frames = 0
        else:
            if len(audio_buffer) > 0:
                silence_frames += 1
                audio_buffer.extend(chunk)
                
        buffer_duration = len(audio_buffer) / SAMPLE_RATE
        
        # Transcribe if we hit a pause in speech (pushed by silence) OR buffer is getting long (7+ seconds)
        if (buffer_duration >= 1.5 and silence_frames >= 2) or buffer_duration >= 6.0:
            audio_data = np.array(audio_buffer, dtype=np.float32)
            
            # Reset buffers instantly to allow next sentences to queue up
            audio_buffer = []
            silence_frames = 0
            
            try:
                # Transcribe
                segments, info = model.transcribe(
                    audio_data,
                    language=source_lang if source_lang != 'auto' else None,
                    beam_size=2,  # Balanced for speed and accuracy
                    vad_filter=True,
                    vad_parameters=dict(min_silence_duration_ms=200),
                )
                text = " ".join([seg.text for seg in segments]).strip()
                
                if not text:
                    continue
                    
                # Filter hallucinations
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
                print(f"Transcription error: {e}")


def capture_audio(device_index=None):
    """Focuses ONLY on capturing microphone loopback data smoothly"""
    global is_recording

    try:
        all_loopback = [m for m in sc.all_microphones(include_loopback=True) if m.isloopback]
        if not all_loopback:
            raise Exception("Khong tim thay loopback device. Kiem tra audio driver.")

        if device_index is not None and device_index < len(all_loopback):
            loopback_mic = all_loopback[device_index]
        else:
            default_speaker = sc.default_speaker()
            loopback_mic = sc.get_microphone(id=str(default_speaker.id), include_loopback=True)

        device_name = loopback_mic.name
        print(f"[REC] Recording from: {device_name}")
        socketio.emit('status', {
            'message': f'\ud83c\udfa7 \u0110ang l\u1eafng nghe: {device_name}',
            'recording': True
        })

        # Process thread
        process_thread = threading.Thread(target=process_audio_worker, daemon=True)
        process_thread.start()

        # Capture loop - blocks but is very tight
        with loopback_mic.recorder(samplerate=SAMPLE_RATE, channels=1) as recorder:
            while is_recording:
                audio = recorder.record(numframes=int(SAMPLE_RATE * CHUNK_SECONDS))
                audio = audio.flatten().astype(np.float32)
                audio_queue.put(audio)

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
    return jsonify(get_loopback_devices())


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

    # Clear queue
    while not audio_queue.empty():
        audio_queue.get_nowait()

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
    thread = threading.Thread(target=capture_audio, args=(device_index,), daemon=True)
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


if __name__ == '__main__':
    print("=" * 50)
    print("  Meeting Translator (Multi-threaded & High Accuracy)")
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
