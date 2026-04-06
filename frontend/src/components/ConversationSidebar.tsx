import { Conversation } from '../services/storage';
import './ConversationSidebar.css';

interface ConversationSidebarProps {
    conversations: Conversation[];
    activeConversationId: string | null;
    onNewChat: () => void;
    onSelectConversation: (id: string) => void;
    onDeleteConversation: (id: string) => void;
    onSearch?: (query: string) => Conversation[];
    isOpen: boolean;
    onToggle: () => void;
}

export function ConversationSidebar({
    conversations,
    activeConversationId,
    onNewChat,
    onSelectConversation,
    onDeleteConversation,
    isOpen,
    onToggle
}: ConversationSidebarProps) {

    // Group conversations by date
    const groupedConversations = groupByDate(conversations);

    const formatTime = (date: Date) => {
        const now = new Date();
        const diff = now.getTime() - date.getTime();
        const hours = Math.floor(diff / (1000 * 60 * 60));

        if (hours < 1) return 'Just now';
        if (hours < 24) return `${hours}h ago`;
        if (hours < 48) return 'Yesterday';
        return date.toLocaleDateString();
    };

    return (
        <>
            {/* Toggle button for mobile */}
            <button className="sidebar-toggle" onClick={onToggle}>
                {isOpen ? '✕' : '☰'}
            </button>

            <div className={`conversation-sidebar ${isOpen ? 'open' : 'closed'}`}>
                {/* Header */}
                <div className="sidebar-header">
                    <h2>🎓 Voice RAG</h2>
                    <button className="new-chat-btn" onClick={onNewChat}>
                        ➕ New Chat
                    </button>
                </div>

                {/* Conversation List */}
                <div className="conversation-list">
                    {groupedConversations.today.length > 0 && (
                        <div className="conversation-group">
                            <div className="group-label">Today</div>
                            {groupedConversations.today.map(conv => (
                                <ConversationItem
                                    key={conv.id}
                                    conversation={conv}
                                    isActive={conv.id === activeConversationId}
                                    onClick={() => onSelectConversation(conv.id)}
                                    onDelete={() => onDeleteConversation(conv.id)}
                                    formatTime={formatTime}
                                />
                            ))}
                        </div>
                    )}

                    {groupedConversations.yesterday.length > 0 && (
                        <div className="conversation-group">
                            <div className="group-label">Yesterday</div>
                            {groupedConversations.yesterday.map(conv => (
                                <ConversationItem
                                    key={conv.id}
                                    conversation={conv}
                                    isActive={conv.id === activeConversationId}
                                    onClick={() => onSelectConversation(conv.id)}
                                    onDelete={() => onDeleteConversation(conv.id)}
                                    formatTime={formatTime}
                                />
                            ))}
                        </div>
                    )}

                    {groupedConversations.last7Days.length > 0 && (
                        <div className="conversation-group">
                            <div className="group-label">Last 7 Days</div>
                            {groupedConversations.last7Days.map(conv => (
                                <ConversationItem
                                    key={conv.id}
                                    conversation={conv}
                                    isActive={conv.id === activeConversationId}
                                    onClick={() => onSelectConversation(conv.id)}
                                    onDelete={() => onDeleteConversation(conv.id)}
                                    formatTime={formatTime}
                                />
                            ))}
                        </div>
                    )}

                    {groupedConversations.older.length > 0 && (
                        <div className="conversation-group">
                            <div className="group-label">Older</div>
                            {groupedConversations.older.map(conv => (
                                <ConversationItem
                                    key={conv.id}
                                    conversation={conv}
                                    isActive={conv.id === activeConversationId}
                                    onClick={() => onSelectConversation(conv.id)}
                                    onDelete={() => onDeleteConversation(conv.id)}
                                    formatTime={formatTime}
                                />
                            ))}
                        </div>
                    )}

                    {conversations.length === 0 && (
                        <div className="empty-state">
                            <p>No conversations yet</p>
                            <p className="empty-hint">Click "New Chat" to start!</p>
                        </div>
                    )}
                </div>
            </div>
        </>
    );
}

// Conversation Item Component
interface ConversationItemProps {
    conversation: Conversation;
    isActive: boolean;
    onClick: () => void;
    onDelete: () => void;
    formatTime: (date: Date) => string;
}

function ConversationItem({ conversation, isActive, onClick, onDelete, formatTime }: ConversationItemProps) {
    const handleDelete = (e: React.MouseEvent) => {
        e.stopPropagation();
        if (confirm('Delete this conversation?')) {
            onDelete();
        }
    };

    return (
        <div
            className={`conversation-item ${isActive ? 'active' : ''}`}
            onClick={onClick}
        >
            <div className="conversation-icon">💬</div>
            <div className="conversation-info">
                <div className="conversation-title">{conversation.title}</div>
                <div className="conversation-time">{formatTime(conversation.updatedAt)}</div>
            </div>
            
            {/* Unread Badge - Phase 2.5 */}
            {conversation.unreadCount && conversation.unreadCount > 0 && !isActive && (
                <div className="unread-badge">
                    {conversation.unreadCount > 99 ? '99+' : conversation.unreadCount}
                </div>
            )}
            
            <button
                className="delete-btn"
                onClick={handleDelete}
                title="Delete conversation"
            >
                🗑️
            </button>
        </div>
    );
}

// Helper function to group conversations by date
function groupByDate(conversations: Conversation[]) {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    const last7Days = new Date(today);
    last7Days.setDate(last7Days.getDate() - 7);

    return {
        today: conversations.filter(c => c.updatedAt >= today),
        yesterday: conversations.filter(c => c.updatedAt >= yesterday && c.updatedAt < today),
        last7Days: conversations.filter(c => c.updatedAt >= last7Days && c.updatedAt < yesterday),
        older: conversations.filter(c => c.updatedAt < last7Days)
    };
}
