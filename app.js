/**
 * Meeting Translator — Frontend Client
 * Connects to Python backend via Socket.IO for real-time transcription & translation
 */

// ===== DOM Elements =====
const deviceSelect = document.getElementById('device-select');
const sourceLang = document.getElementById('source-lang');
const targetLang = document.getElementById('target-lang');
const btnStart = document.getElementById('btn-start');
const btnStop = document.getElementById('btn-stop');
const btnClear = document.getElementById('btn-clear');
const btnDownload = document.getElementById('btn-download');
const btnCopyOriginal = document.getElementById('btn-copy-original');
const btnCopyTranslated = document.getElementById('btn-copy-translated');
const panelOriginal = document.getElementById('panel-original');
const panelTranslated = document.getElementById('panel-translated');
const statusBar = document.getElementById('status-bar');
const statusText = document.getElementById('status-text');
const connDot = document.getElementById('conn-dot');
const connText = document.getElementById('conn-text');
const entryCountEl = document.getElementById('entry-count');
const durationEl = document.getElementById('duration');
const toast = document.getElementById('toast');
const toastMsg = document.getElementById('toast-msg');

// ===== State =====
let isRecording = false;
let entryCount = 0;
let startTime = null;
let durationInterval = null;
let allOriginal = [];
let allTranslated = [];

// ===== Socket.IO Connection =====
const socket = io();

socket.on('connect', () => {
    connDot.className = 'conn-dot connected';
    connText.textContent = 'Đã kết nối tới server';
    console.log('✅ Connected to server');
    loadDevices();
});

socket.on('disconnect', () => {
    connDot.className = 'conn-dot disconnected';
    connText.textContent = 'Mất kết nối...';
    console.log('❌ Disconnected');
    if (isRecording) {
        setRecordingUI(false);
    }
});

socket.on('connect_error', () => {
    connDot.className = 'conn-dot disconnected';
    connText.textContent = 'Không thể kết nối server. Kiểm tra server.py đang chạy.';
});

socket.on('status', (data) => {
    statusText.textContent = data.message;
    if (data.recording !== undefined) {
        setRecordingUI(data.recording);
    }
    statusBar.style.display = 'flex';
});

socket.on('transcript', (data) => {
    addTranscriptEntry(data.timestamp, data.original, data.translated);
});

socket.on('error', (data) => {
    showToast('❌ ' + data.message);
    setRecordingUI(false);
});

// ===== Load Audio Devices =====
async function loadDevices() {
    try {
        const res = await fetch('/api/devices');
        const devices = await res.json();

        // Clear existing options except default
        deviceSelect.innerHTML = '<option value="">Mặc định (Default Speaker)</option>';

        devices.forEach(device => {
            const opt = document.createElement('option');
            opt.value = device.id;
            opt.textContent = device.name;
            deviceSelect.appendChild(opt);
        });
    } catch (e) {
        console.warn('Could not load devices:', e);
    }
}

// ===== Start / Stop =====
btnStart.addEventListener('click', () => {
    if (isRecording) return;

    socket.emit('start', {
        sourceLang: sourceLang.value,
        targetLang: targetLang.value,
        deviceIndex: deviceSelect.value || null,
    });

    setRecordingUI(true);
    statusBar.style.display = 'flex';
    statusText.textContent = '⏳ Đang khởi động...';

    // Clear placeholders
    clearPlaceholders();
});

btnStop.addEventListener('click', () => {
    socket.emit('stop');
    setRecordingUI(false);
});

// ===== UI State =====
function setRecordingUI(recording) {
    isRecording = recording;
    btnStart.disabled = recording;
    btnStop.disabled = !recording;
    deviceSelect.disabled = recording;
    sourceLang.disabled = recording;
    targetLang.disabled = recording;

    if (recording) {
        btnStart.classList.add('recording');
        btnStart.querySelector('span').textContent = 'Đang lắng nghe...';
        startTime = startTime || Date.now();
        if (!durationInterval) {
            durationInterval = setInterval(updateDuration, 1000);
        }
    } else {
        btnStart.classList.remove('recording');
        btnStart.querySelector('span').textContent = 'Bắt đầu lắng nghe';
        if (durationInterval) {
            clearInterval(durationInterval);
            durationInterval = null;
        }
    }
}

// ===== Transcript Management =====
function clearPlaceholders() {
    const ph1 = panelOriginal.querySelector('.placeholder-text');
    const ph2 = panelTranslated.querySelector('.placeholder-text');
    if (ph1) ph1.remove();
    if (ph2) ph2.remove();
}

function addTranscriptEntry(timestamp, original, translated) {
    clearPlaceholders();

    // Original panel
    const origEntry = createEntry(timestamp, original);
    panelOriginal.appendChild(origEntry);
    panelOriginal.scrollTop = panelOriginal.scrollHeight;

    // Translated panel
    const transEntry = createEntry(timestamp, translated);
    panelTranslated.appendChild(transEntry);
    panelTranslated.scrollTop = panelTranslated.scrollHeight;

    // Store for export
    allOriginal.push({ timestamp, text: original });
    allTranslated.push({ timestamp, text: translated });

    entryCount++;
    entryCountEl.textContent = `${entryCount} câu`;
}

function createEntry(timestamp, text) {
    const entry = document.createElement('div');
    entry.className = 'entry';

    const timeEl = document.createElement('div');
    timeEl.className = 'entry-time';
    timeEl.textContent = timestamp;

    const textEl = document.createElement('div');
    textEl.className = 'entry-text';
    textEl.textContent = text;

    entry.appendChild(timeEl);
    entry.appendChild(textEl);
    return entry;
}

function updateDuration() {
    if (!startTime) return;
    const elapsed = Math.floor((Date.now() - startTime) / 1000);
    const mins = Math.floor(elapsed / 60);
    const secs = elapsed % 60;
    durationEl.textContent = `${mins}:${secs.toString().padStart(2, '0')}`;
}

// ===== Action Buttons =====
btnCopyOriginal.addEventListener('click', () => {
    const text = allOriginal.map(e => `[${e.timestamp}] ${e.text}`).join('\n');
    if (!text) { showToast('📋 Chưa có nội dung.'); return; }
    navigator.clipboard.writeText(text)
        .then(() => showToast('✅ Đã sao chép bản gốc!'))
        .catch(() => showToast('❌ Lỗi sao chép.'));
});

btnCopyTranslated.addEventListener('click', () => {
    const text = allTranslated.map(e => `[${e.timestamp}] ${e.text}`).join('\n');
    if (!text) { showToast('📋 Chưa có nội dung.'); return; }
    navigator.clipboard.writeText(text)
        .then(() => showToast('✅ Đã sao chép bản dịch!'))
        .catch(() => showToast('❌ Lỗi sao chép.'));
});

btnClear.addEventListener('click', () => {
    panelOriginal.innerHTML = '<p class="placeholder-text">Transcript sẽ xuất hiện ở đây...</p>';
    panelTranslated.innerHTML = '<p class="placeholder-text">Bản dịch sẽ xuất hiện ở đây...</p>';
    allOriginal = [];
    allTranslated = [];
    entryCount = 0;
    startTime = null;
    entryCountEl.textContent = '0 câu';
    durationEl.textContent = '0:00';
    showToast('🗑️ Đã xóa tất cả.');
});

btnDownload.addEventListener('click', () => {
    if (allOriginal.length === 0) {
        showToast('📄 Chưa có nội dung để tải.');
        return;
    }

    let content = '=== MEETING TRANSCRIPT ===\n';
    content += `Date: ${new Date().toLocaleString('vi-VN')}\n`;
    content += `Entries: ${entryCount}\n\n`;

    content += '--- ORIGINAL ---\n';
    allOriginal.forEach(e => {
        content += `[${e.timestamp}] ${e.text}\n`;
    });

    content += '\n--- BẢN DỊCH ---\n';
    allTranslated.forEach(e => {
        content += `[${e.timestamp}] ${e.text}\n`;
    });

    const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    const now = new Date();
    a.download = `meeting_${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}_${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast('📥 Đã tải file transcript!');
});

// ===== Toast =====
let toastTimeout = null;
function showToast(message) {
    toastMsg.textContent = message;
    toast.classList.add('show');
    if (toastTimeout) clearTimeout(toastTimeout);
    toastTimeout = setTimeout(() => toast.classList.remove('show'), 3000);
}

// ===== Init =====
console.log('🌐 Meeting Translator frontend ready.');
