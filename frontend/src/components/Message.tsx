import React, { useState } from 'react';
import './Message.css';

export interface MessageProps {
    id: string;
    type: 'user' | 'assistant';
    content: string;
    timestamp: Date;
    language?: string;
    isVoice?: boolean;
    onFeedback?: (messageId: string, rating: 'positive' | 'negative') => void;
    feedbackGiven?: 'positive' | 'negative' | null;
}

export const Message: React.FC<MessageProps> = ({
    id,
    type,
    content,
    timestamp,
    language,
    isVoice,
    onFeedback,
    feedbackGiven
}) => {
    const [showFeedback, setShowFeedback] = useState(false);

    const handleFeedback = (rating: 'positive' | 'negative') => {
        if (onFeedback && !feedbackGiven) {
            onFeedback(id, rating);
        }
    };

    const formatTime = (date: Date) => {
        return new Date(date).toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    return (
        <div
            className={`message ${type}`}
            onMouseEnter={() => type === 'assistant' && setShowFeedback(true)}
            onMouseLeave={() => setShowFeedback(false)}
        >
            <div className="message-header">
                <span className="message-sender">
                    {type === 'user' ? 'You' : 'AI Assistant'}
                </span>
                <span className="message-meta">
                    {isVoice && <span className="voice-badge">🎤 Voice</span>}
                    {language && <span className="language-badge">{language}</span>}
                    <span className="message-time">{formatTime(timestamp)}</span>
                </span>
            </div>

            <div className="message-content">
                {content}
            </div>

            {/* Feedback buttons for assistant messages */}
            {type === 'assistant' && (showFeedback || feedbackGiven) && (
                <div className="message-feedback">
                    <button
                        className={`feedback-btn ${feedbackGiven === 'positive' ? 'active' : ''}`}
                        onClick={() => handleFeedback('positive')}
                        disabled={!!feedbackGiven}
                        title="Helpful"
                    >
                        👍 {feedbackGiven === 'positive' && '✓'}
                    </button>
                    <button
                        className={`feedback-btn ${feedbackGiven === 'negative' ? 'active' : ''}`}
                        onClick={() => handleFeedback('negative')}
                        disabled={!!feedbackGiven}
                        title="Not Helpful"
                    >
                        👎 {feedbackGiven === 'negative' && '✓'}
                    </button>
                </div>
            )}
        </div>
    );
};
