import axios from 'axios';

// Use environment variable for API URL, fallback to localhost
// Remove trailing slash if present to avoid double slashes
const getApiUrl = () => {
    let url = import.meta.env.VITE_API_URL;

    if (!url) {
        console.error("❌ VITE_API_URL is NOT defined");
    }

    if (url.endsWith('/')) {
        url = url.slice(0, -1);
    }

    console.log('🔗 API Base URL:', url);
    return url;
};
export const API_BASE_URL = getApiUrl();

export interface TextQueryRequest {
    question: string;
    language?: string;
    session_id?: string;
    client_conversation_id?: string;
}

export interface QueryResponse {
    question: string;
    answer: string;
    language: string;
    trust_score?: number;
    evidence?: Array<{
        rank: number;
        score: number;
        raw_score: number;
        snippet: string;
        metadata: Record<string, any>;
    }>;
    sources: Array<{
        content: string;
        metadata: Record<string, any>;
        distance: number;
    }>;
}

export interface VoiceQueryResponse {
    original_text: string;
    english_text: string;
    detected_language: string;
    answer: string;
    trust_score?: number;
    evidence?: Array<{
        rank: number;
        score: number;
        raw_score: number;
        snippet: string;
        metadata: Record<string, any>;
    }>;
    sources: Array<{
        content: string;
        metadata: Record<string, any>;
        distance: number;
    }>;
}

export interface Language {
    code: string;
    name: string;
}

export interface StreamQueryHandlers {
    onMeta?: (payload: any) => void;
    onDelta?: (text: string) => void;
    onSentence?: (text: string) => void;
    onDone?: (payload: QueryResponse) => void;
    onError?: (message: string) => void;
}

export interface StreamQueryOptions {
    signal?: AbortSignal;
    timeoutMs?: number;
    inactivityTimeoutMs?: number;
}

const REQUEST_TIMEOUT_MS = Number(import.meta.env.VITE_API_TIMEOUT_MS || 90000);
const RETRY_DELAY_MS = 2500;
const STREAM_INACTIVITY_TIMEOUT_MS = Number(import.meta.env.VITE_STREAM_INACTIVITY_TIMEOUT_MS || 45000);

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

const isRetryableError = (error: any): boolean => {
    const status = error?.response?.status;
    const code = error?.code;
    return status === 502 || status === 503 || status === 504 || code === 'ECONNABORTED' || code === 'ERR_NETWORK';
};

const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
    timeout: REQUEST_TIMEOUT_MS
});
// Add response interceptor for better error diagnosis
api.interceptors.response.use(
    response => response,
    error => {
        console.error('❌ API Error:', {
            url: error.config?.url,
            status: error.response?.status,
            message: error.message
        });
        return Promise.reject(error);
    }
);

export const apiService = {
    async textQuery(
        question: string,
        language: string = 'English',
        clientConversationId?: string
    ): Promise<QueryResponse> {
        try {
            const response = await api.post<QueryResponse>('/api/query', {
                question,
                language,
                client_conversation_id: clientConversationId,
            });
            return response.data;
        } catch (error: any) {
            if (!isRetryableError(error)) {
                throw error;
            }

            // One retry helps during Render cold-start or transient gateway restarts.
            await sleep(RETRY_DELAY_MS);
            const retryResponse = await api.post<QueryResponse>('/api/query', {
                question,
                language,
                client_conversation_id: clientConversationId,
            });
            return retryResponse.data;
        }
    },

    async voiceQuery(
        audioBlob: Blob,
        language: string = 'auto',
        clientConversationId?: string
    ): Promise<VoiceQueryResponse> {
        const formData = new FormData();
        formData.append('audio', audioBlob, 'recording.wav');
        formData.append('language', language);
        if (clientConversationId) {
            formData.append('client_conversation_id', clientConversationId);
        }

        try {
            const response = await axios.post<VoiceQueryResponse>(
    `${API_BASE_URL}/api/voice-query`,
    formData,
    {
        headers: {
            'Content-Type': 'multipart/form-data',
        },
        timeout: REQUEST_TIMEOUT_MS
    }
);
            return response.data;
        } catch (error: any) {
            if (!isRetryableError(error)) {
                throw error;
            }

            await sleep(RETRY_DELAY_MS);
            const retryResponse = await axios.post<VoiceQueryResponse>(
                `${API_BASE_URL}/api/voice-query`,
                formData,
                {
                    headers: {
                        'Content-Type': 'multipart/form-data',
                    },
                    timeout: REQUEST_TIMEOUT_MS,
                    withCredentials: true,
                }
            );
            return retryResponse.data;
        }
    },

    async getSupportedLanguages(): Promise<Language[]> {
        const response = await api.get<{ languages: Language[] }>('/api/languages');
        return response.data.languages;
    },

    async healthCheck(): Promise<{ status: string }> {
        const response = await api.get<{ status: string }>('/api/health');
        return response.data;
    },

    async clearSessionMemory(clientConversationId: string): Promise<void> {
        try {
            await api.post('/api/session/clear', { client_conversation_id: clientConversationId });
        } catch (error) {
            // Best-effort cleanup; UI should not fail if this endpoint is unavailable.
            console.warn('Failed to clear backend session memory:', error);
        }
    },

    async textQueryStream(
        question: string,
        language: string = 'English',
        clientConversationId?: string,
        handlers?: StreamQueryHandlers,
        options?: StreamQueryOptions
    ): Promise<QueryResponse> {
        const start = performance.now();
        console.log('🌊 Stream start', { questionPreview: question.slice(0, 40), language });

        const controller = new AbortController();
        const timeoutMs = options?.timeoutMs ?? REQUEST_TIMEOUT_MS;
        const inactivityTimeoutMs = options?.inactivityTimeoutMs ?? STREAM_INACTIVITY_TIMEOUT_MS;

        const onExternalAbort = () => controller.abort();
        options?.signal?.addEventListener('abort', onExternalAbort);

        const requestTimeoutId = setTimeout(() => controller.abort(), timeoutMs);
        let inactivityTimeoutId: number | null = null;

        const resetInactivityTimeout = () => {
            if (inactivityTimeoutId !== null) {
                clearTimeout(inactivityTimeoutId);
            }
            inactivityTimeoutId = window.setTimeout(() => controller.abort(), inactivityTimeoutMs);
        };

        let finalResult: QueryResponse | null = null;

        const dispatchEvent = (eventType: string, dataString: string) => {
            let payload: any = {};
            try {
                payload = dataString ? JSON.parse(dataString) : {};
            } catch {
                payload = { text: dataString };
            }

            switch (eventType) {
                case 'meta':
                    handlers?.onMeta?.(payload);
                    break;
                case 'delta':
                    handlers?.onDelta?.(payload.text || '');
                    break;
                case 'sentence':
                    handlers?.onSentence?.(payload.text || '');
                    break;
                case 'done':
                    finalResult = {
                        question,
                        answer: payload.answer || '',
                        language: payload.language || language,
                        trust_score: payload.trust_score,
                        evidence: payload.evidence || [],
                        sources: payload.sources || [],
                    };
                    handlers?.onDone?.(finalResult);
                    break;
                case 'error':
                    handlers?.onError?.(payload.message || 'Streaming error');
                    break;
                default:
                    break;
            }
        };

        try {
            const response = await fetch(`${API_BASE_URL}/api/query-stream`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ question, language, client_conversation_id: clientConversationId }),
                signal: controller.signal,
            });

            if (!response.ok || !response.body) {
                throw new Error(`Streaming request failed: ${response.status}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            resetInactivityTimeout();

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                resetInactivityTimeout();

                buffer += decoder.decode(value, { stream: true });
                const events = buffer.split('\n\n');
                buffer = events.pop() || '';

                for (const eventBlock of events) {
                    if (!eventBlock.trim()) continue;

                    const lines = eventBlock.split('\n');
                    let eventType = 'message';
                    const dataLines: string[] = [];

                    for (const line of lines) {
                        if (line.startsWith('event:')) {
                            eventType = line.slice(6).trim();
                        } else if (line.startsWith('data:')) {
                            dataLines.push(line.slice(5).trim());
                        }
                    }

                    dispatchEvent(eventType, dataLines.join('\n'));
                }
            }

            if (finalResult) {
                console.log('🌊 Stream done', { durationMs: Math.round(performance.now() - start) });
                return finalResult;
            }

            throw new Error('Streaming completed without final result');
        } catch (error: any) {
            const aborted = controller.signal.aborted || error?.name === 'AbortError';
            const message = aborted ? 'Streaming request cancelled or timed out' : (error?.message || 'Streaming error');
            handlers?.onError?.(message);
            console.error('❌ Stream failure', { message });
            throw error;
        } finally {
            clearTimeout(requestTimeoutId);
            if (inactivityTimeoutId !== null) {
                clearTimeout(inactivityTimeoutId);
            }
            options?.signal?.removeEventListener('abort', onExternalAbort);
        }
    },
};
