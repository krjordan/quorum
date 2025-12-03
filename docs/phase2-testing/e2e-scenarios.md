# Phase 2 E2E Test Scenarios - Multi-LLM Debate Engine

**Date:** 2025-12-02
**Agent:** Test Engineer
**Phase:** Phase 2 - Multi-LLM Debate Engine

---

## Overview

End-to-end tests validate complete user workflows using Playwright to simulate real browser interactions. These tests verify the entire stack from UI interactions through backend processing to visual feedback.

**Test Environment:** Playwright with real backend (mocked LLM APIs)

---

## 1. Test Structure

```
tests/e2e/phase2/
├── playwright.config.ts               # Playwright configuration
├── fixtures/
│   └── debate-fixtures.ts             # Reusable test data
├── scenarios/
│   ├── simple-debate.spec.ts          # Scenario 1: Simple 2-debater
│   ├── multi-debater.spec.ts          # Scenario 2: 4-debater structured
│   ├── cost-warning.spec.ts           # Scenario 3: Cost warnings
│   ├── stream-failure.spec.ts         # Scenario 4: Stream reconnection
│   ├── judge-intervention.spec.ts     # Scenario 5: Judge stops debate
│   └── export.spec.ts                 # Scenario 6: Export functionality
└── helpers/
    └── debate-helpers.ts              # Common helper functions
```

---

## 2. Playwright Configuration

**File:** `tests/e2e/phase2/playwright.config.ts`

```typescript
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e/phase2',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['html', { outputFolder: 'tests/coverage/e2e/phase2' }],
    ['json', { outputFile: 'tests/coverage/e2e/phase2/results.json' }]
  ],

  use: {
    baseURL: 'http://localhost:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
    {
      name: 'mobile-chrome',
      use: { ...devices['Pixel 5'] },
    },
  ],

  // Start dev server before tests
  webServer: [
    {
      command: 'npm run dev',
      url: 'http://localhost:5173',
      reuseExistingServer: !process.env.CI,
    },
    {
      command: 'cd backend && uvicorn app.main:app --port 8000',
      url: 'http://localhost:8000/health',
      reuseExistingServer: !process.env.CI,
    }
  ],
});
```

---

## 3. Scenario 1: Simple 2-Debater Free-Form Debate

**File:** `tests/e2e/phase2/scenarios/simple-debate.spec.ts`

### User Story
> As a user, I want to start a simple debate between two AI models and watch them discuss a topic in real-time.

```typescript
import { test, expect } from '@playwright/test';

test.describe('Simple 2-Debater Debate', () => {
  test('should complete a basic debate workflow', async ({ page }) => {
    // Step 1: Navigate to debate page
    await page.goto('/debates/new');
    await expect(page).toHaveTitle(/Quorum/);

    // Step 2: Configure debate
    await page.fill('[data-testid="debate-topic"]', 'Is AI beneficial?');

    // Add first participant
    await page.click('[data-testid="add-participant"]');
    await page.selectOption(
      '[data-testid="participant-1-model"]',
      'claude-3-5-sonnet-20241022'
    );
    await page.fill(
      '[data-testid="participant-1-persona"]',
      'Optimistic AI Researcher'
    );

    // Add second participant
    await page.click('[data-testid="add-participant"]');
    await page.selectOption(
      '[data-testid="participant-2-model"]',
      'gpt-4'
    );
    await page.fill(
      '[data-testid="participant-2-persona"]',
      'Cautious Ethicist'
    );

    // Select judge
    await page.selectOption(
      '[data-testid="judge-model"]',
      'claude-3-opus-20240229'
    );

    // Select format
    await page.selectOption('[data-testid="debate-format"]', 'free-form');

    // Step 3: Start debate
    await page.click('[data-testid="start-debate"]');

    // Verify debate started
    await expect(page.locator('[data-testid="debate-status"]'))
      .toHaveText('Running', { timeout: 5000 });

    // Step 4: Watch streaming responses
    // Wait for first participant to start responding
    await expect(page.locator('[data-testid="participant-1-response"]'))
      .not.toBeEmpty({ timeout: 10000 });

    // Verify streaming animation is active
    await expect(page.locator('[data-testid="participant-1-streaming-indicator"]'))
      .toBeVisible();

    // Wait for second participant to start responding
    await expect(page.locator('[data-testid="participant-2-response"]'))
      .not.toBeEmpty({ timeout: 10000 });

    // Step 5: Wait for round completion
    await expect(page.locator('[data-testid="round-complete-indicator"]'))
      .toBeVisible({ timeout: 30000 });

    // Step 6: Verify judge assessment appears
    await expect(page.locator('[data-testid="judge-assessment"]'))
      .toBeVisible({ timeout: 10000 });

    const assessment = await page.locator('[data-testid="judge-assessment"]').textContent();
    expect(assessment).toContain('Score');
    expect(assessment).toContain('Summary');

    // Step 7: Wait for debate completion
    await expect(page.locator('[data-testid="debate-status"]'))
      .toHaveText(/Completed/, { timeout: 60000 });

    // Step 8: Verify final verdict
    await expect(page.locator('[data-testid="final-verdict"]'))
      .toBeVisible();

    const verdict = await page.locator('[data-testid="final-verdict"]').textContent();
    expect(verdict).not.toBeEmpty();

    // Step 9: Verify costs are displayed
    const totalCost = await page.locator('[data-testid="total-cost"]').textContent();
    expect(totalCost).toMatch(/\$\d+\.\d{2}/);
  });

  test('should allow pausing and resuming debate', async ({ page }) => {
    await page.goto('/debates/new');

    // Configure and start debate (same as above)
    // ...

    // Wait for debate to start
    await expect(page.locator('[data-testid="debate-status"]'))
      .toHaveText('Running', { timeout: 5000 });

    // Pause debate
    await page.click('[data-testid="pause-debate"]');

    // Verify paused state
    await expect(page.locator('[data-testid="debate-status"]'))
      .toHaveText('Paused');

    // Verify streaming stopped
    await expect(page.locator('[data-testid="participant-1-streaming-indicator"]'))
      .not.toBeVisible();

    // Resume debate
    await page.click('[data-testid="resume-debate"]');

    // Verify resumed
    await expect(page.locator('[data-testid="debate-status"]'))
      .toHaveText('Running');

    // Verify streaming restarted
    await expect(page.locator('[data-testid="participant-1-streaming-indicator"]'))
      .toBeVisible();
  });

  test('should display round progression', async ({ page }) => {
    await page.goto('/debates/new');

    // Configure debate with round limit
    await page.fill('[data-testid="debate-topic"]', 'Test topic');
    // ... configure participants ...
    await page.selectOption('[data-testid="debate-format"]', 'round-limited');
    await page.fill('[data-testid="round-limit"]', '3');

    await page.click('[data-testid="start-debate"]');

    // Verify round counter
    await expect(page.locator('[data-testid="current-round"]'))
      .toHaveText('1');

    // Wait for round 1 to complete
    await expect(page.locator('[data-testid="round-complete-indicator"]'))
      .toBeVisible({ timeout: 30000 });

    // Verify round 2 starts
    await expect(page.locator('[data-testid="current-round"]'))
      .toHaveText('2', { timeout: 5000 });

    // Verify progress bar
    const progressBar = page.locator('[data-testid="debate-progress"]');
    const progress = await progressBar.getAttribute('aria-valuenow');
    expect(parseInt(progress!)).toBeGreaterThan(30);  // At least 1/3 complete
  });
});
```

---

## 4. Scenario 2: 4-Debater Structured Debate

**File:** `tests/e2e/phase2/scenarios/multi-debater.spec.ts`

### User Story
> As a user, I want to see four AI models debate with structured phases (opening, middle, closing).

```typescript
import { test, expect } from '@playwright/test';

test.describe('4-Debater Structured Debate', () => {
  test('should manage 4 simultaneous debaters', async ({ page }) => {
    await page.goto('/debates/new');

    // Configure 4 participants
    await page.fill('[data-testid="debate-topic"]', 'Best programming language');

    for (let i = 1; i <= 4; i++) {
      await page.click('[data-testid="add-participant"]');
      await page.selectOption(
        `[data-testid="participant-${i}-model"]`,
        i % 2 === 0 ? 'claude-3-5-sonnet-20241022' : 'gpt-4'
      );
      await page.fill(
        `[data-testid="participant-${i}-persona"]`,
        `Advocate ${i}`
      );
    }

    // Configure structured rounds
    await page.selectOption('[data-testid="debate-format"]', 'structured-rounds');

    await page.click('[data-testid="start-debate"]');

    // Verify all 4 participant cards are visible
    for (let i = 1; i <= 4; i++) {
      await expect(page.locator(`[data-testid="participant-${i}-card"]`))
        .toBeVisible();
    }

    // Verify all are streaming simultaneously
    await expect(page.locator('[data-testid="participant-1-streaming-indicator"]'))
      .toBeVisible({ timeout: 10000 });

    // Check that all 4 start within a short timeframe (simultaneous mode)
    const streamingIndicators = page.locator('[data-testid*="streaming-indicator"]');
    const count = await streamingIndicators.count();
    expect(count).toBe(4);

    // Wait for round completion
    await expect(page.locator('[data-testid="round-complete-indicator"]'))
      .toBeVisible({ timeout: 60000 });

    // Verify all 4 responses are complete
    for (let i = 1; i <= 4; i++) {
      const response = await page.locator(
        `[data-testid="participant-${i}-response"]`
      ).textContent();
      expect(response).not.toBeEmpty();
    }
  });

  test('should show structured round phases', async ({ page }) => {
    await page.goto('/debates/new');

    // Configure structured debate
    // ...

    await page.click('[data-testid="start-debate"]');

    // Verify opening phase
    await expect(page.locator('[data-testid="current-phase"]'))
      .toHaveText('Opening Statements');

    // Wait for round 1 completion
    await expect(page.locator('[data-testid="round-complete-indicator"]'))
      .toBeVisible({ timeout: 60000 });

    // Verify middle phase
    await expect(page.locator('[data-testid="current-phase"]'))
      .toHaveText('Discussion', { timeout: 5000 });

    // Wait for round 2 completion
    await expect(page.locator('[data-testid="round-complete-indicator"]'))
      .toBeVisible({ timeout: 60000 });

    // Verify closing phase
    await expect(page.locator('[data-testid="current-phase"]'))
      .toHaveText('Closing Arguments', { timeout: 5000 });
  });

  test('should handle layout with 4 participants', async ({ page }) => {
    await page.goto('/debates/new');

    // Configure 4 participants
    // ...

    await page.click('[data-testid="start-debate"]');

    // Verify responsive grid layout
    const participantCards = page.locator('[data-testid*="participant"][data-testid$="card"]');
    const count = await participantCards.count();
    expect(count).toBe(4);

    // Check that cards are arranged in 2x2 grid
    const firstCard = participantCards.nth(0);
    const secondCard = participantCards.nth(1);

    const firstBox = await firstCard.boundingBox();
    const secondBox = await secondCard.boundingBox();

    // Should be side by side (within 50px vertically)
    expect(Math.abs(firstBox!.y - secondBox!.y)).toBeLessThan(50);
  });
});
```

---

## 5. Scenario 3: Cost Warning and Override

**File:** `tests/e2e/phase2/scenarios/cost-warning.spec.ts`

### User Story
> As a user, I want to be warned when debate costs are high and have the option to continue or stop.

```typescript
import { test, expect } from '@playwright/test';

test.describe('Cost Warning System', () => {
  test('should display cost warning when threshold exceeded', async ({ page }) => {
    await page.goto('/debates/new');

    // Configure debate with low cost threshold
    await page.fill('[data-testid="debate-topic"]', 'Test topic');
    // ... configure participants ...

    // Set low cost warning threshold
    await page.fill('[data-testid="cost-threshold"]', '0.10');

    await page.click('[data-testid="start-debate"]');

    // Wait for debate to progress
    await expect(page.locator('[data-testid="debate-status"]'))
      .toHaveText('Running');

    // Monitor for cost warning
    await expect(page.locator('[data-testid="cost-warning-dialog"]'))
      .toBeVisible({ timeout: 30000 });

    // Verify warning content
    const warningText = await page.locator('[data-testid="cost-warning-message"]')
      .textContent();
    expect(warningText).toContain('Cost threshold exceeded');
    expect(warningText).toMatch(/\$\d+\.\d{2}/);

    // Verify action buttons are present
    await expect(page.locator('[data-testid="continue-debate"]'))
      .toBeVisible();
    await expect(page.locator('[data-testid="stop-debate"]'))
      .toBeVisible();
  });

  test('should continue debate when user overrides warning', async ({ page }) => {
    await page.goto('/debates/new');

    // Configure debate with low threshold
    // ...

    await page.click('[data-testid="start-debate"]');

    // Wait for cost warning
    await expect(page.locator('[data-testid="cost-warning-dialog"]'))
      .toBeVisible({ timeout: 30000 });

    // Click continue
    await page.click('[data-testid="continue-debate"]');

    // Verify warning dismissed
    await expect(page.locator('[data-testid="cost-warning-dialog"]'))
      .not.toBeVisible();

    // Verify debate continues
    await expect(page.locator('[data-testid="debate-status"]'))
      .toHaveText('Running');

    // Verify streaming continues
    await expect(page.locator('[data-testid*="streaming-indicator"]').first())
      .toBeVisible();
  });

  test('should stop debate when user declines to continue', async ({ page }) => {
    await page.goto('/debates/new');

    // Configure debate
    // ...

    await page.click('[data-testid="start-debate"]');

    // Wait for cost warning
    await expect(page.locator('[data-testid="cost-warning-dialog"]'))
      .toBeVisible({ timeout: 30000 });

    // Click stop
    await page.click('[data-testid="stop-debate"]');

    // Verify debate stopped
    await expect(page.locator('[data-testid="debate-status"]'))
      .toHaveText(/Stopped|Completed/, { timeout: 5000 });

    // Verify no streaming indicators
    const streamingIndicators = page.locator('[data-testid*="streaming-indicator"]');
    expect(await streamingIndicators.count()).toBe(0);
  });

  test('should show real-time cost updates', async ({ page }) => {
    await page.goto('/debates/new');

    // Configure debate
    // ...

    await page.click('[data-testid="start-debate"]');

    // Get initial cost
    const initialCost = await page.locator('[data-testid="total-cost"]')
      .textContent();

    // Wait for streaming to progress
    await page.waitForTimeout(5000);

    // Get updated cost
    const updatedCost = await page.locator('[data-testid="total-cost"]')
      .textContent();

    // Cost should have increased
    expect(updatedCost).not.toBe(initialCost);

    // Parse and compare numeric values
    const initialValue = parseFloat(initialCost!.replace('$', ''));
    const updatedValue = parseFloat(updatedCost!.replace('$', ''));
    expect(updatedValue).toBeGreaterThan(initialValue);
  });
});
```

---

## 6. Scenario 4: Stream Failure and Reconnection

**File:** `tests/e2e/phase2/scenarios/stream-failure.spec.ts`

### User Story
> As a user, I want the debate to recover gracefully if a streaming connection fails.

```typescript
import { test, expect } from '@playwright/test';

test.describe('Stream Failure Recovery', () => {
  test('should reconnect after stream disconnection', async ({ page, context }) => {
    await page.goto('/debates/new');

    // Configure and start debate
    // ...

    await page.click('[data-testid="start-debate"]');

    // Wait for streaming to start
    await expect(page.locator('[data-testid="participant-1-streaming-indicator"]'))
      .toBeVisible({ timeout: 10000 });

    // Simulate network disruption
    await context.setOffline(true);
    await page.waitForTimeout(2000);

    // Verify error state shown
    await expect(page.locator('[data-testid="connection-error"]'))
      .toBeVisible({ timeout: 5000 });

    // Restore network
    await context.setOffline(false);

    // Verify automatic reconnection
    await expect(page.locator('[data-testid="reconnecting-indicator"]'))
      .toBeVisible();

    await expect(page.locator('[data-testid="connection-error"]'))
      .not.toBeVisible({ timeout: 10000 });

    // Verify streaming resumes
    await expect(page.locator('[data-testid="participant-1-streaming-indicator"]'))
      .toBeVisible({ timeout: 10000 });

    // Verify debate completes successfully
    await expect(page.locator('[data-testid="debate-status"]'))
      .toHaveText(/Completed/, { timeout: 60000 });
  });

  test('should show retry button on persistent failure', async ({ page, context }) => {
    await page.goto('/debates/new');

    // Configure and start debate
    // ...

    await page.click('[data-testid="start-debate"]');

    // Wait for streaming
    await expect(page.locator('[data-testid="debate-status"]'))
      .toHaveText('Running');

    // Simulate persistent network failure
    await context.setOffline(true);

    // Wait for multiple reconnection attempts to fail
    await page.waitForTimeout(15000);

    // Verify retry button appears
    await expect(page.locator('[data-testid="retry-connection"]'))
      .toBeVisible();

    // Click retry
    await context.setOffline(false);
    await page.click('[data-testid="retry-connection"]');

    // Verify successful reconnection
    await expect(page.locator('[data-testid="connection-error"]'))
      .not.toBeVisible({ timeout: 10000 });
  });

  test('should handle individual participant stream failure', async ({ page }) => {
    // Mock backend to fail one participant's stream
    await page.route('**/api/debates/*/stream/participant-2', route => {
      route.abort('failed');
    });

    await page.goto('/debates/new');

    // Configure debate with 3 participants
    // ...

    await page.click('[data-testid="start-debate"]');

    // Wait for streaming to start
    await page.waitForTimeout(5000);

    // Verify participant 2 shows error
    await expect(page.locator('[data-testid="participant-2-error"]'))
      .toBeVisible();

    // Verify other participants continue normally
    await expect(page.locator('[data-testid="participant-1-streaming-indicator"]'))
      .toBeVisible();
    await expect(page.locator('[data-testid="participant-3-streaming-indicator"]'))
      .toBeVisible();

    // Verify debate continues
    await expect(page.locator('[data-testid="debate-status"]'))
      .toHaveText('Running');
  });
});
```

---

## 7. Scenario 5: Judge Intervention

**File:** `tests/e2e/phase2/scenarios/judge-intervention.spec.ts`

### User Story
> As a user, I want the judge to stop the debate intelligently when it detects repetition or convergence.

```typescript
import { test, expect } from '@playwright/test';

test.describe('Judge Intervention', () => {
  test('should stop debate when judge detects repetition', async ({ page }) => {
    // Mock backend to return repetition flag after round 3
    await page.route('**/api/judge/assess', (route, request) => {
      const requestBody = request.postDataJSON();
      if (requestBody.round_number >= 3) {
        route.fulfill({
          status: 200,
          body: JSON.stringify({
            quality_scores: [...],
            should_continue: false,
            flags: {
              repetition_detected: true,
              convergence_reached: false,
              diminishing_returns: true
            }
          })
        });
      } else {
        route.continue();
      }
    });

    await page.goto('/debates/new');

    // Configure free-form debate (no round limit)
    await page.fill('[data-testid="debate-topic"]', 'Repetitive topic');
    // ...
    await page.selectOption('[data-testid="debate-format"]', 'free-form');

    await page.click('[data-testid="start-debate"]');

    // Wait for multiple rounds
    await expect(page.locator('[data-testid="current-round"]'))
      .toHaveText('3', { timeout: 90000 });

    // Verify judge assessment shows repetition
    await expect(page.locator('[data-testid="judge-assessment"]'))
      .toContainText(/repetition|repeating/i, { timeout: 10000 });

    // Verify debate stops
    await expect(page.locator('[data-testid="debate-status"]'))
      .toHaveText(/Completed/, { timeout: 10000 });

    // Verify termination reason displayed
    await expect(page.locator('[data-testid="termination-reason"]'))
      .toContainText(/repetition|diminishing/i);
  });

  test('should stop when convergence reached', async ({ page }) => {
    // Mock convergence detection
    await page.route('**/api/judge/assess', (route, request) => {
      const requestBody = request.postDataJSON();
      if (requestBody.round_number >= 2) {
        route.fulfill({
          status: 200,
          body: JSON.stringify({
            quality_scores: [...],
            should_continue: false,
            flags: {
              repetition_detected: false,
              convergence_reached: true,
              diminishing_returns: false
            },
            round_summary: "Participants have reached agreement."
          })
        });
      } else {
        route.continue();
      }
    });

    await page.goto('/debates/new');

    // Configure convergence-seeking debate
    await page.fill('[data-testid="debate-topic"]', 'Convergence topic');
    // ...
    await page.selectOption('[data-testid="debate-format"]', 'convergence-seeking');

    await page.click('[data-testid="start-debate"]');

    // Wait for convergence
    await expect(page.locator('[data-testid="debate-status"]'))
      .toHaveText(/Completed/, { timeout: 60000 });

    // Verify early termination (should be <5 rounds)
    const finalRound = await page.locator('[data-testid="current-round"]')
      .textContent();
    expect(parseInt(finalRound!)).toBeLessThan(5);

    // Verify convergence message
    await expect(page.locator('[data-testid="termination-reason"]'))
      .toContainText(/convergence|agreement/i);
  });

  test('should display judge assessment clearly', async ({ page }) => {
    await page.goto('/debates/new');

    // Configure and start debate
    // ...

    await page.click('[data-testid="start-debate"]');

    // Wait for first round completion
    await expect(page.locator('[data-testid="round-complete-indicator"]'))
      .toBeVisible({ timeout: 60000 });

    // Verify judge assessment panel
    const assessment = page.locator('[data-testid="judge-assessment"]');
    await expect(assessment).toBeVisible();

    // Verify quality scores for each participant
    await expect(page.locator('[data-testid="participant-1-score"]'))
      .toBeVisible();
    await expect(page.locator('[data-testid="participant-2-score"]'))
      .toBeVisible();

    // Verify round summary
    await expect(page.locator('[data-testid="round-summary"]'))
      .not.toBeEmpty();

    // Verify continue/stop decision indicator
    const continueIndicator = page.locator('[data-testid="should-continue"]');
    await expect(continueIndicator).toBeVisible();
  });
});
```

---

## 8. Scenario 6: Export Functionality

**File:** `tests/e2e/phase2/scenarios/export.spec.ts`

### User Story
> As a user, I want to export completed debates as Markdown or JSON for sharing and analysis.

```typescript
import { test, expect } from '@playwright/test';
import fs from 'fs';
import path from 'path';

test.describe('Debate Export', () => {
  test('should export debate as Markdown', async ({ page }) => {
    await page.goto('/debates/new');

    // Configure and complete debate
    // ...

    await page.click('[data-testid="start-debate"]');

    // Wait for completion
    await expect(page.locator('[data-testid="debate-status"]'))
      .toHaveText(/Completed/, { timeout: 120000 });

    // Click export button
    await page.click('[data-testid="export-debate"]');

    // Select Markdown format
    await page.click('[data-testid="export-format-markdown"]');

    // Wait for download
    const downloadPromise = page.waitForEvent('download');
    await page.click('[data-testid="confirm-export"]');
    const download = await downloadPromise;

    // Verify filename
    expect(download.suggestedFilename()).toMatch(/debate-.*\.md$/);

    // Save and verify content
    const downloadPath = path.join(__dirname, '../downloads', download.suggestedFilename());
    await download.saveAs(downloadPath);

    const content = fs.readFileSync(downloadPath, 'utf-8');

    // Verify Markdown structure
    expect(content).toContain('# Debate:');
    expect(content).toContain('## Round 1');
    expect(content).toContain('## Judge\'s Final Verdict');
    expect(content).toContain('### Participant');

    // Cleanup
    fs.unlinkSync(downloadPath);
  });

  test('should export debate as JSON', async ({ page }) => {
    await page.goto('/debates/new');

    // Configure and complete debate
    // ...

    await page.click('[data-testid="start-debate"]');

    // Wait for completion
    await expect(page.locator('[data-testid="debate-status"]'))
      .toHaveText(/Completed/, { timeout: 120000 });

    // Export as JSON
    await page.click('[data-testid="export-debate"]');
    await page.click('[data-testid="export-format-json"]');

    const downloadPromise = page.waitForEvent('download');
    await page.click('[data-testid="confirm-export"]');
    const download = await downloadPromise;

    // Verify filename
    expect(download.suggestedFilename()).toMatch(/debate-.*\.json$/);

    // Save and verify content
    const downloadPath = path.join(__dirname, '../downloads', download.suggestedFilename());
    await download.saveAs(downloadPath);

    const content = fs.readFileSync(downloadPath, 'utf-8');
    const json = JSON.parse(content);

    // Verify JSON structure
    expect(json).toHaveProperty('debate_id');
    expect(json).toHaveProperty('topic');
    expect(json).toHaveProperty('participants');
    expect(json).toHaveProperty('rounds');
    expect(json).toHaveProperty('judge');
    expect(json.rounds).toBeInstanceOf(Array);
    expect(json.rounds.length).toBeGreaterThan(0);

    // Cleanup
    fs.unlinkSync(downloadPath);
  });

  test('should preview export before downloading', async ({ page }) => {
    await page.goto('/debates/new');

    // Complete debate
    // ...

    await page.click('[data-testid="export-debate"]');
    await page.click('[data-testid="export-format-markdown"]');

    // Click preview instead of export
    await page.click('[data-testid="preview-export"]');

    // Verify preview modal
    await expect(page.locator('[data-testid="export-preview-modal"]'))
      .toBeVisible();

    // Verify preview content
    const preview = await page.locator('[data-testid="export-preview-content"]')
      .textContent();
    expect(preview).toContain('# Debate:');
    expect(preview).toContain('## Round');

    // Close preview
    await page.click('[data-testid="close-preview"]');
    await expect(page.locator('[data-testid="export-preview-modal"]'))
      .not.toBeVisible();
  });
});
```

---

## 9. Running E2E Tests

```bash
# Run all Phase 2 E2E tests
npm run test:e2e:phase2

# Run specific scenario
npm run test:e2e:phase2 -- simple-debate.spec.ts

# Run in headed mode (see browser)
npm run test:e2e:phase2 -- --headed

# Run in specific browser
npm run test:e2e:phase2 -- --project=chromium

# Debug mode
npm run test:e2e:phase2 -- --debug

# Generate HTML report
npm run test:e2e:phase2 -- --reporter=html

# Run with video recording
npm run test:e2e:phase2 -- --video=on
```

---

## 10. Success Criteria

| Scenario | Pass Criteria |
|----------|---------------|
| Scenario 1: Simple debate | Completes with streaming responses and final verdict |
| Scenario 2: 4-debater | All 4 participants stream simultaneously, 3 rounds complete |
| Scenario 3: Cost warning | Warning appears, user can continue or stop |
| Scenario 4: Stream failure | Automatic reconnection within 10 seconds |
| Scenario 5: Judge intervention | Debate stops when repetition/convergence detected |
| Scenario 6: Export | Valid Markdown/JSON downloaded |

---

## 11. Test Data & Helpers

**File:** `tests/e2e/phase2/helpers/debate-helpers.ts`

```typescript
export async function configureSimpleDebate(page: Page) {
  await page.fill('[data-testid="debate-topic"]', 'Test topic');
  await page.click('[data-testid="add-participant"]');
  await page.selectOption('[data-testid="participant-1-model"]', 'claude-3-5-sonnet-20241022');
  await page.fill('[data-testid="participant-1-persona"]', 'Debater A');
  await page.click('[data-testid="add-participant"]');
  await page.selectOption('[data-testid="participant-2-model"]', 'gpt-4');
  await page.fill('[data-testid="participant-2-persona"]', 'Debater B');
  await page.selectOption('[data-testid="judge-model"]', 'claude-3-opus-20240229');
}

export async function waitForDebateCompletion(page: Page, timeout = 120000) {
  await expect(page.locator('[data-testid="debate-status"]'))
    .toHaveText(/Completed/, { timeout });
}
```

---

**Status:** ✅ Ready for Implementation
**Estimated Test Count:** 25+ E2E scenarios
**Estimated Runtime:** 10-15 minutes per browser
**Browser Coverage:** Chrome, Firefox, Safari, Mobile Chrome
