// Text streaming utility for word-by-word display
class TextStreamer {
    private options: {
        onWord: (word: string, fullText: string) => void;
        onSentenceComplete: (sentence: string) => void;
        onComplete: () => void;
        wordsPerSecond: number;
    };
    private words: string[];
    private currentIndex: number = 0;
    private currentSentence: string[] = [];
    private intervalId: any = null;

    constructor(text: string, options: {
        onWord: (word: string, fullText: string) => void;
        onSentenceComplete: (sentence: string) => void;
        onComplete: () => void;
        wordsPerSecond: number;
    }) {
        this.options = options;
        this.words = text.split(/\s+/).filter(word => word.length > 0);
    }

    start() {
        const interval = 1000 / this.options.wordsPerSecond;

        this.intervalId = setInterval(() => {
            if (this.currentIndex >= this.words.length) {
                this.finish();
                return;
            }

            const word = this.words[this.currentIndex];
            this.currentSentence.push(word);
            this.currentIndex++;

            // Build full text so far
            const fullText = this.words.slice(0, this.currentIndex).join(' ');
            this.options.onWord(word, fullText);

            // Check if sentence ends
            if (word.match(/[.!?]$/)) {
                const sentence = this.currentSentence.join(' ');
                this.options.onSentenceComplete(sentence);
                this.currentSentence = [];
            }
        }, interval);
    }

    stop() {
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
    }

    private finish() {
        this.stop();

        // Speak any remaining sentence
        if (this.currentSentence.length > 0) {
            const sentence = this.currentSentence.join(' ');
            this.options.onSentenceComplete(sentence);
        }

        this.options.onComplete();
    }
}

// TTS Queue using Google Cloud TTS API
class TTSQueue {
    private queue: string[] = [];
    private isPlaying: boolean = false;
    private language: string = 'en-US';
    private languageMap: { [key: string]: string } = {
        'en-US': 'English',
        'hi-IN': 'Hindi'
    };

    constructor(language: string) {
        this.language = language;
        console.log(`🎤 TTSQueue initialized for language: ${language}`);
    }

    async addSentence(sentence: string) {
        console.log(`📝 Adding to TTS queue: "${sentence.substring(0, 50)}..."`);
        this.queue.push(sentence);
        if (!this.isPlaying) {
            await this.playNext();
        }
    }

    private async playNext() {
        if (this.queue.length === 0) {
            this.isPlaying = false;
            console.log('✅ TTS queue finished');
            return;
        }

        this.isPlaying = true;
        const sentence = this.queue.shift()!;

        // Use Google Cloud TTS
        await this.speakWithGoogleTTS(sentence);

        // Play next sentence
        await this.playNext();
    }

    private async speakWithGoogleTTS(text: string): Promise<void> {
        try {
            const languageName = this.languageMap[this.language] || 'English';
            console.log(`🎤 Requesting Google TTS: "${text.substring(0, 50)}" in ${languageName}`);

            const response = await fetch('http://localhost:8000/api/tts', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text: text,
                    language: languageName
                })
            });

            if (!response.ok) {
                console.error(`❌ TTS request failed: ${response.status}`);
                return;
            }

            const data = await response.json();

            if (!data.audio) {
                console.error('❌ No audio data in response');
                return;
            }

            console.log('✅ TTS audio received, playing...');

            // Create and play audio
            const audio = new Audio(`data:audio/mp3;base64,${data.audio}`);

            // Wait for audio to finish playing
            await new Promise<void>((resolve, reject) => {
                audio.onloadeddata = () => {
                    console.log('🔊 Audio loaded, starting playback...');
                    audio.play()
                        .then(() => console.log('✅ Audio playing'))
                        .catch(err => {
                            console.error('❌ Audio play error:', err);
                            reject(err);
                        });
                };

                audio.onended = () => {
                    console.log('✅ Audio finished');
                    resolve();
                };

                audio.onerror = (err) => {
                    console.error('❌ Audio load error:', err);
                    reject(err);
                };
            });

        } catch (error) {
            console.error('❌ Google TTS error:', error);
        }
    }

    clear() {
        this.queue = [];
        this.isPlaying = false;
        console.log('🗑️ TTS queue cleared');
    }
}

export { TextStreamer, TTSQueue };
