import React from 'react';
import './TypingIndicator.css';

interface TypingIndicatorProps {
    isVisible?: boolean;
    message?: string;
}

/**
 * Animated breathing typing indicator component
 * Shows three dots with smooth scale + opacity animation
 * Used while AI is processing/streaming responses
 */
export const TypingIndicator: React.FC<TypingIndicatorProps> = ({
    isVisible = true,
    message = 'AI is thinking'
}) => {
    if (!isVisible) return null;

    return (
        <div className="typing-indicator-wrapper">
            <div className="typing-indicator">
                <span className="typing-dot"></span>
                <span className="typing-dot"></span>
                <span className="typing-dot"></span>
            </div>
            <span className="typing-message">{message}</span>
        </div>
    );
};
