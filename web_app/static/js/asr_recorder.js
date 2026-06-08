// recorder.js

class VoiceRecorder {
    constructor() {
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.audioBlob = null;
        this.audioUrl = null;
        this.stream = null;
    }

    /**
     * Starts recording audio from user microphone.
     */
    async start() {
        this.audioChunks = [];
        this.audioBlob = null;
        this.audioUrl = null;

        try {
            // Request microphone access
            this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            
            // Choose optimal mimeType based on browser support
            let mimeType = 'audio/webm';
            if (!MediaRecorder.isTypeSupported(mimeType)) {
                mimeType = 'audio/ogg';
            }
            if (!MediaRecorder.isTypeSupported(mimeType)) {
                mimeType = 'audio/mp4';
            }
            if (!MediaRecorder.isTypeSupported(mimeType)) {
                mimeType = ''; // Browser default fallback
            }

            const options = mimeType ? { mimeType } : {};
            this.mediaRecorder = new MediaRecorder(this.stream, options);

            this.mediaRecorder.ondataavailable = (event) => {
                if (event.data.size > 0) {
                    this.audioChunks.push(event.data);
                }
            };

            this.mediaRecorder.onstop = () => {
                const finalMime = this.mediaRecorder.mimeType || 'audio/webm';
                this.audioBlob = new Blob(this.audioChunks, { type: finalMime });
                this.audioUrl = URL.createObjectURL(this.audioBlob);
                
                // Dispatch custom event to notify UI
                const event = new CustomEvent('recording-stopped', {
                    detail: {
                        url: this.audioUrl,
                        blob: this.audioBlob
                    }
                });
                window.dispatchEvent(event);
            };

            this.mediaRecorder.start();
        } catch (error) {
            console.error("Microphone access denied or error starting recording:", error);
            throw error;
        }
    }

    /**
     * Stops current recording.
     */
    stop() {
        if (this.mediaRecorder && this.mediaRecorder.state !== 'inactive') {
            this.mediaRecorder.stop();
        }
        if (this.stream) {
            this.stream.getTracks().forEach(track => track.stop());
        }
    }
}

// Export to window
window.VoiceRecorder = VoiceRecorder;
