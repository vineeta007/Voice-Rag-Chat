import { test, expect, Page } from '@playwright/test';

type StreamDonePayload = {
    answer: string;
    language: string;
    sources: Array<Record<string, unknown>>;
};

async function mockApi(page: Page) {
    await page.route('**/api/health', async (route) => {
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ status: 'healthy' }),
        });
    });

    await page.route('**/api/languages', async (route) => {
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
                languages: [
                    { code: 'en', name: 'English' },
                    { code: 'hi', name: 'Hindi' },
                ],
            }),
        });
    });

    await page.route('**/api/elevenlabs-status', async (route) => {
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ success: false }),
        });
    });

    await page.route('**/api/session/clear', async (route) => {
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({ success: true }),
        });
    });

    await page.route('**/api/query-stream', async (route) => {
        const body = route.request().postDataJSON() as { question?: string; language?: string };
        const question = body.question?.trim() || 'unknown';
        const answer = `Answer for: ${question}`;

        const donePayload: StreamDonePayload = {
            answer,
            language: body.language || 'English',
            sources: [],
        };

        const sse = [
            `event: meta\ndata: ${JSON.stringify({ question, language: donePayload.language, sources: [] })}\n\n`,
            `event: delta\ndata: ${JSON.stringify({ text: answer })}\n\n`,
            `event: done\ndata: ${JSON.stringify(donePayload)}\n\n`,
        ].join('');

        await route.fulfill({
            status: 200,
            contentType: 'text/event-stream',
            headers: {
                'Cache-Control': 'no-cache',
                Connection: 'keep-alive',
            },
            body: sse,
        });
    });
}

async function sendTextQuestion(page: Page, question: string) {
    await page.getByPlaceholder('Ask me anything about the university...').fill(question);
    await page.locator('.premium-send-button').click();
    await expect(page.locator('.message-bubble.assistant .message-text').last()).toContainText(`Answer for: ${question}`);
}

test.describe('Chat memory integration', () => {
    test.beforeEach(async ({ page }) => {
        await mockApi(page);
        await page.goto('/');
        await expect(page.getByText('Connected')).toBeVisible();
    });

    test('new chat, switch chat, clear chat, and delete chat preserve isolation', async ({ page }) => {
        const q1 = 'Admissions for CSE';
        const q2 = 'Hostel fee details';

        // First conversation
        await sendTextQuestion(page, q1);
        await expect(page.locator('.conversation-title').first()).toContainText(q1);

        // New conversation and second message
        await page.getByRole('button', { name: '➕ New Chat' }).click();
        await expect(page.getByText('Welcome to Voice RAG!')).toBeVisible();
        await sendTextQuestion(page, q2);

        // Sidebar should contain both chats
        await expect(page.locator('.conversation-title')).toHaveCount(2);
        await expect(page.locator('.conversation-title').nth(0)).toContainText(q2);
        await expect(page.locator('.conversation-title').nth(1)).toContainText(q1);

        // Switch to old conversation and verify isolation
        await page.locator('.conversation-item').filter({ hasText: q1 }).click();
        await expect(page.locator('.message-text')).toContainText([q1, `Answer for: ${q1}`]);
        await expect(page.locator('.chat-messages')).not.toContainText(q2);

        // Switch to new conversation and verify isolation in reverse
        await page.locator('.conversation-item').filter({ hasText: q2 }).click();
        await expect(page.locator('.message-text')).toContainText([q2, `Answer for: ${q2}`]);
        await expect(page.locator('.chat-messages')).not.toContainText(q1);

        // Clear only active conversation (q2)
        await page.getByRole('button', { name: '🗑️ Clear Chat' }).click();
        await expect(page.getByText('Welcome to Voice RAG!')).toBeVisible();

        // Switch back to q1 conversation and ensure it is still intact
        await page.locator('.conversation-item').filter({ hasText: q1 }).click();
        await expect(page.locator('.message-text')).toContainText([q1, `Answer for: ${q1}`]);

        // Delete q1 conversation and ensure q2 remains
        page.on('dialog', async (dialog) => dialog.accept());
        const q1Item = page.locator('.conversation-item').filter({ hasText: q1 });
        await q1Item.hover();
        await q1Item.locator('.delete-btn').click();

        await expect(page.locator('.conversation-title')).toHaveCount(1);
        await expect(page.locator('.conversation-title').first()).toContainText(q2);
    });
});
