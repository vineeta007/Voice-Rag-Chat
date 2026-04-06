const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  await page.goto('http://localhost:5173', { waitUntil: 'networkidle' });
  await page.evaluate(() => localStorage.clear());
  await page.reload({ waitUntil: 'networkidle' });

  const cardText = await page.locator('.example-question .text').first().innerText();

  const quickQuestion = page.locator('.example-question').first();
  await quickQuestion.click();
  await page.waitForTimeout(2500);

  // Verify assistant reply is present in active chat before switching
  const beforeSwitch = await page.locator('.chat-container').innerText();
  const hadAssistantBefore = beforeSwitch.includes('I can help') || beforeSwitch.includes('Please specify') || beforeSwitch.includes('AI Assistant');

  await page.locator('button.new-chat-btn').click();
  await page.waitForTimeout(400);
  await page
    .locator('.conversation-item')
    .filter({ hasNotText: 'New Chat' })
    .first()
    .click();
  await page.waitForTimeout(600);

  const afterSwitch = await page.locator('.chat-container').innerText();
  const hasUser = afterSwitch.includes('What are the admission requirements for B.Tech CSE?');
  const hasAssistant = afterSwitch.includes('I can help') || afterSwitch.includes('Please specify') || afterSwitch.includes('AI Assistant');

  console.log('CARD_TEXT:', cardText);
  console.log('HAD_ASSISTANT_BEFORE_SWITCH:', hadAssistantBefore);
  console.log('HAS_USER_AFTER_SWITCH:', hasUser);
  console.log('HAS_ASSISTANT_AFTER_SWITCH:', hasAssistant);

  const ok = cardText.includes('B.Tech CSE') && hasUser && hasAssistant;
  console.log('RESULT:', ok ? 'PASS' : 'FAIL');

  await browser.close();
  process.exit(ok ? 0 : 2);
})().catch((err) => {
  console.error('PLAYWRIGHT_ERROR:', err?.message || err);
  process.exit(1);
});
