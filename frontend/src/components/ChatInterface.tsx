import { useEffect, useRef, useState } from 'react';
import { SkeletonLoader } from './SkeletonLoader';
import { TimeGroupDivider } from './TimeGroupDivider';
import { ConfidenceBar } from './ConfidenceBar';
import './ChatInterface.css';

export interface Message {
    id: string;
    type: 'user' | 'assistant';
    content: string;
    timestamp: Date;
    language?: string;
    isVoice?: boolean;
    highlightedWordIndex?: number;  // For synced audio word highlighting
    trustScore?: number;
    feedback?: 'positive' | 'negative' | null;
    feedbackReason?: string;
    // Message delivery status (Phase 2.3)
    status?: 'sending' | 'sent' | 'delivered' | 'read';
    statusTimestamp?: Date;
    evidence?: Array<{
        rank: number;
        score: number;
        raw_score: number;
        snippet: string;
        metadata: Record<string, any>;
    }>;
    sources?: Array<{
        content: string;
        metadata: Record<string, any>;
        distance: number;
    }>;
}

interface ChatInterfaceProps {
    messages: Message[];
    isProcessing?: boolean;
    onRegenerate?: (messageId: string) => void;
    onFeedback?: (messageId: string, rating: 'positive' | 'negative', reason?: string) => void;
}

export function ChatInterface({ messages, isProcessing, onRegenerate, onFeedback }: ChatInterfaceProps) {
    const [hoveredMessageId, setHoveredMessageId] = useState<string | null>(null);
    const [feedbackComments, setFeedbackComments] = useState<Record<string, string>>({});
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const formatTime = (date: Date) => {
        return date.toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    // Phase 2.6: Determine time group for a message
    const getTimeGroup = (messageDate: Date): { group: string; label: string } => {
        const now = new Date();
        const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
        const yesterday = new Date(today);
        yesterday.setDate(yesterday.getDate() - 1);
        const lastWeek = new Date(today);
        lastWeek.setDate(lastWeek.getDate() - 7);
        const lastMonth = new Date(today);
        lastMonth.setMonth(lastMonth.getMonth() - 1);

        const msgDate = new Date(messageDate.getFullYear(), messageDate.getMonth(), messageDate.getDate());

        if (msgDate.getTime() === today.getTime()) {
            return { group: 'today', label: 'Today' };
        } else if (msgDate.getTime() === yesterday.getTime()) {
            return { group: 'yesterday', label: 'Yesterday' };
        } else if (msgDate >= lastWeek) {
            return { group: 'lastWeek', label: 'Last 7 Days' };
        } else if (msgDate >= lastMonth) {
            return { group: 'lastMonth', label: 'Last Month' };
        } else {
            return { group: 'older', label: msgDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: msgDate.getFullYear() !== now.getFullYear() ? 'numeric' : undefined }) };
        }
    };

    // Voice sync stays enabled, but visual word highlighting is disabled.
    const renderMessageContent = (message: Message) => {
        return message.content;
    };

    const getStatusDisplay = (status?: string) => {
        switch (status) {
            case 'sending':
                return { icon: '✓', label: 'Sending...', className: 'status-sending' };
            case 'sent':
                return { icon: '✓', label: 'Sent', className: 'status-sent' };
            case 'delivered':
                return { icon: '✓✓', label: 'Delivered', className: 'status-delivered' };
            case 'read':
                return { icon: '✓✓', label: 'Read', className: 'status-read' };
            default:
                return null;
        }
    };

    const handleCopy = async (content: string) => {
        try {
            await navigator.clipboard.writeText(content);
        } catch (error) {
            console.warn('Copy failed:', error);
        }
    };

    const handleRegenerate = (messageId: string) => {
        if (onRegenerate) {
            onRegenerate(messageId);
        }
    };

    const buildFallbackEvidence = (message: Message) => {
        const sources = message.sources || [];
        if (sources.length === 0) {
            return { trustScore: undefined as number | undefined, evidence: [] as NonNullable<Message['evidence']> };
        }

        const top = sources.slice(0, 3);
        const confidences = top.map((s) => Math.max(0, Math.min(1, Number(s.distance || 0))));
        const topConfidence = confidences[0];
        const avgConfidence = confidences.reduce((a, b) => a + b, 0) / confidences.length;

        const answerTokens = new Set((message.content || '').toLowerCase().split(/\W+/).filter(Boolean));
        const contextTokens = new Set(
            top
                .map((s) => (s.content || '').toLowerCase())
                .join(' ')
                .split(/\W+/)
                .filter(Boolean)
        );
        const coverage =
            answerTokens.size > 0 && contextTokens.size > 0
                ? [...answerTokens].filter((t) => contextTokens.has(t)).length / answerTokens.size
                : 0;

        const agreement = confidences.filter((c) => c >= 0.6).length / confidences.length;

        const evidence = top.map((s, idx) => ({
            rank: idx + 1,
            score: Number((confidences[idx] * 100).toFixed(2)),
            raw_score: Number((Number(s.distance || 0)).toFixed(6)),
            snippet: (s.content || '').slice(0, 280) + ((s.content || '').length > 280 ? '...' : ''),
            metadata: s.metadata || {},
        }));

        const trustScore = Number(
            ((0.55 * topConfidence + 0.25 * avgConfidence + 0.15 * coverage + 0.05 * agreement) * 100).toFixed(2)
        );
        return { trustScore, evidence };
    };

    const shouldShowProcessing =
        !!isProcessing && !(messages.length > 0 && messages[messages.length - 1]?.type === 'assistant');

    // Phase 2.6: Build messages array with time group dividers
    const messagesWithDividers = messages.reduce((acc, message, index) => {
        const currentGroup = getTimeGroup(message.timestamp);
        const previousMessage = index > 0 ? messages[index - 1] : null;
        const previousGroup = previousMessage ? getTimeGroup(previousMessage.timestamp) : null;

        // Add divider if group changed
        if (previousGroup === null || previousGroup.group !== currentGroup.group) {
            acc.push({
                type: 'divider',
                id: `divider-${currentGroup.group}-${index}`,
                label: currentGroup.label,
                timestamp: message.timestamp
            });
        }

        acc.push(message);
        return acc;
    }, [] as any[]);

    return (
        <div className="chat-messages">
            {messagesWithDividers.map((item, index) => {
                // Render time group divider
                if (item.type === 'divider') {
                    return (
                        <TimeGroupDivider
                            key={item.id}
                            label={item.label}
                        />
                    );
                }

                // Render regular message
                const message = item as Message;
                const fallback = buildFallbackEvidence(message);
                const effectiveTrustScore = message.trustScore ?? fallback.trustScore;
                const effectiveEvidence = (message.evidence && message.evidence.length > 0) ? message.evidence : fallback.evidence;
                const strongEvidence = effectiveEvidence.filter((item) => item.score >= 20);
                const weakEvidence = effectiveEvidence.filter((item) => item.score < 20);

                return (
                <div
                    key={message.id}
                    className={`message-wrapper ${message.type}`}
                    style={{ animationDelay: `${index * 0.1}s` }}
                >
                    <div className="message-avatar">
                        {message.type === 'user' ? (
                            <div className="avatar user-avatar">
                                <span className="avatar-emoji">👤</span>
                            </div>
                        ) : (
                            <div className="avatar assistant-avatar">
                                <span className="avatar-emoji">🤖</span>
                                <div className="avatar-pulse"></div>
                            </div>
                        )}
                    </div>

                    <div className="message-content-wrapper">
                        <div className="message-header">
                            <span className="message-sender">
                                {message.type === 'user' ? 'You' : 'AI Assistant'}
                            </span>
                            {message.isVoice && (
                                <span className="voice-badge">
                                    🎤 Voice
                                </span>
                            )}
                            <span className="message-time">
                                {formatTime(message.timestamp)}
                            </span>
                        </div>

                        <div
                            className={`message-bubble ${message.type}`}
                            onMouseEnter={() => message.type === 'assistant' && setHoveredMessageId(message.id)}
                            onMouseLeave={() => message.type === 'assistant' && setHoveredMessageId(null)}
                        >
                            <div className="message-text">
                                {renderMessageContent(message)}
                            </div>

                            {message.type === 'assistant' && hoveredMessageId === message.id && (
                                <div className="assistant-hover-actions">
                                    <button className="hover-action-btn" onClick={() => handleCopy(message.content)} title="Copy answer">
                                        📋 Copy
                                    </button>
                                    <button className="hover-action-btn" onClick={() => handleRegenerate(message.id)} title="Regenerate answer">
                                        🔁 Regenerate
                                    </button>
                                </div>
                            )}

                            {message.type === 'assistant' && (
                                <div className="message-decoration">
                                    <div className="sparkle">✨</div>
                                </div>
                            )}
                        </div>

                        {message.type === 'assistant' && (
                            <div className="message-feedback-row">
                                <button
                                    className={`feedback-btn ${message.feedback === 'positive' ? 'active' : ''}`}
                                onClick={() => onFeedback?.(message.id, 'positive')}
                                disabled={message.feedback !== undefined}
                                title="Helpful"
                            >
                                👍
                            </button>
                            <button
                                className={`feedback-btn ${message.feedback === 'negative' ? 'active' : ''}`}
                                onClick={() => onFeedback?.(message.id, 'negative')}
                                disabled={message.feedback !== undefined}
                                title="Not helpful"
                            >
                                👎
                            </button>
                            {message.feedback === 'positive' && (
                                <span className="feedback-sentiment">
                                    Thank you for your feedback!
                                </span>
                            )}
                            {message.feedback === 'negative' && message.feedbackReason && (
                                <span className="feedback-sentiment">
                                    Thank you for your feedback — we will improve it.
                                </span>
                            )}
                        </div>
                    )}

                    {message.type === 'assistant' && message.feedback === 'negative' && !message.feedbackReason && (
                        <div className="feedback-comment-box">
                            <textarea
                                className="feedback-textarea"
                                placeholder="Tell us what was wrong..."
                                value={feedbackComments[message.id] ?? ''}
                                onChange={(e) => setFeedbackComments(prev => ({ ...prev, [message.id]: e.target.value }))}
                                rows={3}
                            />
                            <button
                                className="feedback-submit-btn"
                                type="button"
                                disabled={!feedbackComments[message.id]?.trim()}
                                onClick={() => {
                                    const comment = feedbackComments[message.id]?.trim();
                                    if (!comment) return;
                                    onFeedback?.(message.id, 'negative', comment);
                                    setFeedbackComments(prev => ({ ...prev, [message.id]: '' }));
                                }}
                            >
                                Submit feedback
                            </button>
                        </div>
                    )}

                    {message.type === 'user' && message.status && (
                        <div className={`message-status ${getStatusDisplay(message.status)?.className}`}>
                            <span className="status-icon" title={getStatusDisplay(message.status)?.label}>
                                {getStatusDisplay(message.status)?.icon}
                            </span>
                        </div>
                    )}

                        {message.type === 'assistant' && (effectiveTrustScore !== undefined || effectiveEvidence.length > 0) && (
                            <div className="trust-evidence-panel">
                                {effectiveTrustScore !== undefined && (
                                    <ConfidenceBar
                                        score={effectiveTrustScore}
                                        evidence={effectiveEvidence}
                                        sources={message.sources}
                                    />
                                )}

                                {!!effectiveEvidence.length && (
                                    <details className="evidence-details">
                                        <summary>View Evidence ({strongEvidence.length})</summary>
                                        <div className="evidence-list">
                                            <div className="evidence-summary">
                                                {strongEvidence.length} strong source{strongEvidence.length === 1 ? '' : 's'}, {weakEvidence.length} weak source{weakEvidence.length === 1 ? '' : 's'}
                                            </div>

                                            {strongEvidence.map((item) => (
                                                <div key={`${message.id}-ev-${item.rank}`} className="evidence-item">
                                                    <div className="evidence-meta">
                                                        <span>#{item.rank}</span>
                                                        <span>{item.score.toFixed(1)}%</span>
                                                    </div>
                                                    <p>{item.snippet}</p>
                                                </div>
                                            ))}

                                            {!!weakEvidence.length && (
                                                <details className="weak-evidence-details">
                                                    <summary>Weak Context ({weakEvidence.length})</summary>
                                                    <div className="weak-evidence-list">
                                                        {weakEvidence.map((item) => (
                                                            <div key={`${message.id}-weak-${item.rank}`} className="evidence-item weak">
                                                                <div className="evidence-meta">
                                                                    <span>#{item.rank}</span>
                                                                    <span>{item.score.toFixed(1)}%</span>
                                                                </div>
                                                                <p>{item.snippet}</p>
                                                            </div>
                                                        ))}
                                                    </div>
                                                </details>
                                            )}
                                        </div>
                                    </details>
                                )}
                            </div>
                        )}

                        {message.language && message.language !== 'English' && (
                            <div className="language-tag">
                                🌐 {message.language}
                            </div>
                        )}
                    </div>
                </div>
                );
            })}

            {shouldShowProcessing && (
                <div className="message-wrapper assistant processing">
                    <div className="message-avatar">
                        <div className="avatar assistant-avatar">
                            <span className="avatar-emoji">🤖</span>
                            <div className="avatar-pulse active"></div>
                        </div>
                    </div>

                    <div className="message-content-wrapper">
                        <div className="message-header">
                            <span className="message-sender">AI Assistant</span>
                        </div>

                        <div className="message-bubble assistant">
                            <SkeletonLoader lines={3} hasShortLine={true} />
                        </div>
                    </div>
                </div>
            )}

            <div ref={messagesEndRef} />
        </div>
    );
}
