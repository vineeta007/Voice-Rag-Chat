// Professional Text-to-Speech using Google Cloud TTS
import { API_BASE_URL } from '../services/api';

// Global audio instance to track current playback
let currentAudio: HTMLAudioElement | null = null;
let isSpeaking = false;

export const speakText = async (text: string, language: string = 'en-US') => {
    try {
        // Stop any ongoing speech first
        stopSpeaking();

        // Map language codes to language names
        const langMap: { [key: string]: string } = {
            'en-US': 'English',
            'hi-IN': 'Hindi'
        };

        const languageName = langMap[language] || 'English';

        console.log('🔊 Requesting TTS for:', text.substring(0, 50) + '...', 'Language:', languageName);

        // Call backend TTS API
        const response = await fetch(`${API_BASE_URL}/api/tts`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                text: text,
                language: languageName
            })
        });

        if (!response.ok) {
            const error = await response.json();
            console.error('TTS API error:', error);

            // Fallback to browser TTS
            return fallbackBrowserTTS(text, language);
        }

        const data = await response.json();

        // Decode base64 audio
        const audioData = atob(data.audio);
        const arrayBuffer = new ArrayBuffer(audioData.length);
        const view = new Uint8Array(arrayBuffer);
        for (let i = 0; i < audioData.length; i++) {
            view[i] = audioData.charCodeAt(i);
        }

        // Create blob and play
        const audioBlob = new Blob([arrayBuffer], { type: 'audio/mp3' });
        const audioUrl = URL.createObjectURL(audioBlob);
        currentAudio = new Audio(audioUrl);
        isSpeaking = true;

        currentAudio.onended = () => {
            URL.revokeObjectURL(audioUrl);
            currentAudio = null;
            isSpeaking = false;
            console.log('✅ Speech finished');
            // Dispatch event for UI update
            window.dispatchEvent(new CustomEvent('tts-ended'));
        };

        currentAudio.onerror = (e) => {
            console.error('Audio playback error:', e);
            URL.revokeObjectURL(audioUrl);
            currentAudio = null;
            isSpeaking = false;
            window.dispatchEvent(new CustomEvent('tts-ended'));
        };

        await currentAudio.play();
        console.log('🔊 Playing Google Cloud TTS audio');
        // Dispatch event for UI update
        window.dispatchEvent(new CustomEvent('tts-started'));

        return true;
    } catch (error) {
        console.error('TTS error:', error);
        isSpeaking = false;
        // Fallback to browser TTS
        return fallbackBrowserTTS(text, language);
    }
};

// Fallback to browser's built-in TTS
const fallbackBrowserTTS = (text: string, language: string) => {
    if ('speechSynthesis' in window) {
        console.log('⚠️ Falling back to browser TTS');
        
        // Ensure synthesis is ready
        const speak = () => {
            window.speechSynthesis.cancel();

            const utterance = new SpeechSynthesisUtterance(text);
            utterance.lang = language;
            utterance.rate = 0.9;
            utterance.pitch = 1.0;
            utterance.volume = 0.9;

            utterance.onstart = () => {
                isSpeaking = true;
                window.dispatchEvent(new CustomEvent('tts-started'));
                console.log('🔊 Browser TTS started');
            };

            utterance.onend = () => {
                isSpeaking = false;
                window.dispatchEvent(new CustomEvent('tts-ended'));
                console.log('✅ Browser TTS finished');
            };

            utterance.onerror = (e) => {
                console.error('Browser TTS error:', e);
                isSpeaking = false;
                window.dispatchEvent(new CustomEvent('tts-ended'));
            };

            // Try to find a better voice
            const voices = window.speechSynthesis.getVoices();
            if (voices.length > 0) {
                const voice = voices.find(v => v.lang.startsWith(language.split('-')[0]));
                if (voice) {
                    utterance.voice = voice;
                    console.log('🎤 Using voice:', voice.name);
                }
            }

            window.speechSynthesis.speak(utterance);
        };

        // Load voices if not already loaded
        const voices = window.speechSynthesis.getVoices();
        if (voices.length > 0) {
            speak();
        } else {
            // Wait for voices to load
            window.speechSynthesis.onvoiceschanged = () => {
                speak();
            };
            // Fallback timeout in case voices don't load
            setTimeout(speak, 100);
        }
        
        return true;
    }
    console.error('❌ Browser TTS not supported');
    return false;
};

export const stopSpeaking = () => {
    // Stop Google Cloud TTS audio
    if (currentAudio) {
        currentAudio.pause();
        currentAudio.currentTime = 0;
        currentAudio = null;
    }

    // Stop browser TTS
    if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
    }

    isSpeaking = false;
    window.dispatchEvent(new CustomEvent('tts-ended'));
    console.log('🛑 Speech stopped');
};

export const isTTSSpeaking = () => isSpeaking;
