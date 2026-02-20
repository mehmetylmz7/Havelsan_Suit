const socket = io();

let audioContext = null;
let processor = null;
let input = null;
let stream = null;

const startBtn = document.getElementById("realtimeStartBtn");
const stopBtn = document.getElementById("realtimeStopBtn");
const statusEl = document.getElementById("realtimeStatus");
const textEl = document.getElementById("realtimeText");
const modelSelect = document.getElementById("modelSelect");

// Float32Array -> base64
function float32ToBase64(float32Array) {
    const bytes = new Uint8Array(float32Array.buffer);
    let binary = "";
    for (let i = 0; i < bytes.length; i++) {
        binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
}

startBtn.onclick = async () => {
    const modelId = modelSelect.value;
    if (!modelId) {
        alert("Önce model seç");
        return;
    }

    textEl.innerText = "";
    statusEl.innerText = "🎙️ Dinleniyor...";

    audioContext = new AudioContext({ sampleRate: 16000 });
    stream = await navigator.mediaDevices.getUserMedia({ audio: true });

    input = audioContext.createMediaStreamSource(stream);
    processor = audioContext.createScriptProcessor(4096, 1, 1);

    input.connect(processor);
    processor.connect(audioContext.destination);

    processor.onaudioprocess = (e) => {
        const audioData = e.inputBuffer.getChannelData(0);
        const audioBase64 = float32ToBase64(audioData);

        socket.emit("audio_chunk", {
            audio: audioBase64,
            model_id: modelId
        });
    };

    startBtn.disabled = true;
    stopBtn.disabled = false;
};

stopBtn.onclick = () => {
    if (processor) processor.disconnect();
    if (input) input.disconnect();
    if (stream) stream.getTracks().forEach(t => t.stop());
    if (audioContext) audioContext.close();

    statusEl.innerText = "⏹️ Durduruldu";
    startBtn.disabled = false;
    stopBtn.disabled = true;
};

socket.on("partial_transcript", (data) => {
    textEl.innerText += data.text + " ";
});
