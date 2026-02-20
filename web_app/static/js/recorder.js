// Global değişkenler
let mediaRecorder;
let audioChunks = [];
let audioBlob = null;
let uploadedFile = null;
let availableModels = [];
let selectedModelId = null;

// DOM elementleri
const recordBtn = document.getElementById('recordBtn');
const stopBtn = document.getElementById('stopBtn');
const recordingStatus = document.getElementById('recordingStatus');
const audioPlayback = document.getElementById('audioPlayback');
const fileUploadArea = document.getElementById('fileUploadArea');
const fileInput = document.getElementById('fileInput');
const fileName = document.getElementById('fileName');
const transcribeBtn = document.getElementById('transcribeBtn');
const resultsCard = document.getElementById('resultsCard');
const modelSelect = document.getElementById('modelSelect');
const modelInfo = document.getElementById('modelInfo');

// Sayfa yüklendiğinde modelleri çek
document.addEventListener('DOMContentLoaded', async () => {
    await loadAvailableModels();
});

// Mevcut modelleri yükle
async function loadAvailableModels() {
    try {
        const response = await fetch('/models');
        const data = await response.json();
        
        if (data.success) {
            availableModels = data.models;
            populateModelDropdown();
        } else {
            console.error('Model listesi alınamadı:', data.error);
            modelSelect.innerHTML = '<option value="">Model bulunamadı</option>';
        }
    } catch (error) {
        console.error('Modeller yüklenirken hata:', error);
        modelSelect.innerHTML = '<option value="">Hata oluştu</option>';
    }
}

// Dropdown'ı doldur
function populateModelDropdown() {
    modelSelect.innerHTML = '';
    
    availableModels.forEach((model, index) => {
        const option = document.createElement('option');
        option.value = model.id;
        option.textContent = `${model.name} (${model.size})`;
        modelSelect.appendChild(option);
        
        // İlk modeli seç
        if (index === 0) {
            selectedModelId = model.id;
            updateModelInfo(model);
        }
    });
}

// Model bilgisini göster
function updateModelInfo(model) {
    if (model.type === 'huggingface') {
        modelInfo.innerHTML = `<small>📡 HuggingFace model (ilk kullanımda indirilecek)</small>`;
    } else {
        modelInfo.innerHTML = `<small>💾 Lokal model</small>`;
    }
}

// Model seçimi değiştiğinde
modelSelect.addEventListener('change', (e) => {
    selectedModelId = e.target.value;
    const model = availableModels.find(m => m.id === selectedModelId);
    if (model) {
        updateModelInfo(model);
    }
});

// Mikrofon kaydı başlat
recordBtn.addEventListener('click', async () => {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];

        mediaRecorder.ondataavailable = (event) => {
            audioChunks.push(event.data);
        };

        mediaRecorder.onstop = () => {
            audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
            const audioUrl = URL.createObjectURL(audioBlob);
            audioPlayback.src = audioUrl;
            audioPlayback.style.display = 'block';
            
            // Transcribe butonunu aktif et
            transcribeBtn.disabled = false;
            
            // Upload file'ı temizle
            uploadedFile = null;
            fileName.textContent = '';
        };

        mediaRecorder.start();
        recordBtn.disabled = true;
        stopBtn.disabled = false;
        recordingStatus.textContent = '🔴 Kayıt yapılıyor...';
        recordingStatus.className = 'status recording';
    } catch (err) {
        alert('Mikrofonunuza erişim izni gerekiyor: ' + err.message);
    }
});

// Kaydı durdur
stopBtn.addEventListener('click', () => {
    mediaRecorder.stop();
    mediaRecorder.stream.getTracks().forEach(track => track.stop());
    recordBtn.disabled = false;
    stopBtn.disabled = true;
    recordingStatus.textContent = '✅ Kayıt tamamlandı';
    recordingStatus.className = 'status';
});

// Dosya yükleme - tıklama
fileUploadArea.addEventListener('click', () => {
    fileInput.click();
});

// Dosya yükleme - input change
fileInput.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
        handleFile(file);
    }
});

// Drag & Drop
fileUploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    fileUploadArea.classList.add('dragover');
});

fileUploadArea.addEventListener('dragleave', () => {
    fileUploadArea.classList.remove('dragover');
});

fileUploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    fileUploadArea.classList.remove('dragover');
    
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('audio/')) {
        handleFile(file);
    } else {
        alert('Lütfen bir ses dosyası yükleyin (WAV veya MP3)');
    }
});

function handleFile(file) {
    uploadedFile = file;
    fileName.textContent = `📁 ${file.name}`;
    
    // Transcribe butonunu aktif et
    transcribeBtn.disabled = false;
    
    // Mikrofon kaydını temizle
    audioBlob = null;
    audioPlayback.style.display = 'none';
}

// Transcribe butonu
transcribeBtn.addEventListener('click', async () => {
    // Ses dosyasını al
    const audioFile = audioBlob || uploadedFile;
    if (!audioFile) {
        alert('Lütfen önce ses kaydı yapın veya dosya yükleyin');
        return;
    }
    
    if (!selectedModelId) {
        alert('Lütfen bir model seçin');
        return;
    }
    
    // FormData oluştur
    const formData = new FormData();
    formData.append('audio', audioFile instanceof Blob ? audioFile : audioFile, 'audio.wav');
    formData.append('model_id', selectedModelId);
    
    // Loading göster
    transcribeBtn.textContent = '⏳ İşleniyor...';
    transcribeBtn.disabled = true;
    
    try {
        const response = await fetch('/transcribe', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Sonuçları göster
            document.getElementById('usedModel').textContent = data.model;
            document.getElementById('transcriptionText').textContent = data.transcription;
            resultsCard.style.display = 'block';
            
            // Smooth scroll
            resultsCard.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        } else {
            alert('Hata: ' + data.error);
        }
    } catch (error) {
        alert('Bir hata oluştu: ' + error.message);
    } finally {
        transcribeBtn.textContent = '🔊 Transcribe Et';
        transcribeBtn.disabled = false;
    }
});
