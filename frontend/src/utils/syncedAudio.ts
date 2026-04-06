/**
 * Synced Audio Playback Utility
 * Perfectly synchronizes text highlighting with audio word-by-word
 */

import { API_BASE_URL } from '../services/api';

const TTS_REQUEST_TIMEOUT_MS = 45000;
const TTS_MAX_RETRIES = 2;

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export interface WordTiming {
    word: string;
    start: number;  // seconds
    end: number;    // seconds
    textOffset: number;
    wordLength: number;
}

export interface SyncedTTSResponse {
    audio: string;      // base64
    timings: WordTiming[];
    format: string;
}

export class SyncedAudioPlayer {
    private audio: HTMLAudioElement | null = null;
    private timings: WordTiming[] = [];
    private animationFrameId: number | null = null;
    private onWordHighlight: ((wordIndex: number, word: string) => void) | null = null;
    private onComplete: (() => void) | null = null;
    private currentWordIndex: number = -1;
    private isPlaying: boolean = false;

    constructor() {
        console.log('🎵 SyncedAudioPlayer initialized');
    }

    /**
     * Load and play synced audio with word highlighting
     */
    async play(
        audioBase64: string,
        timings: WordTiming[],
        onWordHighlight: (wordIndex: number, word: string) => void,
        onComplete?: () => void
    ): Promise<void> {
        // Clean up previous playback
        this.stop();

        this.timings = timings;
        this.onWordHighlight = onWordHighlight;
        this.onComplete = onComplete || null;
        this.currentWordIndex = -1;

        console.log(`🎵 Playing synced audio with ${timings.length} word timings`);

        // Create audio element
        this.audio = new Audio(`data:audio/mp3;base64,${audioBase64}`);
        
        return new Promise((resolve, reject) => {
            if (!this.audio) {
                reject(new Error('Failed to create audio element'));
                return;
            }

            this.audio.onloadeddata = () => {
                console.log('✅ Audio loaded, starting playback...');
                this.audio!.play()
                    .then(() => {
                        console.log('✅ Audio playing');
                        this.isPlaying = true;
                        window.dispatchEvent(new CustomEvent('tts-started'));
                        this.startWordTracking();
                    })
                    .catch(err => {
                        console.error('❌ Audio play error:', err);
                        reject(err);
                    });
            };

            this.audio.onended = () => {
                console.log('✅ Audio finished');
                this.isPlaying = false;
                this.stopWordTracking();
                window.dispatchEvent(new CustomEvent('tts-ended'));
                if (this.onComplete) {
                    this.onComplete();
                }
                resolve();
            };

            this.audio.onerror = (err) => {
                console.error('❌ Audio load error:', err);
                this.isPlaying = false;
                window.dispatchEvent(new CustomEvent('tts-ended'));
                reject(err);
            };
        });
    }

    /**
     * Start tracking current word based on audio playback time
     */
    private startWordTracking() {
        const updateCurrentWord = () => {
            if (!this.audio || !this.isPlaying) {
                return;
            }

            const currentTime = this.audio.currentTime;
            const startIndex = Math.max(this.currentWordIndex, 0);

            // Find the word that should be highlighted at this time
            for (let i = startIndex; i < this.timings.length; i++) {
                const timing = this.timings[i];
                
                // If we're within this word's time range
                if (currentTime >= timing.start && currentTime < timing.end) {
                    if (i !== this.currentWordIndex) {
                        this.currentWordIndex = i;
                        if (this.onWordHighlight) {
                            this.onWordHighlight(i, timing.word);
                        }
                    }
                    break;
                }
                
                // If we've passed this word, check the next one
                if (currentTime >= timing.end && i === this.currentWordIndex) {
                    this.currentWordIndex = i + 1;
                }
            }

            // Continue tracking
            this.animationFrameId = requestAnimationFrame(updateCurrentWord);
        };

        updateCurrentWord();
    }

    /**
     * Stop word tracking
     */
    private stopWordTracking() {
        if (this.animationFrameId !== null) {
            cancelAnimationFrame(this.animationFrameId);
            this.animationFrameId = null;
        }
    }

    /**
     * Stop playback and clean up
     */
    stop() {
        this.isPlaying = false;
        this.stopWordTracking();

        if (this.audio) {
            this.audio.pause();
            this.audio.currentTime = 0;
            this.audio = null;
        }

        this.timings = [];
        this.currentWordIndex = -1;
        this.onWordHighlight = null;
        this.onComplete = null;
        window.dispatchEvent(new CustomEvent('tts-ended'));
    }

    /**
     * Check if currently playing
     */
    get playing(): boolean {
        return this.isPlaying;
    }
}

/**
 * Synced TTS Queue - queues sentences and plays them with word sync
 */
export class SyncedTTSQueue {
    private queue: { text: string; language: string }[] = [];
    private isPlaying: boolean = false;
    private player: SyncedAudioPlayer;
    private onWordUpdate: ((wordIndex: number, word: string, sentenceIndex: number) => void) | null = null;
    private currentSentenceIndex: number = 0;

    constructor() {
        this.player = new SyncedAudioPlayer();
        console.log('🎤 SyncedTTSQueue initialized');
    }

    /**
     * Set callback for word updates
     */
    setWordUpdateCallback(
        callback: (wordIndex: number, word: string, sentenceIndex: number) => void
    ) {
        this.onWordUpdate = callback;
    }

    /**
     * Add sentence to queue
     */
    async addSentence(text: string, language: string = 'English') {
        console.log(`📝 Adding to synced TTS queue: "${text.substring(0, 50)}..."`);
        this.queue.push({ text, language });
        
        if (!this.isPlaying) {
            await this.playNext();
        }
    }

    /**
     * Play next sentence in queue
     */
    private async playNext() {
        if (this.queue.length === 0) {
            this.isPlaying = false;
            this.currentSentenceIndex = 0;
            console.log('✅ Synced TTS queue finished');
            return;
        }

        this.isPlaying = true;
        const { text, language } = this.queue.shift()!;

        await this.speakWithSyncedTTS(text, language);
        await this.playNext();
    }

    /**
     * Speak text with synced word highlighting
     */
    private async speakWithSyncedTTS(text: string, language: string): Promise<void> {
        try {
            const startedAt = performance.now();
            console.log(`🎤 Requesting synced TTS: "${text.substring(0, 50)}" in ${language}`);

            let response: Response | null = null;
            let attempt = 0;

            while (attempt <= TTS_MAX_RETRIES) {
                attempt += 1;
                const controller = new AbortController();
                const timeoutId = setTimeout(() => controller.abort(), TTS_REQUEST_TIMEOUT_MS);

                try {
                    response = await fetch(`${API_BASE_URL}/api/tts-synced`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ text, language }),
                        signal: controller.signal,
                    });

                    if (response.ok) {
                        break;
                    }

                    const retryableStatus = response.status === 502 || response.status === 503 || response.status === 504;
                    if (!retryableStatus || attempt > TTS_MAX_RETRIES) {
                        console.error(`❌ Synced TTS request failed: ${response.status}`);
                        return;
                    }

                    console.warn(`⚠️ Synced TTS retry ${attempt}/${TTS_MAX_RETRIES} after status ${response.status}`);
                    await sleep(700 * attempt);
                } catch (error: any) {
                    const aborted = error?.name === 'AbortError';
                    if (attempt > TTS_MAX_RETRIES) {
                        console.error(`❌ Synced TTS ${aborted ? 'timeout' : 'network'} error:`, error);
                        return;
                    }
                    console.warn(`⚠️ Synced TTS retry ${attempt}/${TTS_MAX_RETRIES} after ${aborted ? 'timeout' : 'network error'}`);
                    await sleep(700 * attempt);
                } finally {
                    clearTimeout(timeoutId);
                }
            }

            if (!response || !response.ok) {
                return;
            }

            const data: SyncedTTSResponse = await response.json();

            if (!data.audio || !data.timings) {
                console.error('❌ No audio or timing data in response');
                return;
            }

            console.log(`✅ Synced TTS received: ${data.timings.length} words`);

            // Play with word highlighting
            const sentenceIndex = this.currentSentenceIndex;
            await this.player.play(
                data.audio,
                data.timings,
                (wordIndex, word) => {
                    if (this.onWordUpdate) {
                        this.onWordUpdate(wordIndex, word, sentenceIndex);
                    }
                }
            );

            this.currentSentenceIndex++;

            console.log(`📊 Synced TTS chunk telemetry`, {
                chars: text.length,
                words: data.timings.length,
                durationMs: Math.round(performance.now() - startedAt),
                queueRemaining: this.queue.length,
            });

        } catch (error) {
            console.error('❌ Synced TTS error:', error);
        }
    }

    /**
     * Clear queue and stop playback
     */
    clear() {
        this.queue = [];
        this.player.stop();
        this.isPlaying = false;
        this.currentSentenceIndex = 0;
        console.log('🗑️ Synced TTS queue cleared');
    }

    /**
     * Check if playing
     */
    get playing(): boolean {
        return this.isPlaying;
    }
}
