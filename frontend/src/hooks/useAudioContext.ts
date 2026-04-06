import { useEffect, useRef, useState, useCallback } from 'react';

/**
 * Hook to manage Web Audio API context and frequency analysis
 * Provides real-time frequency data from microphone input
 */
export function useAudioContext() {
    const audioContextRef = useRef<AudioContext | null>(null);
    const analyserRef = useRef<AnalyserNode | null>(null);
    const micStreamRef = useRef<MediaStream | null>(null);
    const dataArrayRef = useRef<Uint8Array | null>(null);
    const animationIdRef = useRef<number | null>(null);
    const [frequencyData, setFrequencyData] = useState<number[]>(new Array(30).fill(0));
    const [isActive, setIsActive] = useState(false);

    const initializeAudio = useCallback(async () => {
        try {
            if (audioContextRef.current?.state === 'running') {
                return; // Already initialized
            }

            // Create or resume audio context
            const audioContext = audioContextRef.current || new (window.AudioContext || (window as any).webkitAudioContext)();
            audioContextRef.current = audioContext;

            // Resume context if suspended (required for user interaction)
            if (audioContext.state === 'suspended') {
                await audioContext.resume();
            }

            // Get microphone stream
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            micStreamRef.current = stream;

            // Create analyser
            const source = audioContext.createMediaStreamSource(stream);
            const analyser = audioContext.createAnalyser();
            analyser.fftSize = 256; // Frequency bins
            analyser.smoothingTimeConstant = 0.8; // Smooth animations

            source.connect(analyser);
            analyserRef.current = analyser;

            // Create data array for frequency data
            const bufferLength = analyser.frequencyBinCount;
            dataArrayRef.current = new Uint8Array(bufferLength);

            setIsActive(true);
            return stream;
        } catch (error) {
            console.error('Failed to initialize audio context:', error);
            setIsActive(false);
            return null;
        }
    }, []);

    const startVisualization = useCallback(() => {
        if (!analyserRef.current || !dataArrayRef.current) return;

        const animate = () => {
            animationIdRef.current = requestAnimationFrame(animate);

            // Get frequency data
            const dataArray = dataArrayRef.current;
            if (dataArray && analyserRef.current) {
                (analyserRef.current as AnalyserNode).getByteFrequencyData(dataArray as any);

                // Downsample to 30 bars for visualization (better performance)
                const barCount = 30;
                const bars: number[] = [];

                for (let i = 0; i < barCount; i++) {
                    const startIdx = Math.floor((i / barCount) * dataArray.length);
                    const endIdx = Math.floor(((i + 1) / barCount) * dataArray.length);

                    let sum = 0;
                    for (let j = startIdx; j < endIdx; j++) {
                        sum += dataArray[j];
                    }
                    const avg = sum / (endIdx - startIdx);
                    bars.push(avg / 255); // Normalize to 0-1
                }

                setFrequencyData(bars);
            }
        };

        animate();
    }, []);

    const stopVisualization = useCallback(() => {
        if (animationIdRef.current) {
            cancelAnimationFrame(animationIdRef.current);
            animationIdRef.current = null;
        }
    }, []);

    const cleanup = useCallback(() => {
        stopVisualization();

        // Stop microphone stream
        if (micStreamRef.current) {
            micStreamRef.current.getTracks().forEach(track => track.stop());
            micStreamRef.current = null;
        }

        // Close audio context
        if (audioContextRef.current && audioContextRef.current.state !== 'closed') {
            audioContextRef.current.close();
            audioContextRef.current = null;
        }

        analyserRef.current = null;
        dataArrayRef.current = null;
        setIsActive(false);
        setFrequencyData(new Array(30).fill(0));
    }, [stopVisualization]);

    useEffect(() => {
        return () => {
            cleanup();
        };
    }, [cleanup]);

    return {
        frequencyData,
        isActive,
        initializeAudio,
        startVisualization,
        stopVisualization,
        cleanup,
    };
}
