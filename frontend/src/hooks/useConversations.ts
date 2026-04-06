// Hook for managing conversations

import { useState, useEffect, useCallback } from 'react';
import { useRef } from 'react';
import { conversationStorage, Conversation, Message } from '../services/storage';

export function useConversations() {
    const [conversations, setConversations] = useState<Conversation[]>([]);
    const [activeConversationId, setActiveConversationId] = useState<string | null>(null);
    const [activeConversation, setActiveConversation] = useState<Conversation | null>(null);
    const activeConversationIdRef = useRef<string | null>(null);

    const sortByUpdatedAtDesc = (items: Conversation[]) => {
        return [...items].sort((a, b) => b.updatedAt.getTime() - a.updatedAt.getTime());
    };

    const generateConversationId = () => {
        if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
            return crypto.randomUUID();
        }
        return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
    };

    const upsertConversation = useCallback((
        conversationId: string,
        messages: Message[],
        language: string = 'English'
    ) => {
        setConversations(prev => {
            let updatedTarget = false;

            const updated = prev.map(conv => {
                if (conv.id === conversationId) {
                    updatedTarget = true;

                    let title = conv.title;
                    if (title === 'New Chat' && messages.length > 0) {
                        const firstUserMsg = messages.find(m => m.type === 'user');
                        if (firstUserMsg) {
                            title = conversationStorage.generateTitle(firstUserMsg.content);
                        }
                    }

                    return {
                        ...conv,
                        messages,
                        title,
                        language: conv.language || language,
                        updatedAt: new Date()
                    };
                }
                return conv;
            });

            if (!updatedTarget) {
                const firstUserMsg = messages.find(m => m.type === 'user');
                const title = firstUserMsg
                    ? conversationStorage.generateTitle(firstUserMsg.content)
                    : 'New Chat';

                updated.unshift({
                    id: conversationId,
                    title,
                    messages,
                    createdAt: new Date(),
                    updatedAt: new Date(),
                    language
                });
            }

            const sorted = sortByUpdatedAtDesc(updated);
            conversationStorage.saveConversations(sorted);
            return sorted;
        });
    }, []);

    // Load conversations on mount
    useEffect(() => {
        const loaded = conversationStorage.loadConversations();
        setConversations(loaded);

        // Set most recent as active if exists
        if (loaded.length > 0 && !activeConversationId) {
            setActiveConversationId(loaded[0].id);
            activeConversationIdRef.current = loaded[0].id;
            setActiveConversation(loaded[0]);
        }
    }, []);

    useEffect(() => {
        activeConversationIdRef.current = activeConversationId;
    }, [activeConversationId]);

    // Update active conversation when ID changes
    useEffect(() => {
        if (activeConversationId) {
            const conv = conversations.find(c => c.id === activeConversationId);
            setActiveConversation(conv || null);
        } else {
            setActiveConversation(null);
        }
    }, [activeConversationId, conversations]);

    // Create new conversation
    const createNewConversation = useCallback((language: string = 'English'): string => {
        const newConv: Conversation = {
            id: generateConversationId(),
            title: 'New Chat',
            messages: [],
            createdAt: new Date(),
            updatedAt: new Date(),
            language
        };

        conversationStorage.saveConversation(newConv);
        setConversations(prev => [newConv, ...prev]);
        setActiveConversationId(newConv.id);
        activeConversationIdRef.current = newConv.id;

        return newConv.id;
    }, []);

    // Switch to a different conversation
    const switchConversation = useCallback((id: string) => {
        setActiveConversationId(id);
        activeConversationIdRef.current = id;
        
        // Clear unread count when switching to conversation - Phase 2.5
        setConversations(prev => 
            prev.map(conv => 
                conv.id === id 
                    ? { ...conv, unreadCount: 0 }
                    : conv
            )
        );
    }, []);

    // Update current conversation with new messages
    const updateCurrentConversation = useCallback((messages: Message[]) => {
        let convId = activeConversationIdRef.current;

        if (!convId) {
            // Create new conversation if none is active yet
            convId = createNewConversation(messages[0]?.language || 'English');
            activeConversationIdRef.current = convId;
        }

        upsertConversation(convId, messages, messages[0]?.language || 'English');
    }, [createNewConversation, upsertConversation]);

    const updateConversationById = useCallback((
        conversationId: string,
        messages: Message[],
        language: string = 'English'
    ) => {
        upsertConversation(conversationId, messages, language);
    }, [upsertConversation]);

    // Delete a conversation
    const deleteConversation = useCallback((id: string) => {
        conversationStorage.deleteConversation(id);

        setConversations(prev => {
            const remaining = prev.filter(c => c.id !== id);

            // If deleted conversation was active, switch to another derived from latest state.
            if (id === activeConversationIdRef.current) {
                if (remaining.length > 0) {
                    setActiveConversationId(remaining[0].id);
                    activeConversationIdRef.current = remaining[0].id;
                } else {
                    setActiveConversationId(null);
                    activeConversationIdRef.current = null;
                }
            }

            return remaining;
        });
    }, []);

    // Search conversations
    const searchConversations = useCallback((query: string): Conversation[] => {
        if (!query.trim()) return conversations;
        return conversationStorage.searchConversations(query);
    }, [conversations]);

    // Clear all conversations
    const clearAllConversations = useCallback(() => {
        conversationStorage.clearAll();
        setConversations([]);
        setActiveConversationId(null);
        activeConversationIdRef.current = null;
        setActiveConversation(null);
    }, []);

    // Increment unread count for a conversation - Phase 2.5
    const incrementConversationUnreadCount = useCallback((conversationId: string) => {
        setConversations(prev =>
            prev.map(conv =>
                conv.id === conversationId && conv.id !== activeConversationIdRef.current
                    ? { ...conv, unreadCount: (conv.unreadCount || 0) + 1 }
                    : conv
            )
        );
    }, []);

    return {
        conversations,
        activeConversation,
        activeConversationId,
        createNewConversation,
        switchConversation,
        updateCurrentConversation,
        updateConversationById,
        deleteConversation,
        searchConversations,
        clearAllConversations,
        incrementConversationUnreadCount
    };
}
