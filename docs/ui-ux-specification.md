# Quorum - UI/UX Architecture Specification

## Executive Summary

This document provides a comprehensive UI/UX architecture for Quorum, a real-time multi-LLM debate platform. Based on extensive research of current best practices, component libraries, and accessibility standards, this specification delivers actionable design patterns, component recommendations, and implementation strategies optimized for React/Next.js.

**Key Recommendations:**
- **Component Library:** shadcn/ui with Tailwind CSS
- **Streaming Strategy:** Server-Sent Events (SSE) for one-way AI responses
- **Layout Pattern:** Responsive multi-column grid (4-column desktop, 2-column tablet, stacked mobile)
- **Animation:** Custom typewriter effect with react-type-animation as fallback
- **Accessibility:** WCAG 2.2 Level AA compliance with ARIA live regions

---

## 1. Component Architecture

### 1.1 Component Hierarchy

```
App (Next.js 14+ with App Router)
├── DebateConfigurationPage
│   ├── TopicInput
│   ├── ParticipantSelector
│   │   ├── ModelDropdown (per debater)
│   │   └── PersonaAssignment (auto/custom toggle)
│   ├── JudgeSelector
│   ├── FormatSelector (4 formats)
│   └── StartDebateButton
│
├── LiveDebateInterface
│   ├── DebateHeader
│   │   ├── TopicDisplay
│   │   ├── RoundIndicator
│   │   └── ControlPanel (pause/resume/stop)
│   │
│   ├── DebateStreamGrid
│   │   ├── DebaterStream (2-4 instances)
│   │   │   ├── DebaterHeader
│   │   │   │   ├── Avatar/Icon
│   │   │   │   ├── NameLabel
│   │   │   │   ├── PersonaBadge
│   │   │   │   └── StatusIndicator (typing/idle)
│   │   │   │
│   │   │   └── MessageContainer
│   │   │       ├── StreamingText (typewriter effect)
│   │   │       ├── Timestamp
│   │   │       └── CrossReferences (clickable mentions)
│   │   │
│   │   └── GridLayoutManager (responsive)
│   │
│   └── JudgePanel (collapsible sidebar/bottom panel)
│       ├── JudgePanelHeader
│       ├── RoundAssessments (optional, toggleable)
│       ├── QualityMetrics (visual indicators)
│       └── FinalVerdict (when complete)
│
├── DebateHistoryPage
│   ├── DebateList
│   │   └── DebateCard (preview)
│   └── DebateViewer
│       ├── ReplayControls
│       │   ├── PlayPauseButton
│       │   ├── RoundScrubber
│       │   └── PlaybackSpeed
│       └── ExportButton (Markdown/JSON)
│
└── SettingsPage
    └── APIKeyManager
        ├── ProviderKeyInput (Anthropic, OpenAI, Google, Mistral)
        ├── KeyValidation
        ├── StorageOptions (local/session toggle)
        └── ProviderStatusIndicators
```

### 1.2 Component Responsibilities

**DebateStreamGrid**
- Manages responsive layout (4-col → 2-col → 1-col)
- Handles simultaneous vs. sequential reveal modes
- Coordinates scroll synchronization across streams
- Manages round-based batching for simultaneous mode

**DebaterStream**
- Receives SSE stream and buffers text
- Implements typewriter animation
- Handles cross-reference highlighting and linking
- Manages individual debater state (typing, idle, complete)

**JudgePanel**
- Collapsible/expandable sidebar (desktop) or bottom drawer (tablet/mobile)
- Displays real-time quality assessments
- Shows structured verdict with clear visual hierarchy
- Provides "verdict arrived" notification

**ReplayControls**
- Timeline scrubber showing round markers
- Speed controls (0.5x, 1x, 2x, 4x)
- Jump to round functionality
- Progress indicator

---

## 2. Recommended Component Library

### 2.1 Primary Recommendation: **shadcn/ui**

**Justification:**
1. **Flexibility & Customization:** shadcn/ui provides "open code" where components are copied directly into the project, enabling unlimited customization without fighting against library constraints
2. **Modern Stack Alignment:** Built on Radix UI primitives with Tailwind CSS, perfectly aligned with current best practices
3. **Performance:** Lightweight with no bundle bloat—only include components you actually use
4. **Design Freedom:** Not bound to Material Design, allowing Quorum to establish a unique visual identity
5. **TypeScript-First:** Excellent type safety out of the box
6. **Active Development:** Rapidly growing community with regular updates

**Key Components to Use:**
- `Dialog` - For settings modal, export dialogs
- `Select` - Model selection dropdowns
- `Tabs` - Debate format selection
- `Card` - Debater stream containers, debate history cards
- `Button` - Primary actions (start debate, pause, export)
- `Badge` - Persona labels, round indicators, status tags
- `Separator` - Visual dividers between rounds
- `ScrollArea` - Message containers with custom scrollbars
- `Collapsible` - Judge panel expand/collapse
- `Toast` - Notifications (debate started, error messages, export complete)
- `Avatar` - Debater profile images/icons
- `Progress` - Round progress, loading indicators
- `Switch` - Auto-assign toggle, settings options
- `Tooltip` - Hover explanations for controls

**Supporting Libraries:**
- **Tailwind CSS:** Utility-first styling for rapid development
- **Radix UI:** Unstyled accessible primitives (shadcn/ui is built on this)
- **class-variance-authority (CVA):** Type-safe component variants
- **tailwind-merge:** Intelligent class merging
- **Framer Motion:** Advanced animations (optional, for enhanced transitions)

### 2.2 Alternative: Material UI (MUI)

**When to Consider:**
- Team has extensive MUI experience
- Material Design aesthetic is desired
- Need enterprise-grade data components for future analytics features

**Trade-offs:**
- Larger bundle size
- More opinionated design system
- Harder to achieve unique visual identity
- 10 years of stability and comprehensive documentation

**Recommendation:** Use shadcn/ui for MVP to maintain design flexibility and optimal performance.

---

## 3. Layout Patterns

### 3.1 Desktop Layout (≥1280px)

```
┌─────────────────────────────────────────────────────────────────┐
│ Header: Topic | Round 2/5 | [Pause] [Stop] [Export]            │
├───────────────┬───────────────┬───────────────┬─────────────────┤
│               │               │               │                 │
│  Debater 1    │  Debater 2    │  Debater 3    │  Judge Panel   │
│  ┌─────────┐  │  ┌─────────┐  │  ┌─────────┐  │  ┌───────────┐ │
│  │ Avatar  │  │  │ Avatar  │  │  │ Avatar  │  │  │  Metrics  │ │
│  │ Claude  │  │  │  GPT-4  │  │  │ Gemini  │  │  │           │ │
│  │Pro-Mars │  │  │Anti-Mars│  │  │Moderate │  │  │ Quality:  │ │
│  └─────────┘  │  └─────────┘  │  └─────────┘  │  │ ████░░ 8  │ │
│               │               │               │  │           │ │
│  Streaming    │  Streaming    │  Streaming    │  │ Relevance │ │
│  text with    │  text with    │  text with    │  │ ████░░ 8  │ │
│  typewriter   │  typewriter   │  typewriter   │  │           │ │
│  effect...    │  effect...    │  effect...    │  │ ▼ Round   │ │
│               │               │               │  │   Notes   │ │
│  12:45:32     │  12:45:35     │  12:45:33     │  └───────────┘ │
│               │               │               │                 │
│               │               │               │                 │
│               │               │               │                 │
└───────────────┴───────────────┴───────────────┴─────────────────┘
```

**Grid Specification:**
- **4-column layout:** 3 columns for debaters (equal width, flexible), 1 column for judge (fixed 320px)
- **CSS Grid:** `grid-template-columns: repeat(3, minmax(280px, 1fr)) 320px`
- **Gap:** 16px between columns
- **Judge Panel:** Fixed-width sidebar, collapsible to icon bar (40px)
- **Max Content Width:** 1920px (centers on ultra-wide displays)

### 3.2 Tablet Layout (768px - 1279px)

```
┌─────────────────────────────────────────────┐
│ Header: Topic | Round 2/5 | [≡ Controls]   │
├──────────────────────┬──────────────────────┤
│                      │                      │
│   Debater 1          │   Debater 2         │
│   Claude (Pro)       │   GPT-4 (Anti)      │
│   Streaming text...  │   Streaming text... │
│                      │                      │
├──────────────────────┴──────────────────────┤
│                      │                      │
│   Debater 3          │   Debater 4         │
│   Gemini (Mod)       │   Mistral (Skep)    │
│   Streaming text...  │   Streaming text... │
│                      │                      │
├──────────────────────────────────────────────┤
│ Judge Panel (Bottom Drawer - Slide Up)      │
│ [▲] Quality: High | Relevance: Good         │
└──────────────────────────────────────────────┘
```

**Grid Specification:**
- **2-column layout:** `grid-template-columns: repeat(2, 1fr)`
- **Rows:** Auto-flow, 2 debaters per row
- **Judge Panel:** Bottom drawer (Sheet component), swipe up to reveal
- **Gap:** 12px between columns/rows

### 3.3 Mobile Layout (<768px)

```
┌────────────────────────────┐
│ [≡] Round 2/5    [⋮ More] │
├────────────────────────────┤
│                            │
│  Debater 1: Claude (Pro)   │
│  ┌──────────────────────┐  │
│  │ Streaming text with  │  │
│  │ typewriter effect... │  │
│  └──────────────────────┘  │
│  12:45:32                  │
│                            │
├────────────────────────────┤
│                            │
│  Debater 2: GPT-4 (Anti)   │
│  ┌──────────────────────┐  │
│  │ Streaming text...    │  │
│  └──────────────────────┘  │
│  12:45:35                  │
│                            │
├────────────────────────────┤
│ [▲] Judge Assessment       │
└────────────────────────────┘
```

**Specification:**
- **Single column:** `grid-template-columns: 1fr`
- **Stacked layout:** Vertical scroll through all debaters
- **Compact headers:** Hamburger menu for controls
- **Judge Panel:** Persistent bottom bar with tap-to-expand
- **Gap:** 8px between sections

### 3.4 Responsive Breakpoints

```css
/* Tailwind CSS classes */
.debate-grid {
  /* Mobile first - single column */
  @apply grid grid-cols-1 gap-2;

  /* Tablet - 2 columns */
  @apply md:grid-cols-2 md:gap-3;

  /* Desktop - 3 debaters + judge sidebar */
  @apply lg:grid-cols-[repeat(3,minmax(280px,1fr))_320px] lg:gap-4;

  /* Large desktop - optimize spacing */
  @apply xl:gap-6;
}
```

---

## 4. Streaming Animation Patterns

### 4.1 Recommended Approach: Custom Hook + SSE

**Implementation Pattern:**

```tsx
// hooks/useStreamingText.ts
import { useState, useEffect, useRef } from 'react';

interface StreamingOptions {
  speed?: number; // ms per character
  onComplete?: () => void;
  enabled?: boolean; // Allow pause/resume
}

export function useStreamingText(
  eventSource: string | null,
  options: StreamingOptions = {}
) {
  const [displayedText, setDisplayedText] = useState('');
  const [fullText, setFullText] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const bufferRef = useRef('');
  const { speed = 30, onComplete, enabled = true } = options;

  // Receive SSE data and buffer
  useEffect(() => {
    if (!eventSource) return;

    const source = new EventSource(eventSource);

    source.onmessage = (event) => {
      const chunk = event.data;
      bufferRef.current += chunk;
      setFullText(prev => prev + chunk);
    };

    source.addEventListener('done', () => {
      setIsStreaming(false);
      source.close();
    });

    source.onerror = (error) => {
      console.error('SSE Error:', error);
      source.close();
      setIsStreaming(false);
    };

    setIsStreaming(true);
    return () => source.close();
  }, [eventSource]);

  // Typewriter effect from buffer
  useEffect(() => {
    if (!enabled || displayedText.length >= fullText.length) {
      if (displayedText.length === fullText.length && fullText.length > 0) {
        onComplete?.();
      }
      return;
    }

    const timeout = setTimeout(() => {
      setDisplayedText(fullText.slice(0, displayedText.length + 1));
    }, speed);

    return () => clearTimeout(timeout);
  }, [displayedText, fullText, speed, enabled, onComplete]);

  return {
    displayedText,
    isStreaming,
    isComplete: displayedText.length === fullText.length
  };
}
```

**Usage in Component:**

```tsx
function DebaterStream({ debaterId, sseEndpoint }) {
  const { displayedText, isStreaming } = useStreamingText(sseEndpoint, {
    speed: 30, // 30ms per character
    onComplete: () => console.log('Stream complete'),
  });

  return (
    <div className="debater-stream">
      <div className="message-content">
        {displayedText}
        {isStreaming && <span className="cursor-blink">|</span>}
      </div>
    </div>
  );
}
```

### 4.2 Fallback: react-type-animation Library

**For simpler implementation or non-SSE scenarios:**

```tsx
import { TypeAnimation } from 'react-type-animation';

function DebaterMessage({ text }) {
  return (
    <TypeAnimation
      sequence={[text]}
      wrapper="span"
      speed={80} // Higher = faster
      cursor={false}
      repeat={0}
    />
  );
}
```

### 4.3 Animation Performance Optimizations

1. **Virtualization for Long Debates:**
   - Use `react-window` or `@tanstack/react-virtual` for message lists exceeding 100 messages
   - Only render visible messages + buffer

2. **Debounced Scroll:**
   - Auto-scroll to bottom during streaming with smooth behavior
   - Detect user scroll-up and disable auto-scroll
   - Show "New message" indicator when user is scrolled up

3. **Request Animation Frame:**
   - For ultra-smooth animations, use `requestAnimationFrame` instead of `setTimeout`

```tsx
// Performance-optimized streaming
useEffect(() => {
  if (!enabled || displayedText.length >= fullText.length) return;

  let frameId: number;
  let lastUpdate = Date.now();

  const animate = () => {
    const now = Date.now();
    if (now - lastUpdate >= speed) {
      setDisplayedText(fullText.slice(0, displayedText.length + 1));
      lastUpdate = now;
    }
    if (displayedText.length < fullText.length) {
      frameId = requestAnimationFrame(animate);
    }
  };

  frameId = requestAnimationFrame(animate);
  return () => cancelAnimationFrame(frameId);
}, [displayedText, fullText, speed, enabled]);
```

### 4.4 CSS Animations

```css
/* Cursor blink */
@keyframes blink {
  0%, 49% { opacity: 1; }
  50%, 100% { opacity: 0; }
}

.cursor-blink {
  animation: blink 1s infinite;
}

/* Fade-in for new messages */
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.message-enter {
  animation: fadeIn 0.3s ease-out;
}

/* Typing indicator pulse */
@keyframes pulse {
  0%, 100% { opacity: 0.4; }
  50% { opacity: 1; }
}

.typing-indicator span {
  animation: pulse 1.4s infinite;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}
```

---

## 5. Color & Visual Coding System

### 5.1 Participant Color Palette

**Best Practice:** Color names/badges, not entire message bubbles, to avoid visual overwhelm.

**Color Assignment:**

```tsx
// Semantic color system (8 distinct colors for accessibility)
const DEBATER_COLORS = {
  blue: {
    primary: 'hsl(221, 83%, 53%)',    // #2563eb
    light: 'hsl(221, 83%, 95%)',      // Background tint
    border: 'hsl(221, 83%, 40%)',
    text: 'hsl(221, 100%, 20%)',
  },
  violet: {
    primary: 'hsl(258, 90%, 66%)',    // #a855f7
    light: 'hsl(258, 90%, 95%)',
    border: 'hsl(258, 90%, 50%)',
    text: 'hsl(258, 100%, 25%)',
  },
  emerald: {
    primary: 'hsl(160, 84%, 39%)',    // #10b981
    light: 'hsl(160, 84%, 95%)',
    border: 'hsl(160, 84%, 30%)',
    text: 'hsl(160, 100%, 20%)',
  },
  amber: {
    primary: 'hsl(38, 92%, 50%)',     // #f59e0b
    light: 'hsl(38, 92%, 95%)',
    border: 'hsl(38, 92%, 40%)',
    text: 'hsl(38, 100%, 25%)',
  },
  rose: {
    primary: 'hsl(351, 83%, 58%)',    // #fb7185
    light: 'hsl(351, 83%, 95%)',
    border: 'hsl(351, 83%, 45%)',
    text: 'hsl(351, 100%, 25%)',
  },
  cyan: {
    primary: 'hsl(188, 94%, 43%)',    // #06b6d4
    light: 'hsl(188, 94%, 95%)',
    border: 'hsl(188, 94%, 35%)',
    text: 'hsl(188, 100%, 20%)',
  },
  orange: {
    primary: 'hsl(25, 95%, 53%)',     // #f97316
    light: 'hsl(25, 95%, 95%)',
    border: 'hsl(25, 95%, 40%)',
    text: 'hsl(25, 100%, 25%)',
  },
  indigo: {
    primary: 'hsl(239, 84%, 67%)',    // #818cf8
    light: 'hsl(239, 84%, 95%)',
    border: 'hsl(239, 84%, 55%)',
    text: 'hsl(239, 100%, 25%)',
  },
};

// Judge uses neutral gray
const JUDGE_COLOR = {
  primary: 'hsl(215, 16%, 47%)',      // #64748b
  light: 'hsl(215, 16%, 95%)',
  border: 'hsl(215, 16%, 35%)',
  text: 'hsl(215, 100%, 15%)',
};
```

### 5.2 Visual Differentiation Strategy

**1. Name Badge (Primary Identifier)**

```tsx
function DebaterHeader({ name, persona, color }) {
  return (
    <div className="flex items-center gap-3 p-4">
      <Avatar className={`border-2 border-${color}-500`}>
        <AvatarFallback className={`bg-${color}-100 text-${color}-700`}>
          {name[0]}
        </AvatarFallback>
      </Avatar>
      <div>
        <h3 className={`font-semibold text-${color}-700`}>{name}</h3>
        <Badge variant="outline" className={`border-${color}-300 text-${color}-600`}>
          {persona}
        </Badge>
      </div>
    </div>
  );
}
```

**2. Subtle Border Accent**

```tsx
function MessageContainer({ color, children }) {
  return (
    <div className={`
      rounded-lg border-l-4 border-${color}-500
      bg-white dark:bg-gray-900
      p-4 shadow-sm
    `}>
      {children}
    </div>
  );
}
```

**3. Color Legend (Always Visible)**

```tsx
function ColorLegend({ debaters }) {
  return (
    <div className="flex gap-2 items-center">
      {debaters.map(({ name, color }) => (
        <div key={name} className="flex items-center gap-1">
          <div className={`w-3 h-3 rounded-full bg-${color}-500`} />
          <span className="text-sm text-gray-600">{name}</span>
        </div>
      ))}
    </div>
  );
}
```

### 5.3 Accessibility Considerations

**Color Contrast Requirements (WCAG 2.2 AA):**
- Text color contrast ratio ≥ 4.5:1 against background
- Large text (≥18pt) contrast ratio ≥ 3:1
- Non-text elements (borders, icons) ≥ 3:1

**Never Rely on Color Alone:**
- Use icons alongside color (e.g., different avatar shapes)
- Include text labels for all participants
- Provide pattern overlays as alternative to color (optional user setting)

**Colorblind-Friendly Palette:**
The chosen colors (blue, violet, emerald, amber, rose, cyan, orange, indigo) are distinguishable for most types of color vision deficiency:
- Protanopia (red-weak)
- Deuteranopia (green-weak)
- Tritanopia (blue-weak)

---

## 6. Accessibility Implementation

### 6.1 WCAG 2.2 Level AA Compliance

**Priority Areas:**
1. **Dynamic Content Announcements**
2. **Keyboard Navigation**
3. **Screen Reader Optimization**
4. **Focus Management**
5. **Color Contrast**

### 6.2 ARIA Live Regions for Streaming Content

**Challenge:** Screen readers struggle with rapidly changing content.

**Solution:** Implement throttled ARIA live announcements.

```tsx
function DebaterStream({ debaterId, name, sseEndpoint }) {
  const { displayedText, isStreaming } = useStreamingText(sseEndpoint);
  const [announcement, setAnnouncement] = useState('');

  // Throttle announcements to every 5 seconds during streaming
  useEffect(() => {
    if (!isStreaming) {
      setAnnouncement(`${name} finished speaking.`);
      return;
    }

    const interval = setInterval(() => {
      setAnnouncement(`${name} is speaking. ${displayedText.slice(-100)}`);
    }, 5000);

    return () => clearInterval(interval);
  }, [isStreaming, name, displayedText]);

  return (
    <div
      role="article"
      aria-label={`${name}'s argument`}
      aria-live="polite"
      aria-atomic="false"
    >
      {/* Hidden announcement for screen readers */}
      <div className="sr-only" aria-live="polite" aria-atomic="true">
        {announcement}
      </div>

      <div aria-hidden={isStreaming}>
        {displayedText}
      </div>
    </div>
  );
}
```

**ARIA Live Region Strategies:**

| Content Type | aria-live | aria-atomic | Update Frequency |
|-------------|-----------|-------------|------------------|
| Streaming text | `polite` | `false` | Every 5 seconds |
| New round started | `assertive` | `true` | Immediate |
| Judge verdict | `assertive` | `true` | Immediate |
| Debater finished | `polite` | `true` | Immediate |
| Quality metrics | `off` | - | Manual query only |

### 6.3 Keyboard Navigation

**Required Keyboard Shortcuts:**

```tsx
// Global shortcuts
const KEYBOARD_SHORTCUTS = {
  'Space': 'Pause/Resume debate',
  'Escape': 'Stop debate',
  'E': 'Export debate',
  'J': 'Toggle judge panel',
  '1-4': 'Focus debater 1-4',
  'ArrowUp/Down': 'Scroll through messages',
  'Ctrl+F': 'Search in debate',
};

function useKeyboardShortcuts() {
  useEffect(() => {
    function handleKeyPress(e: KeyboardEvent) {
      // Don't trigger if user is typing in input
      if (e.target instanceof HTMLInputElement) return;

      switch(e.key) {
        case ' ':
          e.preventDefault();
          togglePause();
          break;
        case 'Escape':
          stopDebate();
          break;
        case 'e':
          if (e.ctrlKey || e.metaKey) {
            e.preventDefault();
            openExportDialog();
          }
          break;
        case 'j':
          toggleJudgePanel();
          break;
        case '1':
        case '2':
        case '3':
        case '4':
          focusDebater(parseInt(e.key));
          break;
      }
    }

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, []);
}
```

**Focus Management:**

```tsx
function LiveDebateInterface() {
  const debateStartedRef = useRef(false);

  useEffect(() => {
    if (debateStatus === 'started' && !debateStartedRef.current) {
      debateStartedRef.current = true;
      // Announce to screen readers
      announceToScreenReader('Debate has started. Press 1-4 to focus on specific debaters.');
      // Move focus to first debater
      document.getElementById('debater-1')?.focus();
    }
  }, [debateStatus]);

  return (
    <div role="main" aria-label="Live debate interface">
      {/* Skip link */}
      <a href="#debate-controls" className="sr-only focus:not-sr-only">
        Skip to debate controls
      </a>
      {/* ... */}
    </div>
  );
}
```

### 6.4 Screen Reader Optimizations

**1. Semantic HTML Structure:**

```tsx
<main role="main" aria-label="Debate interface">
  <header role="banner">
    <h1>Debate: {topic}</h1>
  </header>

  <nav role="navigation" aria-label="Debate controls">
    {/* Control buttons */}
  </nav>

  <section role="region" aria-label="Debate participants">
    <article
      role="article"
      aria-labelledby="debater-1-name"
      tabIndex={0}
    >
      <h2 id="debater-1-name">Claude - Pro Position</h2>
      {/* Content */}
    </article>
  </section>

  <aside role="complementary" aria-label="Judge assessment">
    {/* Judge panel */}
  </aside>
</main>
```

**2. Descriptive Labels:**

```tsx
// ❌ Bad
<button>▶</button>

// ✅ Good
<button aria-label="Resume debate">
  <PlayIcon aria-hidden="true" />
  <span className="sr-only">Resume debate</span>
</button>
```

**3. Loading States:**

```tsx
function StreamLoadingIndicator({ debaterName }) {
  return (
    <div role="status" aria-live="polite">
      <span className="sr-only">{debaterName} is generating response...</span>
      <div className="typing-indicator" aria-hidden="true">
        <span></span><span></span><span></span>
      </div>
    </div>
  );
}
```

### 6.5 Reduced Motion Support

```css
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }

  /* Disable typewriter effect - show all text immediately */
  .streaming-text {
    animation: none;
  }
}
```

```tsx
function useReducedMotion() {
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);

  useEffect(() => {
    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    setPrefersReducedMotion(mediaQuery.matches);

    const listener = (e: MediaQueryListEvent) => {
      setPrefersReducedMotion(e.matches);
    };

    mediaQuery.addEventListener('change', listener);
    return () => mediaQuery.removeEventListener('change', listener);
  }, []);

  return prefersReducedMotion;
}

// Usage
const reducedMotion = useReducedMotion();
const typewriterSpeed = reducedMotion ? 0 : 30; // Instant if reduced motion
```

---

## 7. Responsive Design Strategy

### 7.1 Mobile-First Approach

**Core Principle:** Design for smallest screens first, progressively enhance for larger displays.

```tsx
// Component example - mobile first
function DebateInterface() {
  return (
    <div className="
      /* Mobile: Stack vertically, full width */
      flex flex-col w-full gap-2

      /* Tablet: 2-column grid */
      md:grid md:grid-cols-2 md:gap-3

      /* Desktop: 4-column with sidebar */
      lg:grid-cols-[repeat(3,1fr)_320px] lg:gap-4

      /* Large desktop: Increase spacing */
      xl:gap-6 xl:max-w-screen-2xl xl:mx-auto
    ">
      {/* Content */}
    </div>
  );
}
```

### 7.2 Breakpoint Strategy

```typescript
// tailwind.config.ts
export default {
  theme: {
    screens: {
      'sm': '640px',   // Small phones in landscape
      'md': '768px',   // Tablets
      'lg': '1024px',  // Desktops
      'xl': '1280px',  // Large desktops
      '2xl': '1536px', // Ultra-wide

      // Custom breakpoints for Quorum
      'tablet': '768px',
      'desktop': '1280px',
    },
  },
};
```

### 7.3 Touch-Optimized Interactions

**Minimum Touch Target Sizes:**
- Buttons: 44x44px (Apple HIG) / 48x48px (Material Design)
- Tappable areas: Extend beyond visual bounds with padding

```tsx
function ControlButton({ icon, label, onClick }) {
  return (
    <button
      onClick={onClick}
      className="
        /* Visual size */
        px-4 py-2

        /* Touch target - minimum 44px */
        min-w-[44px] min-h-[44px]

        /* Ensure padding extends touch area */
        touch-manipulation
      "
      aria-label={label}
    >
      {icon}
    </button>
  );
}
```

**Swipe Gestures:**

```tsx
import { useSwipeable } from 'react-swipeable';

function JudgePanelMobile() {
  const [isOpen, setIsOpen] = useState(false);

  const handlers = useSwipeable({
    onSwipedUp: () => setIsOpen(true),
    onSwipedDown: () => setIsOpen(false),
    preventScrollOnSwipe: true,
    trackMouse: false,
  });

  return (
    <div
      {...handlers}
      className={`
        fixed bottom-0 left-0 right-0
        bg-white dark:bg-gray-900
        transform transition-transform duration-300
        ${isOpen ? 'translate-y-0' : 'translate-y-[calc(100%-60px)]'}
      `}
    >
      <div className="h-1 w-12 bg-gray-300 rounded mx-auto my-2" />
      {/* Judge content */}
    </div>
  );
}
```

### 7.4 Viewport Optimization

**Safe Areas (iOS Notch):**

```css
/* Support iPhone notch and home indicator */
.debate-header {
  padding-top: env(safe-area-inset-top);
}

.judge-panel-mobile {
  padding-bottom: env(safe-area-inset-bottom);
}
```

**Viewport Units:**

```css
/* Full viewport height accounting for mobile browser chrome */
.debate-container {
  height: 100vh;
  height: 100dvh; /* Dynamic viewport height - excludes browser UI */
}
```

### 7.5 Image and Icon Optimization

```tsx
// Use SVG icons for crisp rendering at any scale
import { MessageSquare, Gavel, Play, Pause, Download } from 'lucide-react';

// Avatar images with responsive sizing
function DebaterAvatar({ src, name, size = 'md' }) {
  const sizeClasses = {
    sm: 'w-8 h-8',
    md: 'w-12 h-12 md:w-16 md:h-16',
    lg: 'w-16 h-16 md:w-20 md:h-20',
  };

  return (
    <Avatar className={sizeClasses[size]}>
      <AvatarImage src={src} alt={`${name}'s avatar`} />
      <AvatarFallback>{name[0]}</AvatarFallback>
    </Avatar>
  );
}
```

---

## 8. Key Interaction Flows

### 8.1 Setup → Debate Flow

```
┌─────────────────┐
│  Landing Page   │
│  "Start Debate" │
└────────┬────────┘
         │
         ▼
┌─────────────────────────┐
│  Configuration Screen   │
│                         │
│  1. Enter Topic         │ ← Auto-focus on mount
│  2. Select Debaters     │ ← Min 2, max 4
│  3. Assign Personas     │ ← Toggle auto/custom
│  4. Select Judge        │
│  5. Choose Format       │
│                         │
│  [Start Debate] ────────┼──→ Validation
└─────────────────────────┘      │
                                 ▼
                          ┌──────────────┐
                          │ All fields   │
                          │ complete?    │
                          └──┬────────┬──┘
                             │ NO     │ YES
                             │        ▼
                             │   ┌─────────────────┐
                             │   │ Confirm Dialog  │
                             │   │                 │
                             │   │ Topic: ...      │
                             │   │ Debaters: ...   │
                             │   │ Format: ...     │
                             │   │                 │
                             │   │ [Cancel][Start] │
                             │   └────────┬────────┘
                             │            │
                             ▼            ▼
                     ┌──────────────────────────┐
                     │  Live Debate Interface   │
                     │                          │
                     │  - Streaming responses   │
                     │  - Judge monitoring      │
                     │  - Controls active       │
                     └──────────┬───────────────┘
                                │
                                ▼
                         Debate Complete
                                │
                                ▼
                     ┌──────────────────────┐
                     │  Summary Screen      │
                     │                      │
                     │  - Final verdict     │
                     │  - Export options    │
                     │  - Replay/New debate │
                     └──────────────────────┘
```

### 8.2 Live Debate Controls

**Control Panel States:**

```tsx
type DebateStatus = 'configuring' | 'starting' | 'active' | 'paused' | 'stopping' | 'complete';

function DebateControls({ status, onPause, onResume, onStop }) {
  return (
    <div className="flex gap-2">
      {status === 'active' && (
        <>
          <Button onClick={onPause} variant="secondary">
            <Pause className="mr-2" />
            Pause
          </Button>
          <Button onClick={onStop} variant="destructive">
            <Square className="mr-2" />
            Stop
          </Button>
        </>
      )}

      {status === 'paused' && (
        <>
          <Button onClick={onResume} variant="default">
            <Play className="mr-2" />
            Resume
          </Button>
          <Button onClick={onStop} variant="destructive">
            <Square className="mr-2" />
            Stop
          </Button>
        </>
      )}

      {status === 'complete' && (
        <>
          <Button onClick={openExport} variant="default">
            <Download className="mr-2" />
            Export
          </Button>
          <Button onClick={startReplay} variant="secondary">
            <RotateCcw className="mr-2" />
            Replay
          </Button>
          <Button onClick={startNew} variant="outline">
            New Debate
          </Button>
        </>
      )}
    </div>
  );
}
```

**Pause Behavior:**
- Immediately stop all SSE connections
- Buffer current streaming state
- Show "Paused" overlay on all debater streams
- Resume from exact position when unpaused

**Stop Behavior:**
- Confirm dialog: "Are you sure? Judge will provide summary of debate so far."
- Close SSE connections
- Request judge's partial verdict
- Transition to summary screen

### 8.3 Export Flow

```
User clicks "Export"
       │
       ▼
┌─────────────────────┐
│  Export Dialog      │
│                     │
│  Format:            │
│  ○ Markdown         │
│  ○ JSON             │
│  ○ HTML             │
│                     │
│  Options:           │
│  ☑ Include metadata │
│  ☑ Include judge    │
│  ☐ Timestamps       │
│                     │
│  [Cancel] [Export]  │
└──────────┬──────────┘
           │
           ▼
    Generate file
           │
           ▼
    ┌──────────────┐
    │ Browser      │
    │ downloads    │
    │ file         │
    └──────┬───────┘
           │
           ▼
    ┌──────────────┐
    │ Success      │
    │ Toast        │
    │ "Exported!"  │
    └──────────────┘
```

**Export Format Examples:**

**Markdown:**
```markdown
# Debate: Should We Colonize Mars?

**Format:** Structured Rounds
**Date:** 2024-01-15 14:32:00
**Rounds:** 5

## Participants

**Debater 1:** Claude (Anthropic)
- **Position:** Pro-Colonization
- **Persona:** Optimistic futurist focused on technological solutions

**Debater 2:** GPT-4 (OpenAI)
- **Position:** Anti-Colonization
- **Persona:** Pragmatic economist concerned with resource allocation

**Judge:** Gemini (Google)

---

## Round 1: Opening Statements

### Claude (Pro-Colonization)
*Timestamp: 14:32:15*

The colonization of Mars represents humanity's next great leap...

[Full text]

### GPT-4 (Anti-Colonization)
*Timestamp: 14:32:18*

While the vision of Mars colonization is inspiring, we must consider...

[Full text]

---

## Judge's Final Verdict

**Winner:** No clear winner
**Quality Score:** 8.5/10
**Relevance Score:** 9/10

**Summary:**
Both participants presented compelling arguments...

**Key Points of Agreement:**
- Mars has scientific value
- Technology is not yet ready

**Key Points of Disagreement:**
- Resource priority (Earth vs. Mars)
- Timeline feasibility
```

**JSON:**
```json
{
  "debate_id": "uuid-here",
  "topic": "Should We Colonize Mars?",
  "format": "structured_rounds",
  "timestamp_start": "2024-01-15T14:32:00Z",
  "timestamp_end": "2024-01-15T14:58:23Z",
  "participants": [
    {
      "id": "debater_1",
      "name": "Claude",
      "provider": "Anthropic",
      "model": "claude-3-opus-20240229",
      "position": "Pro-Colonization",
      "persona": "Optimistic futurist focused on technological solutions",
      "color": "blue"
    }
  ],
  "rounds": [
    {
      "round_number": 1,
      "round_type": "opening",
      "messages": [
        {
          "debater_id": "debater_1",
          "timestamp": "2024-01-15T14:32:15Z",
          "text": "The colonization of Mars...",
          "word_count": 342,
          "duration_seconds": 12.5
        }
      ]
    }
  ],
  "judge_verdict": {
    "winner": null,
    "quality_score": 8.5,
    "relevance_score": 9.0,
    "summary": "Both participants presented compelling...",
    "key_agreements": [],
    "key_disagreements": []
  }
}
```

### 8.4 Replay Flow

```
User opens saved debate
       │
       ▼
┌─────────────────────────┐
│  Debate Viewer          │
│                         │
│  [Timeline Scrubber]    │
│  ●──○──○──○──○          │
│  R1 R2 R3 R4 R5         │
│                         │
│  Speed: [1x ▼]          │
│  [◄◄] [▶] [▶▶]         │
│                         │
│  [Debate content...]    │
└─────────────────────────┘
       │
       ▼
  User interactions:
       │
       ├─ Click round marker → Jump to round
       ├─ Click play → Replay with typewriter
       ├─ Adjust speed → Change playback rate
       └─ Scrub timeline → Jump to timestamp
```

**Replay Implementation:**

```tsx
function DebateReplay({ debate }) {
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const [currentRound, setCurrentRound] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);

  const speedOptions = [
    { label: '0.5x', value: 0.5 },
    { label: '1x', value: 1 },
    { label: '2x', value: 2 },
    { label: '4x', value: 4 },
  ];

  return (
    <div>
      <ReplayControls
        currentRound={currentRound}
        totalRounds={debate.rounds.length}
        isPlaying={isPlaying}
        speed={playbackSpeed}
        onPlayPause={() => setIsPlaying(!isPlaying)}
        onSpeedChange={setPlaybackSpeed}
        onRoundChange={setCurrentRound}
      />

      <DebateContent
        round={debate.rounds[currentRound]}
        playback={{ enabled: isPlaying, speed: playbackSpeed }}
      />
    </div>
  );
}

function ReplayControls({
  currentRound,
  totalRounds,
  isPlaying,
  speed,
  onPlayPause,
  onSpeedChange,
  onRoundChange
}) {
  return (
    <div className="flex flex-col gap-4 p-4 bg-gray-100 rounded-lg">
      {/* Timeline scrubber */}
      <div className="relative">
        <input
          type="range"
          min={0}
          max={totalRounds - 1}
          value={currentRound}
          onChange={(e) => onRoundChange(parseInt(e.target.value))}
          className="w-full"
        />
        <div className="flex justify-between mt-1">
          {Array.from({ length: totalRounds }, (_, i) => (
            <span key={i} className="text-xs">R{i + 1}</span>
          ))}
        </div>
      </div>

      {/* Playback controls */}
      <div className="flex items-center justify-center gap-4">
        <Button
          size="sm"
          variant="outline"
          onClick={() => onRoundChange(Math.max(0, currentRound - 1))}
        >
          <SkipBack />
        </Button>

        <Button onClick={onPlayPause}>
          {isPlaying ? <Pause /> : <Play />}
        </Button>

        <Button
          size="sm"
          variant="outline"
          onClick={() => onRoundChange(Math.min(totalRounds - 1, currentRound + 1))}
        >
          <SkipForward />
        </Button>

        <Select value={speed.toString()} onValueChange={(v) => onSpeedChange(parseFloat(v))}>
          <SelectTrigger className="w-24">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {speedOptions.map(opt => (
              <SelectItem key={opt.value} value={opt.value.toString()}>
                {opt.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}
```

---

## 9. Advanced UI Patterns

### 9.1 Cross-Referencing System

**Problem:** Debaters reference each other by name. How to make these interactive?

**Solution:** Highlight mentions and enable click-to-scroll.

```tsx
function parseDebateText(text: string, debaters: Debater[]) {
  const debaterNames = debaters.map(d => d.name);

  // Regex to find debater mentions
  const mentionRegex = new RegExp(
    `(${debaterNames.join('|')})(?='s|\\s|,|\\.|\\))`,
    'gi'
  );

  const parts = [];
  let lastIndex = 0;
  let match;

  while ((match = mentionRegex.exec(text)) !== null) {
    // Text before mention
    if (match.index > lastIndex) {
      parts.push({
        type: 'text',
        content: text.slice(lastIndex, match.index),
      });
    }

    // Mention
    parts.push({
      type: 'mention',
      content: match[0],
      debaterId: debaters.find(d =>
        d.name.toLowerCase() === match[0].toLowerCase()
      )?.id,
    });

    lastIndex = match.index + match[0].length;
  }

  // Remaining text
  if (lastIndex < text.length) {
    parts.push({
      type: 'text',
      content: text.slice(lastIndex),
    });
  }

  return parts;
}

function MessageWithMentions({ text, debaters }) {
  const parts = parseDebateText(text, debaters);

  function scrollToDebater(debaterId: string) {
    document.getElementById(`debater-${debaterId}`)?.scrollIntoView({
      behavior: 'smooth',
      block: 'start',
    });
  }

  return (
    <p>
      {parts.map((part, index) => {
        if (part.type === 'mention' && part.debaterId) {
          const debater = debaters.find(d => d.id === part.debaterId);
          return (
            <button
              key={index}
              onClick={() => scrollToDebater(part.debaterId)}
              className={`
                font-medium text-${debater.color}-600
                hover:text-${debater.color}-800
                hover:underline
                cursor-pointer
                transition-colors
              `}
              aria-label={`Jump to ${debater.name}'s stream`}
            >
              {part.content}
            </button>
          );
        }
        return <span key={index}>{part.content}</span>;
      })}
    </p>
  );
}
```

### 9.2 Judge Panel Design

**Desktop Sidebar:**

```tsx
function JudgePanelDesktop({ isCollapsed, onToggle, assessment }) {
  return (
    <aside
      className={`
        transition-all duration-300
        ${isCollapsed ? 'w-12' : 'w-80'}
        border-l border-gray-200
        flex flex-col
      `}
      role="complementary"
      aria-label="Judge assessment panel"
    >
      {/* Collapse button */}
      <button
        onClick={onToggle}
        className="p-3 hover:bg-gray-100"
        aria-label={isCollapsed ? 'Expand judge panel' : 'Collapse judge panel'}
      >
        {isCollapsed ? <ChevronLeft /> : <ChevronRight />}
      </button>

      {!isCollapsed && (
        <div className="flex-1 overflow-y-auto p-4">
          <div className="flex items-center gap-2 mb-4">
            <Gavel className="w-5 h-5 text-gray-600" />
            <h2 className="font-semibold">Judge Assessment</h2>
          </div>

          {/* Quality Metrics */}
          <div className="space-y-3 mb-6">
            <MetricBar
              label="Quality"
              value={assessment.quality}
              max={10}
              color="blue"
            />
            <MetricBar
              label="Relevance"
              value={assessment.relevance}
              max={10}
              color="green"
            />
            <MetricBar
              label="Engagement"
              value={assessment.engagement}
              max={10}
              color="purple"
            />
          </div>

          {/* Round notes */}
          {assessment.roundNotes && (
            <Collapsible>
              <CollapsibleTrigger className="flex items-center gap-2 font-medium text-sm">
                <ChevronDown className="w-4 h-4" />
                Round Notes
              </CollapsibleTrigger>
              <CollapsibleContent className="mt-2 text-sm text-gray-600">
                {assessment.roundNotes}
              </CollapsibleContent>
            </Collapsible>
          )}

          {/* Final verdict (when available) */}
          {assessment.verdict && (
            <div className="mt-6 p-4 bg-gray-50 rounded-lg border border-gray-200">
              <h3 className="font-semibold mb-2">Final Verdict</h3>
              <p className="text-sm">{assessment.verdict}</p>
            </div>
          )}
        </div>
      )}
    </aside>
  );
}

function MetricBar({ label, value, max, color }) {
  const percentage = (value / max) * 100;

  return (
    <div>
      <div className="flex justify-between text-sm mb-1">
        <span className="text-gray-600">{label}</span>
        <span className="font-medium">{value}/{max}</span>
      </div>
      <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
        <div
          className={`h-full bg-${color}-500 transition-all duration-500`}
          style={{ width: `${percentage}%` }}
          role="progressbar"
          aria-valuenow={value}
          aria-valuemin={0}
          aria-valuemax={max}
          aria-label={`${label} score`}
        />
      </div>
    </div>
  );
}
```

**Mobile Bottom Sheet:**

```tsx
function JudgePanelMobile({ assessment }) {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      {/* Collapsed bar */}
      <div
        onClick={() => setIsOpen(true)}
        className="
          fixed bottom-0 left-0 right-0
          bg-white border-t border-gray-200
          p-4 cursor-pointer
          shadow-lg
        "
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Gavel className="w-4 h-4 text-gray-600" />
            <span className="font-medium text-sm">Judge</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="text-xs text-gray-600">
              Quality: {assessment.quality}/10
            </span>
            <ChevronUp className="w-4 h-4" />
          </div>
        </div>
      </div>

      {/* Expanded sheet */}
      <Sheet open={isOpen} onOpenChange={setIsOpen}>
        <SheetContent side="bottom" className="h-[80vh]">
          <SheetHeader>
            <SheetTitle>Judge Assessment</SheetTitle>
          </SheetHeader>

          <div className="mt-6 space-y-4">
            {/* Same content as desktop */}
          </div>
        </SheetContent>
      </Sheet>
    </>
  );
}
```

### 9.3 Simultaneous vs Sequential Mode UI

**Simultaneous Mode:**
- All debaters' streams load simultaneously
- Show "Waiting for all participants..." overlay
- Reveal all messages together with coordinated animation
- Visual indicator: "Simultaneous Reveal" badge

```tsx
function SimultaneousMode({ debaters, roundMessages }) {
  const [allComplete, setAllComplete] = useState(false);
  const [revealed, setRevealed] = useState(false);

  useEffect(() => {
    const complete = roundMessages.every(msg => msg.complete);
    if (complete && !allComplete) {
      setAllComplete(true);
      // Wait 1 second, then reveal
      setTimeout(() => setRevealed(true), 1000);
    }
  }, [roundMessages, allComplete]);

  return (
    <div className="relative">
      {allComplete && !revealed && (
        <div className="absolute inset-0 bg-white/90 z-10 flex items-center justify-center">
          <div className="text-center">
            <Loader2 className="w-8 h-8 animate-spin mx-auto mb-2" />
            <p className="font-medium">All responses received</p>
            <p className="text-sm text-gray-600">Revealing simultaneously...</p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {debaters.map((debater, index) => (
          <DebaterStream
            key={debater.id}
            debater={debater}
            message={roundMessages[index]}
            revealed={revealed}
          />
        ))}
      </div>
    </div>
  );
}
```

**Sequential Mode:**
- Debaters respond one after another
- Previous debaters' text is fully visible
- Current speaker highlighted with pulsing border
- Visual indicator: "Sequential Debate" badge

```tsx
function SequentialMode({ debaters, currentSpeaker }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {debaters.map((debater) => (
        <DebaterStream
          key={debater.id}
          debater={debater}
          isActive={debater.id === currentSpeaker}
          className={debater.id === currentSpeaker ? 'ring-2 ring-blue-500 ring-offset-2' : ''}
        />
      ))}
    </div>
  );
}
```

---

## 10. Performance Optimizations

### 10.1 Code Splitting

```tsx
// app/layout.tsx
import dynamic from 'next/dynamic';

// Lazy load debate interface (heavy component)
const LiveDebateInterface = dynamic(
  () => import('@/components/LiveDebateInterface'),
  {
    loading: () => <DebateLoadingSkeleton />,
    ssr: false, // Client-side only
  }
);

// Lazy load replay viewer
const DebateReplayViewer = dynamic(
  () => import('@/components/DebateReplayViewer'),
  { loading: () => <ReplayLoadingSkeleton /> }
);
```

### 10.2 Virtual Scrolling for Long Debates

```tsx
import { useVirtualizer } from '@tanstack/react-virtual';

function MessageList({ messages }) {
  const parentRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: messages.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 150, // Estimated message height
    overscan: 5, // Render 5 extra items above/below viewport
  });

  return (
    <div ref={parentRef} className="h-full overflow-y-auto">
      <div
        style={{
          height: `${virtualizer.getTotalSize()}px`,
          width: '100%',
          position: 'relative',
        }}
      >
        {virtualizer.getVirtualItems().map((virtualItem) => {
          const message = messages[virtualItem.index];
          return (
            <div
              key={virtualItem.key}
              style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: `${virtualItem.size}px`,
                transform: `translateY(${virtualItem.start}px)`,
              }}
            >
              <MessageBubble message={message} />
            </div>
          );
        })}
      </div>
    </div>
  );
}
```

### 10.3 SSE Connection Management

```tsx
function useDebateSSE(debateId: string, debaters: Debater[]) {
  const [connections, setConnections] = useState<Map<string, EventSource>>(new Map());

  useEffect(() => {
    const newConnections = new Map();

    debaters.forEach(debater => {
      const source = new EventSource(`/api/debate/${debateId}/stream/${debater.id}`);

      source.onmessage = (event) => {
        // Handle message
      };

      source.onerror = () => {
        console.error(`Connection lost for ${debater.name}`);
        // Implement retry logic
        retryConnection(debater.id);
      };

      newConnections.set(debater.id, source);
    });

    setConnections(newConnections);

    // Cleanup on unmount
    return () => {
      newConnections.forEach(source => source.close());
    };
  }, [debateId, debaters]);

  return connections;
}

function retryConnection(debaterId: string, attempt = 1) {
  const maxRetries = 5;
  const backoff = Math.min(1000 * Math.pow(2, attempt), 30000);

  if (attempt > maxRetries) {
    console.error(`Failed to reconnect after ${maxRetries} attempts`);
    return;
  }

  setTimeout(() => {
    console.log(`Retry attempt ${attempt} for ${debaterId}`);
    // Re-establish connection
  }, backoff);
}
```

---

## 11. Dark Mode Support

### 11.1 Implementation with next-themes

```tsx
// app/providers.tsx
import { ThemeProvider } from 'next-themes';

export function Providers({ children }) {
  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
      {children}
    </ThemeProvider>
  );
}
```

### 11.2 Color Palette Adjustments

```css
/* globals.css */
@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 222.2 84% 4.9%;

    /* Debater colors - light mode */
    --debater-blue: 221 83% 53%;
    --debater-violet: 258 90% 66%;
    --debater-emerald: 160 84% 39%;
    /* ... */
  }

  .dark {
    --background: 222.2 84% 4.9%;
    --foreground: 210 40% 98%;

    /* Debater colors - dark mode (slightly lighter) */
    --debater-blue: 221 83% 63%;
    --debater-violet: 258 90% 76%;
    --debater-emerald: 160 84% 49%;
    /* ... */
  }
}
```

### 11.3 Theme Toggle Component

```tsx
import { Moon, Sun } from 'lucide-react';
import { useTheme } from 'next-themes';

function ThemeToggle() {
  const { theme, setTheme } = useTheme();

  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
      aria-label="Toggle theme"
    >
      <Sun className="h-5 w-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
      <Moon className="absolute h-5 w-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
    </Button>
  );
}
```

---

## 12. Implementation Roadmap

### Phase 1: Foundation (Week 1-2)
- [ ] Set up Next.js 14+ with App Router
- [ ] Install and configure shadcn/ui + Tailwind CSS
- [ ] Create base component structure
- [ ] Implement responsive layout grid
- [ ] Set up dark mode support

### Phase 2: Configuration UI (Week 2-3)
- [ ] Build topic input form
- [ ] Implement participant selector
- [ ] Create persona assignment interface
- [ ] Add format selection
- [ ] Implement API key management

### Phase 3: Live Debate Interface (Week 3-5)
- [ ] Build debater stream components
- [ ] Implement SSE connection handling
- [ ] Create custom streaming text hook
- [ ] Add typewriter animation
- [ ] Implement cross-referencing system
- [ ] Build judge panel (desktop + mobile)
- [ ] Add debate controls (pause/resume/stop)

### Phase 4: Accessibility & Polish (Week 5-6)
- [ ] Implement ARIA live regions
- [ ] Add keyboard navigation
- [ ] Ensure WCAG 2.2 AA compliance
- [ ] Add reduced motion support
- [ ] Optimize touch targets for mobile

### Phase 5: History & Export (Week 6-7)
- [ ] Build debate history list
- [ ] Implement export functionality (Markdown/JSON)
- [ ] Create replay viewer
- [ ] Add playback controls
- [ ] Implement timeline scrubber

### Phase 6: Performance & Testing (Week 7-8)
- [ ] Implement virtual scrolling
- [ ] Add code splitting
- [ ] Optimize bundle size
- [ ] Test across browsers (Chrome, Firefox, Safari, Edge)
- [ ] Test on mobile devices (iOS, Android)
- [ ] Accessibility audit with screen readers

---

## 13. Technology Stack Summary

### Core Framework
- **Next.js 14+** with App Router
- **React 18+** with Server Components
- **TypeScript** for type safety

### UI Components
- **shadcn/ui** - Primary component library
- **Radix UI** - Headless UI primitives
- **Tailwind CSS** - Utility-first styling
- **Lucide React** - Icon library

### State Management
- **React Context** for global state (debate config, settings)
- **Zustand** (optional) for complex state management
- **React Query** (optional) for API state

### Streaming & Real-time
- **Server-Sent Events (SSE)** - One-way AI response streaming
- **EventSource API** - Native browser SSE support
- **Custom hooks** for stream management

### Animation
- **Framer Motion** (optional) - Advanced animations
- **CSS transitions** - Basic animations
- **Custom typewriter effect** - Text streaming

### Accessibility
- **@radix-ui/react-accessible-icon** - Icon accessibility
- **react-focus-lock** - Focus management
- **ARIA live regions** - Dynamic content announcements

### Performance
- **@tanstack/react-virtual** - Virtual scrolling
- **next/dynamic** - Code splitting
- **react-intersection-observer** - Lazy loading

### Development Tools
- **ESLint** - Linting
- **Prettier** - Code formatting
- **TypeScript ESLint** - TS-specific linting
- **Tailwind CSS Prettier Plugin** - Class sorting

---

## 14. Recommended File Structure

```
quorum/
├── app/
│   ├── (debate)/
│   │   ├── layout.tsx
│   │   ├── page.tsx                    # Landing/config
│   │   ├── debate/
│   │   │   └── [id]/
│   │   │       ├── page.tsx            # Live debate
│   │   │       └── loading.tsx
│   │   └── history/
│   │       ├── page.tsx                # Debate history list
│   │       └── [id]/
│   │           └── page.tsx            # Replay viewer
│   ├── settings/
│   │   └── page.tsx                    # API key management
│   ├── api/
│   │   └── debate/
│   │       ├── create/
│   │       │   └── route.ts
│   │       └── [id]/
│   │           └── stream/
│   │               └── [debaterId]/
│   │                   └── route.ts    # SSE endpoint
│   ├── layout.tsx
│   ├── globals.css
│   └── providers.tsx
│
├── components/
│   ├── ui/                             # shadcn/ui components
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── dialog.tsx
│   │   └── ...
│   │
│   ├── debate/
│   │   ├── DebateConfigForm.tsx
│   │   ├── ParticipantSelector.tsx
│   │   ├── PersonaAssignment.tsx
│   │   ├── FormatSelector.tsx
│   │   ├── LiveDebateInterface.tsx
│   │   ├── DebateStreamGrid.tsx
│   │   ├── DebaterStream.tsx
│   │   ├── DebaterHeader.tsx
│   │   ├── MessageContainer.tsx
│   │   ├── StreamingText.tsx
│   │   ├── DebateControls.tsx
│   │   ├── JudgePanelDesktop.tsx
│   │   ├── JudgePanelMobile.tsx
│   │   ├── MetricBar.tsx
│   │   └── CrossReference.tsx
│   │
│   ├── history/
│   │   ├── DebateList.tsx
│   │   ├── DebateCard.tsx
│   │   ├── DebateViewer.tsx
│   │   ├── ReplayControls.tsx
│   │   └── TimelineScrubber.tsx
│   │
│   ├── settings/
│   │   ├── APIKeyManager.tsx
│   │   ├── ProviderKeyInput.tsx
│   │   └── KeyValidation.tsx
│   │
│   └── common/
│       ├── ThemeToggle.tsx
│       ├── ColorLegend.tsx
│       └── ExportDialog.tsx
│
├── hooks/
│   ├── useStreamingText.ts
│   ├── useDebateSSE.ts
│   ├── useKeyboardShortcuts.ts
│   ├── useReducedMotion.ts
│   ├── useCrossReference.ts
│   └── useDebateExport.ts
│
├── lib/
│   ├── api/
│   │   ├── anthropic.ts
│   │   ├── openai.ts
│   │   ├── google.ts
│   │   ├── mistral.ts
│   │   └── unified-client.ts
│   │
│   ├── debate/
│   │   ├── engine.ts
│   │   ├── judge.ts
│   │   ├── personas.ts
│   │   └── formats.ts
│   │
│   ├── export/
│   │   ├── markdown.ts
│   │   ├── json.ts
│   │   └── html.ts
│   │
│   ├── storage/
│   │   ├── api-keys.ts
│   │   └── debate-history.ts
│   │
│   └── utils.ts
│
├── types/
│   ├── debate.ts
│   ├── participant.ts
│   ├── message.ts
│   └── api.ts
│
├── public/
│   ├── avatars/
│   └── ...
│
├── styles/
│   └── animations.css
│
├── tailwind.config.ts
├── tsconfig.json
├── next.config.js
└── package.json
```

---

## 15. Sources & References

### Research Sources

**Multi-Stream Chat UI Patterns:**
- [16 Chat UI Design Patterns That Work in 2025](https://bricxlabs.com/blogs/message-screen-ui-deisgn)
- [Build a Multi-Model AI Chat App with Stream](https://getstream.io/blog/multi-model-ai-chat/)
- [7 UX Best Practices for Livestream Chat](https://getstream.io/blog/7-ux-best-practices-for-livestream-chat/)

**Component Libraries:**
- [Material UI vs Shadcn: UI library war](https://codeparrot.ai/blogs/material-ui-vs-shadcn)
- [Material UI vs. ShadCN UI - Which Should You be using in 2024?](https://blog.openreplay.com/material-ui-vs-shadcn-ui/)
- [React UI libraries in 2025](https://makersden.io/blog/react-ui-libs-2025-comparing-shadcn-radix-mantine-mui-chakra)

**Streaming Animations:**
- [5 ways to implement a typing animation in React](https://blog.logrocket.com/5-ways-implement-typing-animation-react/)
- [Typewriter: Realistic typing animations in React | Motion](https://motion.dev/docs/react-typewriter)
- [Streaming Text Like an LLM with TypeIt](https://macarthur.me/posts/streaming-text-with-typeit/)

**Accessibility:**
- [WCAG Techniques for dynamic content](https://www.w3.org/WAI/GL/wiki/WCAG_Techniques_for_dynamic_content)
- [Web Content Accessibility Guidelines (WCAG) 2.2](https://www.w3.org/TR/WCAG22/)
- [Provide notification of dynamic changes to content](https://accessibility.huit.harvard.edu/provide-notification-dynamic-changes-content)

**Responsive Design:**
- [Responsive and animated Chat UI with CSS Grid](https://catalincodes.com/posts/responsive-chat-with-css-grid)
- [Tailwind CSS Multi-Column Layouts](https://tailwindcss.com/plus/ui-blocks/application-ui/application-shells/multi-column)
- [Material Design Responsive UI](https://m1.material.io/layout/responsive-ui.html)

**Streaming Implementation:**
- [Using Server-Sent Events (SSE) to stream LLM responses in Next.js](https://upstash.com/blog/sse-streaming-llm-responses)
- [Streaming AI Responses with WebSockets, SSE, and gRPC](https://medium.com/@pranavprakash4777/streaming-ai-responses-with-websockets-sse-and-grpc-which-one-wins-a481cab403d3)
- [React WebSocket tutorial](https://blog.logrocket.com/websocket-tutorial-socket-io/)

**Color Coding:**
- [UI/UX Best Practices for Chat App Design](https://www.cometchat.com/blog/chat-app-design-best-practices)
- [Importance of Color Code Concepts in UI/UX Design](https://www.geeksforgeeks.org/websites-apps/importance-of-color-code-concepts-in-ui-ux-design/)

**Export Patterns:**
- [How to Export Your ChatGPT Conversation History](https://medium.com/@yjg30737/how-to-export-your-chatgpt-conversation-history-caa0946d6329)
- [Conversation history | Conversational Agents | Google Cloud](https://cloud.google.com/dialogflow/cx/docs/concept/conversation-history)

---

## Conclusion

This UI/UX specification provides a comprehensive blueprint for building Quorum's real-time debate interface. The recommended architecture prioritizes:

1. **Flexibility** - shadcn/ui enables unlimited customization
2. **Performance** - SSE streaming, virtual scrolling, code splitting
3. **Accessibility** - WCAG 2.2 AA compliance with ARIA live regions
4. **Responsiveness** - Mobile-first design with thoughtful breakpoints
5. **User Experience** - Intuitive flows, clear visual hierarchy, engaging animations

The modular component structure allows for iterative development, starting with core functionality and progressively enhancing with advanced features. By following these patterns and leveraging modern React/Next.js best practices, Quorum will deliver a compelling, accessible, and performant debate experience.

**Next Steps:**
1. Review and approve this specification
2. Set up development environment
3. Begin Phase 1 implementation
4. Iterate based on user testing and feedback

---

**Document Version:** 1.0
**Last Updated:** 2024-01-15
**Author:** UI/UX Architect (Claude Code Research Agent)