/**
 * E2E Tests for Chat Flow
 *
 * Tests complete user journey:
 * 1. Load application
 * 2. Send message
 * 3. Receive streaming response
 * 4. Continue conversation
 * 5. Handle errors
 */

import { test, expect, Page } from '@playwright/test';

test.describe('Chat Flow', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
  });

  test('should load chat interface', async ({ page }) => {
    // Verify main elements are visible
    await expect(page.locator('[data-testid="chat-container"]')).toBeVisible();
    await expect(page.locator('[data-testid="message-input"]')).toBeVisible();
    await expect(page.locator('[data-testid="send-button"]')).toBeVisible();

    // Verify initial state
    await expect(page.locator('[data-testid="empty-state"]')).toBeVisible();
  });

  test('should send message and receive streaming response', async ({ page }) => {
    // Type message
    const input = page.locator('[data-testid="message-input"]');
    await input.fill('What is machine learning?');

    // Send message
    await page.locator('[data-testid="send-button"]').click();

    // Verify user message appears
    await expect(page.locator('[data-testid="message-user"]').last()).toContainText(
      'What is machine learning?'
    );

    // Wait for streaming indicator
    await expect(page.locator('[data-testid="streaming-indicator"]')).toBeVisible({
      timeout: 5000
    });

    // Wait for assistant response to appear
    await expect(page.locator('[data-testid="message-assistant"]').last()).toBeVisible({
      timeout: 30000
    });

    // Verify streaming indicator disappears
    await expect(page.locator('[data-testid="streaming-indicator"]')).not.toBeVisible({
      timeout: 30000
    });

    // Verify response contains relevant content
    const response = await page.locator('[data-testid="message-assistant"]').last().textContent();
    expect(response).toBeTruthy();
    expect(response!.length).toBeGreaterThan(20);
  });

  test('should handle multiple messages in conversation', async ({ page }) => {
    const messages = [
      'What is AI?',
      'How does it work?',
      'What are some applications?'
    ];

    for (const message of messages) {
      await page.locator('[data-testid="message-input"]').fill(message);
      await page.locator('[data-testid="send-button"]').click();

      // Wait for response
      await page.waitForSelector('[data-testid="streaming-indicator"]', {
        state: 'visible',
        timeout: 5000
      });
      await page.waitForSelector('[data-testid="streaming-indicator"]', {
        state: 'hidden',
        timeout: 30000
      });
    }

    // Verify all messages are displayed
    const userMessages = await page.locator('[data-testid="message-user"]').count();
    const assistantMessages = await page.locator('[data-testid="message-assistant"]').count();

    expect(userMessages).toBe(3);
    expect(assistantMessages).toBe(3);
  });

  test('should clear conversation', async ({ page }) => {
    // Send a message
    await page.locator('[data-testid="message-input"]').fill('Hello');
    await page.locator('[data-testid="send-button"]').click();

    // Wait for response
    await page.waitForSelector('[data-testid="message-assistant"]', {
      timeout: 30000
    });

    // Clear conversation
    await page.locator('[data-testid="clear-button"]').click();

    // Confirm clear action
    await page.locator('[data-testid="confirm-clear"]').click();

    // Verify messages are cleared
    await expect(page.locator('[data-testid="empty-state"]')).toBeVisible();
    await expect(page.locator('[data-testid="message-user"]')).not.toBeVisible();
  });

  test('should handle send on Enter key', async ({ page }) => {
    const input = page.locator('[data-testid="message-input"]');

    await input.fill('Test message');
    await input.press('Enter');

    // Verify message was sent
    await expect(page.locator('[data-testid="message-user"]').last()).toContainText(
      'Test message'
    );
  });

  test('should prevent sending empty messages', async ({ page }) => {
    const sendButton = page.locator('[data-testid="send-button"]');

    // Verify send button is disabled when input is empty
    await expect(sendButton).toBeDisabled();

    // Type message
    await page.locator('[data-testid="message-input"]').fill('Test');
    await expect(sendButton).toBeEnabled();

    // Clear input
    await page.locator('[data-testid="message-input"]').clear();
    await expect(sendButton).toBeDisabled();
  });

  test('should display error on connection failure', async ({ page }) => {
    // Intercept API request and return error
    await page.route('**/api/chat/stream', (route) => {
      route.abort('failed');
    });

    // Try to send message
    await page.locator('[data-testid="message-input"]').fill('Test message');
    await page.locator('[data-testid="send-button"]').click();

    // Verify error message is displayed
    await expect(page.locator('[data-testid="error-message"]')).toBeVisible({
      timeout: 10000
    });

    await expect(page.locator('[data-testid="error-message"]')).toContainText(
      /connection|error|failed/i
    );
  });

  test('should allow retry after error', async ({ page }) => {
    let requestCount = 0;

    // Fail first request, succeed on retry
    await page.route('**/api/chat/stream', (route) => {
      requestCount++;
      if (requestCount === 1) {
        route.abort('failed');
      } else {
        route.continue();
      }
    });

    // First attempt - should fail
    await page.locator('[data-testid="message-input"]').fill('Test message');
    await page.locator('[data-testid="send-button"]').click();

    await expect(page.locator('[data-testid="error-message"]')).toBeVisible();

    // Retry
    await page.locator('[data-testid="retry-button"]').click();

    // Should succeed
    await expect(page.locator('[data-testid="message-assistant"]')).toBeVisible({
      timeout: 30000
    });
  });

  test('should auto-scroll to latest message', async ({ page }) => {
    // Send multiple messages to create scroll
    for (let i = 0; i < 5; i++) {
      await page.locator('[data-testid="message-input"]').fill(`Message ${i + 1}`);
      await page.locator('[data-testid="send-button"]').click();

      await page.waitForSelector('[data-testid="streaming-indicator"]', {
        state: 'hidden',
        timeout: 30000
      });
    }

    // Verify scroll position is at bottom
    const chatContainer = page.locator('[data-testid="chat-messages"]');
    const isScrolledToBottom = await chatContainer.evaluate((el) => {
      return Math.abs(el.scrollHeight - el.scrollTop - el.clientHeight) < 10;
    });

    expect(isScrolledToBottom).toBeTruthy();
  });

  test('should show model selection', async ({ page }) => {
    // Open model selector
    await page.locator('[data-testid="model-selector"]').click();

    // Verify model options are visible
    await expect(page.locator('[data-testid="model-option-anthropic"]')).toBeVisible();
    await expect(page.locator('[data-testid="model-option-openrouter"]')).toBeVisible();
  });

  test('should switch between models', async ({ page }) => {
    // Select model
    await page.locator('[data-testid="model-selector"]').click();
    await page.locator('[data-testid="model-option-openrouter"]').click();

    // Send message with selected model
    await page.locator('[data-testid="message-input"]').fill('Test with OpenRouter');
    await page.locator('[data-testid="send-button"]').click();

    // Verify request uses correct model
    const request = await page.waitForRequest(
      (req) => req.url().includes('/api/chat/stream')
    );

    const requestBody = request.postDataJSON();
    expect(requestBody.provider).toBe('openrouter');
  });

  test('should maintain conversation state on page reload', async ({ page }) => {
    // Send message
    await page.locator('[data-testid="message-input"]').fill('Remember this');
    await page.locator('[data-testid="send-button"]').click();

    await page.waitForSelector('[data-testid="message-assistant"]', {
      timeout: 30000
    });

    // Reload page
    await page.reload();
    await page.waitForLoadState('networkidle');

    // Verify conversation is restored (if persistence is implemented)
    // This test may need adjustment based on persistence strategy
    const messageCount = await page.locator('[data-testid^="message-"]').count();
    expect(messageCount).toBeGreaterThan(0);
  });
});

test.describe('Mobile Chat Flow', () => {
  test.use({ viewport: { width: 375, height: 667 } });

  test('should work on mobile viewport', async ({ page }) => {
    await page.goto('/');

    // Verify responsive layout
    await expect(page.locator('[data-testid="chat-container"]')).toBeVisible();

    // Send message on mobile
    await page.locator('[data-testid="message-input"]').fill('Mobile test');
    await page.locator('[data-testid="send-button"]').click();

    await expect(page.locator('[data-testid="message-user"]')).toBeVisible();
  });
});
