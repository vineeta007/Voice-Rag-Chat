// Local storage service for conversation persistence

export interface Message {
    id: string;
    type: 'user' | 'assistant';
    content: string;
    timestamp: Date;
    language?: string;
    isVoice?: boolean;
}

export interface Conversation {
    id: string;
    title: string;
    messages: Message[];
    createdAt: Date;
    updatedAt: Date;
    language: string;
    unreadCount?: number;
}

const STORAGE_KEY = 'voicerag_conversations';
const MAX_CONVERSATIONS = 100;
const MAX_AGE_DAYS = 30;

class ConversationStorage {

    // Load all conversations from localStorage
    loadConversations(): Conversation[] {
        try {
            const data = localStorage.getItem(STORAGE_KEY);
            if (!data) return [];

            const conversations = JSON.parse(data);

            // Convert date strings back to Date objects
            return conversations.map((conv: any) => ({
                ...conv,
                createdAt: new Date(conv.createdAt),
                updatedAt: new Date(conv.updatedAt),
                messages: conv.messages.map((msg: any) => ({
                    ...msg,
                    timestamp: new Date(msg.timestamp)
                }))
            }));
        } catch (error) {
            console.error('Error loading conversations:', error);
            return [];
        }
    }

    // Save all conversations to localStorage
    saveConversations(conversations: Conversation[]): void {
        try {
            // Clean up old conversations
            const cleaned = this.cleanupOldConversations(conversations);

            // Limit number of conversations
            const limited = cleaned.slice(0, MAX_CONVERSATIONS);

            localStorage.setItem(STORAGE_KEY, JSON.stringify(limited));
        } catch (error) {
            console.error('Error saving conversations:', error);

            // If quota exceeded, remove oldest conversations
            if (error instanceof DOMException && error.name === 'QuotaExceededError') {
                const reduced = conversations.slice(0, Math.floor(MAX_CONVERSATIONS / 2));
                localStorage.setItem(STORAGE_KEY, JSON.stringify(reduced));
            }
        }
    }

    // Save a single conversation
    saveConversation(conversation: Conversation): void {
        const conversations = this.loadConversations();
        const index = conversations.findIndex(c => c.id === conversation.id);

        if (index >= 0) {
            conversations[index] = conversation;
        } else {
            conversations.unshift(conversation); // Add to beginning
        }

        this.saveConversations(conversations);
    }

    // Delete a conversation
    deleteConversation(id: string): void {
        const conversations = this.loadConversations();
        const filtered = conversations.filter(c => c.id !== id);
        this.saveConversations(filtered);
    }

    // Get a single conversation
    getConversation(id: string): Conversation | null {
        const conversations = this.loadConversations();
        return conversations.find(c => c.id === id) || null;
    }

    // Search conversations
    searchConversations(query: string): Conversation[] {
        const conversations = this.loadConversations();
        const lowerQuery = query.toLowerCase();

        return conversations.filter(conv =>
            conv.title.toLowerCase().includes(lowerQuery) ||
            conv.messages.some(msg => msg.content.toLowerCase().includes(lowerQuery))
        );
    }

    // Clean up conversations older than MAX_AGE_DAYS
    private cleanupOldConversations(conversations: Conversation[]): Conversation[] {
        const cutoffDate = new Date();
        cutoffDate.setDate(cutoffDate.getDate() - MAX_AGE_DAYS);

        return conversations.filter(conv => conv.updatedAt >= cutoffDate);
    }

    // Generate title from first message
    generateTitle(firstMessage: string): string {
        const maxLength = 40;
        if (firstMessage.length <= maxLength) {
            return firstMessage;
        }
        return firstMessage.substring(0, maxLength) + '...';
    }

    // Clear all conversations
    clearAll(): void {
        localStorage.removeItem(STORAGE_KEY);
    }
}

export const conversationStorage = new ConversationStorage();
