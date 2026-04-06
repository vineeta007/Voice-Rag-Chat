import React, { useEffect } from 'react';
import { useAudioContext } from '../hooks/useAudioContext';
import './VoiceWaveform.css';

interface VoiceWaveformProps {
    isRecording: boolean;
    onWaveformReady?: (ready: boolean) => void;
}

/**
 * Real-time voice waveform visualizer component
 * Shows animated frequency bars responding to microphone input
 * Colors: blue (quiet) → teal (medium) → cyan (loud)
 */
export const VoiceWaveform: React.FC<VoiceWaveformProps> = ({ isRecording, onWaveformReady }) => {
    const { frequencyData, isActive, initializeAudio, startVisualization, stopVisualization, cleanup } = useAudioContext();

    useEffect(() => {
        if (isRecording && !isActive) {
            // Start recording
            initializeAudio().then(stream => {
                if (stream) {
                    startVisualization();
                    onWaveformReady?.(true);
                }
            });
        } else if (!isRecording && isActive) {
            // Stop recording
            stopVisualization();
            cleanup();
            onWaveformReady?.(false);
        }
    }, [isRecording, isActive, initializeAudio, startVisualization, stopVisualization, cleanup, onWaveformReady]);

    // Get color based on frequency magnitude (0-1)
    const getBarColor = (magnitude: number): string => {
        if (magnitude < 0.3) {
            return '#5a7ba1'; // Blue (quiet)
        } else if (magnitude < 0.6) {
            return '#6b8e99'; // Teal (medium)
        } else {
            return '#4db8d9'; // Cyan (loud)
        }
    };

    return (
        <div className="voice-waveform-container">
            <div className="voice-waveform">
                {frequencyData.map((magnitude, index) => (
                    <div
                        key={index}
                        className="waveform-bar"
                        style={{
                            height: `${Math.max(20, magnitude * 100)}%`,
                            backgroundColor: getBarColor(magnitude),
                            animationDelay: `${index * 20}ms`,
                        }}
                        title={`Frequency ${index + 1}: ${(magnitude * 100).toFixed(0)}%`}
                    />
                ))}
            </div>

            {/* Recording indicator dot */}
            <div className="recording-indicator">
                <div className="recording-dot"></div>
                <span className="recording-text">
                    {isActive ? 'Recording...' : 'Ready'}
                </span>
            </div>
        </div>
    );
};
