/**
 * Whisper Worker — Runs Whisper AI model in a background thread
 * Uses @xenova/transformers to transcribe audio chunks
 */
import { pipeline, env } from 'https://cdn.jsdelivr.net/npm/@xenova/transformers@2.17.2';

// Don't look for local models
env.allowLocalModels = false;

let transcriber = null;

// Language code → Whisper language name
const LANG_MAP = {
    'vi-VN': 'vietnamese',
    'en-US': 'english',
    'en-GB': 'english',
    'ja-JP': 'japanese',
    'ko-KR': 'korean',
    'zh-CN': 'chinese',
    'fr-FR': 'french',
    'de-DE': 'german',
};

self.addEventListener('message', async (e) => {
    const { type, data } = e.data;

    switch (type) {
        case 'load':
            await loadModel();
            break;
        case 'transcribe':
            await transcribe(data.audio, data.language);
            break;
    }
});

async function loadModel() {
    try {
        self.postMessage({ type: 'loading', message: 'Đang tải mô hình Whisper AI...' });

        transcriber = await pipeline(
            'automatic-speech-recognition',
            'Xenova/whisper-tiny',
            {
                progress_callback: (progress) => {
                    if (progress.status === 'progress' && progress.progress !== undefined) {
                        self.postMessage({
                            type: 'progress',
                            progress: Math.round(progress.progress),
                            file: progress.file || '',
                        });
                    } else if (progress.status === 'done') {
                        self.postMessage({ type: 'progress', progress: 100, file: progress.file || '' });
                    }
                },
            }
        );

        self.postMessage({ type: 'ready' });
    } catch (error) {
        self.postMessage({ type: 'error', message: 'Lỗi tải model: ' + error.message });
    }
}

async function transcribe(audioFloat32, language) {
    if (!transcriber) {
        self.postMessage({ type: 'error', message: 'Model chưa sẵn sàng.' });
        return;
    }

    try {
        self.postMessage({ type: 'processing' });

        const whisperLang = LANG_MAP[language] || 'english';

        const result = await transcriber(audioFloat32, {
            language: whisperLang,
            task: 'transcribe',
        });

        const text = result.text ? result.text.trim() : '';
        self.postMessage({ type: 'result', text });
    } catch (error) {
        self.postMessage({ type: 'error', message: 'Lỗi nhận diện: ' + error.message });
    }
}
