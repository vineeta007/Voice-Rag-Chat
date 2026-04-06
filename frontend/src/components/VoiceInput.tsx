import React, { useState, useRef, useEffect } from 'react';
import { VoiceWaveform } from './VoiceWaveform';

interface VoiceInputProps {
    onTranscript: (text: string, detectedLanguage?: string) => void;
    isProcessing: boolean;
    selectedLanguage: string;
}

export const VoiceInput: React.FC<VoiceInputProps> = ({ onTranscript, isProcessing, selectedLanguage }) => {
    const [isListening, setIsListening] = useState(false);
    const [isInitializing, setIsInitializing] = useState(false);
    const [transcript, setTranscript] = useState('');
    const [browserWarning, setBrowserWarning] = useState<string | null>(null);
    const [voiceError, setVoiceError] = useState<string | null>(null);
    const [voiceDisabled, setVoiceDisabled] = useState(false);
    const recognitionRef = useRef<any>(null);
    const transcriptRef = useRef(''); // Ref to access latest transcript in closures
    const hasSubmittedRef = useRef(false); // Ref to prevent double submission
    const lastErrorRef = useRef<string | null>(null);
    const startTimeoutRef = useRef<number | null>(null);

    // Detect Brave browser
    const isBrave = () => {
        return navigator.userAgent.includes('Brave');
    };

    useEffect(() => {
        // Check for Brave browser and show warning
        if (isBrave()) {
            setBrowserWarning('Brave browser detected. Voice input may be blocked by privacy shields. Please disable shields for this site or try Chrome/Edge.');
        }

        // Initialize Web Speech API
        if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
            const SpeechRecognition = (window as any).webkitSpeechRecognition || (window as any).SpeechRecognition;
            const recognition = new SpeechRecognition();

            // Adjust settings based on browser
            if (isBrave()) {
                // Brave has issues with continuous mode
                recognition.continuous = false;
                recognition.interimResults = false;
            } else {
                recognition.continuous = true;
                recognition.interimResults = true;
            }
            
            recognition.maxAlternatives = 1;

            // Map selected language to browser language code (only well-supported languages)
            const languageCodeMap: { [key: string]: string } = {
                'English': 'en-US',
                'Hindi': 'hi-IN'
            };

            recognition.lang = languageCodeMap[selectedLanguage] || 'en-US';
            console.log('🎤 Speech recognition language set to:', recognition.lang);

            recognition.onstart = () => {
                console.log('🎤 Speech recognition started successfully');
                setVoiceError(null);
                lastErrorRef.current = null;
                setIsInitializing(false);
                setIsListening(true);
                if (startTimeoutRef.current) {
                    clearTimeout(startTimeoutRef.current);
                    startTimeoutRef.current = null;
                }
                setTranscript('');
                transcriptRef.current = '';
                hasSubmittedRef.current = false;
            };

            recognition.onresult = (event: any) => {
                // Accumulate all results (both interim and final)
                let fullTranscript = '';
                for (let i = 0; i < event.results.length; i++) {
                    fullTranscript += event.results[i][0].transcript;
                }

                // Update the display with current transcript
                setTranscript(fullTranscript);
                transcriptRef.current = fullTranscript;
                console.log('📝 Current transcript:', fullTranscript);
            };

            recognition.onend = () => {
                console.log('🛑 Speech recognition ended');
                setIsListening(false);

                if (lastErrorRef.current) {
                    console.warn('Speech recognition ended after error:', lastErrorRef.current);
                    lastErrorRef.current = null;
                    return;
                }

                // Send the final transcript ONLY if we haven't submitted manually yet
                if (!hasSubmittedRef.current && transcriptRef.current && transcriptRef.current.trim().length > 0) {
                    const detectedLang = recognition.lang || 'en-US';
                    console.log('✅ Final transcript (auto):', transcriptRef.current, 'Language:', detectedLang);
                    onTranscript(transcriptRef.current, detectedLang);
                    hasSubmittedRef.current = true;
                }
            };

            recognition.onerror = (event: any) => {
                console.error('❌ Speech recognition error:', event.error);
                lastErrorRef.current = event.error;
                setIsInitializing(false);
                setIsListening(false);
                if (startTimeoutRef.current) {
                    clearTimeout(startTimeoutRef.current);
                    startTimeoutRef.current = null;
                }

                if (event.error === 'network') {
                    const message = isBrave()
                        ? 'Brave browser blocked voice recognition network access. Disable shields for this site or use Chrome/Edge.'
                        : 'Speech recognition network error occurred. Please try again or use text input.';
                    setVoiceError(message);
                    if (isBrave()) {
                        setVoiceDisabled(true);
                    }
                    console.warn('Network error in speech recognition - this is usually a transient browser issue');
                } else if (event.error === 'no-speech') {
                    console.log('No speech detected - timeout');
                    setVoiceError('No speech detected. Please try again.');
                } else if (event.error === 'not-allowed') {
                    const message = isBrave()
                        ? 'Brave browser blocked microphone access. Disable shields or use another browser.'
                        : 'Microphone access denied. Please allow microphone access in browser settings.';
                    setVoiceError(message);
                    if (isBrave()) {
                        setVoiceDisabled(true);
                    }
                    alert(message);
                } else if (event.error === 'aborted') {
                    console.log('Speech recognition aborted by user or browser.');
                } else if (event.error === 'audio-capture') {
                    setVoiceError('No microphone detected. Please check your microphone connection.');
                    alert('No microphone detected. Please check your microphone connection.');
                } else {
                    const message = isBrave()
                        ? `Brave speech recognition error: ${event.error}. Try disabling shields or use Chrome/Edge.`
                        : `Speech recognition error: ${event.error}`;
                    setVoiceError(message);
                    console.warn(message);
                }
            };

            recognitionRef.current = recognition;
        }

        return () => {
            if (recognitionRef.current) {
                recognitionRef.current.abort();
            }
            if (startTimeoutRef.current) {
                clearTimeout(startTimeoutRef.current);
                startTimeoutRef.current = null;
            }
        };
    }, [onTranscript, selectedLanguage]);

    const startListening = async () => {
        if (voiceDisabled) {
            alert('Voice input is not available in Brave due to browser restrictions. Please use text input or switch to Chrome/Edge.');
            return;
        }

        if (voiceError) {
            alert(voiceError);
            return;
        }

        if (recognitionRef.current && !isListening && !isInitializing) {
            setIsInitializing(true);
            console.log('🎤 Attempting to start voice recognition...');

            try {
                // Check microphone permissions first
                if (navigator.permissions && navigator.permissions.query) {
                    try {
                        const permission = await navigator.permissions.query({ name: 'microphone' as PermissionName });
                        console.log('🎤 Microphone permission state:', permission.state);
                        if (permission.state === 'denied') {
                            setIsInitializing(false);
                            if (isBrave()) {
                                alert('Brave browser denied microphone access. Please:\n1. Click the Brave shield icon\n2. Allow microphone access\n3. Or disable shields for this site');
                            } else {
                                alert('Microphone access is blocked. Please allow microphone access in browser settings.');
                            }
                            return;
                        }
                    } catch (e) {
                        console.warn('Could not check microphone permissions:', e);
                    }
                }

                // Set a timeout to prevent hanging
                startTimeoutRef.current = setTimeout(() => {
                    console.warn('🎤 Speech recognition start timeout - forcing stop');
                    setIsInitializing(false);
                    setIsListening(false);
                    if (recognitionRef.current) {
                        try {
                            recognitionRef.current.abort();
                        } catch (e) {
                            console.error('Error aborting recognition:', e);
                        }
                    }
                    alert('Voice recognition timed out. Please try again or check your browser settings.');
                }, 5000); // 5 second timeout

                // Test if speech recognition can actually start
                recognitionRef.current.start();
                console.log('🎤 Speech recognition start() called successfully');

                transcriptRef.current = ''; // Reset ref
                hasSubmittedRef.current = false;

            } catch (error) {
                console.error('❌ Error in startListening:', error);
                setIsInitializing(false);
                if (startTimeoutRef.current) {
                    clearTimeout(startTimeoutRef.current);
                    startTimeoutRef.current = null;
                }
                const message = isBrave()
                    ? 'Voice recognition failed in Brave browser. Disable shields or use Chrome/Edge.'
                    : 'Could not start voice recognition. Please check browser microphone permissions.';
                setVoiceError(message);
                alert(message);
            }
        }
    };

    const stopListening = () => {
        if (recognitionRef.current && (isListening || isInitializing)) {
            try {
                // Clear any pending timeout
                if (startTimeoutRef.current) {
                    clearTimeout(startTimeoutRef.current);
                    startTimeoutRef.current = null;
                }

                // Send the transcript before stopping (Manual Submit)
                if (!hasSubmittedRef.current && transcriptRef.current && transcriptRef.current.trim().length > 0) {
                    const detectedLang = recognitionRef.current.lang || 'en-US';
                    console.log('✅ Sending transcript on stop:', transcriptRef.current, 'Language:', detectedLang);
                    onTranscript(transcriptRef.current, detectedLang);
                    hasSubmittedRef.current = true; // Mark as submitted
                }

                recognitionRef.current.stop();
                setIsListening(false);
                setIsInitializing(false);
                setTranscript('');
                transcriptRef.current = '';
            } catch (error) {
                console.error('Error stopping recognition:', error);
                setIsListening(false);
                setIsInitializing(false);
            }
        }
    };

    if (!('webkitSpeechRecognition' in window || 'SpeechRecognition' in window)) {
        return (
            <div className="voice-input">
                <button className="mic-button" disabled title="Speech recognition not supported in this browser">
                    🎤 ❌
                </button>
                <p style={{ color: 'red', fontSize: '12px' }}>Voice not supported in this browser</p>
            </div>
        );
    }

    return (
        <div className="voice-input">
            {browserWarning && (
                <div style={{ 
                    background: '#fff3cd', 
                    color: '#856404', 
                    padding: '8px', 
                    borderRadius: '4px', 
                    marginBottom: '8px',
                    fontSize: '12px',
                    border: '1px solid #ffeaa7'
                }}>
                    ⚠️ {browserWarning}
                </div>
            )}
            {!isListening && !isInitializing ? (
                <button
                    onClick={startListening}
                    disabled={isProcessing || Boolean(voiceError) || voiceDisabled}
                    className="mic-button"
                    title={voiceDisabled ? 'Voice input unavailable in Brave. Please use text input or Chrome/Edge.' : voiceError ? voiceError : isBrave() ? "Click to speak (Brave may block this)" : "Click to speak"}
                >
                    🎤
                </button>
            ) : isInitializing ? (
                <div className="voice-initializing">
                    <div className="initializing-spinner">⏳</div>
                    <p style={{ fontSize: '12px', color: '#666' }}>Starting voice recognition...</p>
                </div>
            ) : (
                <div className="voice-overlay">
                    <div className="voice-content">
                        <VoiceWaveform isRecording={isListening} />

                        <div className="voice-transcript">
                            {transcript || "Speak now..."}
                        </div>
                    </div>

                    <div className="voice-controls">
                        <button onClick={stopListening} className="stop-listening-btn">
                            ⏹️ Stop Listening
                        </button>
                    </div>
                </div>
            )}
            {voiceError && (
                <div style={{
                    marginTop: '10px',
                    color: '#842029',
                    background: '#f8d7da',
                    padding: '10px',
                    borderRadius: '6px',
                    border: '1px solid #f5c2c7',
                    fontSize: '12px'
                }}>
                    ⚠️ {voiceError}
                </div>
            )}
        </div>
    );
};
