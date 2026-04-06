import { useState } from 'react';
import './TextInput.css';

interface TextInputProps {
    onSubmit: (text: string) => void;
    isProcessing: boolean;
}

export function TextInput({ onSubmit, isProcessing }: TextInputProps) {
    const [input, setInput] = useState('');

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (input.trim() && !isProcessing) {
            onSubmit(input.trim());
            setInput('');
        }
    };

    return (
        <form className="premium-text-input-form" onSubmit={handleSubmit}>
            <div className="input-wrapper">
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Ask me anything about the university..."
                    disabled={isProcessing}
                    className="premium-text-input"
                />
                <div className="input-glow"></div>
            </div>
            <button
                type="submit"
                disabled={!input.trim() || isProcessing}
                className="premium-send-button"
            >
                {isProcessing ? (
                    <span className="loading-spinner">⏳</span>
                ) : (
                    <span className="send-icon">✨ Send</span>
                )}
            </button>
        </form>
    );
}
