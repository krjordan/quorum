# Phase 2: Multi-LLM Debate Engine - Quick Reference

## 🚀 Quick Start

### Access the Debate Interface
```
http://localhost:3000/debate
```

### Development Commands
```bash
# Install dependencies (if needed)
cd frontend && npm install

# Run development server
npm run dev

# Build for production
npm run build

# Run production server
npm start

# Run tests
npm test
```

## 📁 File Structure

```
frontend/src/
├── app/
│   └── debate/
│       └── page.tsx          # Main debate page route
│
├── components/
│   ├── debate/
│   │   ├── DebateConfigPanel.tsx    # Configuration UI
│   │   ├── DebateArena.tsx          # Multi-participant display
│   │   └── CostTracker.tsx          # Cost monitoring
│   └── ui/
│       ├── select.tsx        # shadcn/ui components
│       ├── dialog.tsx
│       ├── alert.tsx
│       └── progress.tsx
│
├── stores/
│   └── debate-store.ts       # Zustand state management
│
├── hooks/
│   └── useParallelStreaming.ts      # Multi-SSE hook
│
├── lib/
│   └── debate/
│       └── models.ts         # LLM model definitions
│
└── types/
    └── debate.ts             # TypeScript interfaces
```

## 🎯 Key Components

### DebateConfigPanel
**Purpose:** Configure debate settings
**Props:** None (uses store)
**Features:**
- Topic input
- 2-4 participant selection
- Model selection per participant
- Persona customization
- Format selection
- Judge model selection

### DebateArena
**Purpose:** Display real-time debate
**Props:** None (uses store)
**Features:**
- Multi-column grid layout
- Streaming text display
- Token count badges
- Judge verdict panels
- Round progress tracking

### CostTracker
**Purpose:** Monitor debate costs
**Props:** None (uses store)
**Features:**
- Real-time cost display
- Warning thresholds ($0.50, $1.00, $2.00)
- Per-participant breakdown
- Confirmation dialogs

## 🔧 Store Actions

### Configuration
```typescript
import { useDebateStore } from '@/stores/debate-store';

const { setConfig, startDebate } = useDebateStore();

// Set configuration
setConfig({
  topic: "Should AI be regulated?",
  participants: [...],
  format: "free-form",
  judgeModel: {...},
  autoAssignPersonas: true
});

// Start debate
await startDebate();
```

### Controls
```typescript
const {
  pauseDebate,
  resumeDebate,
  stopDebate,
  resetDebate
} = useDebateStore();

pauseDebate();   // Pause ongoing debate
resumeDebate();  // Resume paused debate
stopDebate();    // Stop and complete debate
resetDebate();   // Reset to configuration state
```

### Streaming
```typescript
const { updateStream, completeStream } = useDebateStore();

// Update streaming text
updateStream(participantId, text, tokens, cost);

// Complete a stream
completeStream(participantId);
```

### Export
```typescript
const { exportDebate } = useDebateStore();

// Export as markdown
const markdown = exportDebate("markdown");

// Export as JSON
const json = exportDebate("json");
```

## 🎨 Available Models

### Anthropic
- Claude 3.5 Sonnet ($0.003/1K tokens)
- Claude 3.5 Haiku ($0.001/1K tokens)
- Claude 3 Opus ($0.015/1K tokens)

### OpenAI
- GPT-4 Turbo ($0.01/1K tokens)
- GPT-4 ($0.03/1K tokens)
- GPT-3.5 Turbo ($0.002/1K tokens)

### Google
- Gemini Pro ($0.0005/1K tokens)
- Gemini Pro Vision ($0.002/1K tokens)

### Meta
- Llama 3 70B ($0.0009/1K tokens)
- Llama 3 8B ($0.0002/1K tokens)

## 📊 Debate Formats

### Free-form
- Unlimited rounds
- No structure
- Manual stop
- Best for: Open discussions

### Structured
- Opening → Rebuttal → Closing
- 3 fixed rounds
- Formal structure
- Best for: Traditional debates

### Round-limited
- Fixed number of rounds (1-10)
- User-defined limit
- Best for: Controlled length

### Convergence
- Continues until consensus
- Judge determines convergence
- Automatic termination
- Best for: Resolution seeking

## 💰 Cost Thresholds

```typescript
const COST_THRESHOLDS = {
  WARNING: 0.50,   // Yellow warning
  HIGH: 1.00,      // Red alert + dialog
  CRITICAL: 2.00   // Force stop + override required
};
```

## 🔄 Parallel Streaming Hook

```typescript
import { useParallelStreaming } from '@/hooks/useParallelStreaming';

const {
  streams,           // Map<string, string>
  isStreaming,       // boolean
  errors,            // Map<string, Error>
  completedStreams,  // Set<string>
  startStreaming,    // (configs) => Promise<void>
  stopStreaming,     // () => void
  reset              // () => void
} = useParallelStreaming({
  onStreamUpdate: (participantId, text) => { ... },
  onStreamComplete: (participantId) => { ... },
  onStreamError: (participantId, error) => { ... },
  onAllComplete: () => { ... },
  bufferDelay: 50    // ms
});

// Start multiple streams
await startStreaming([
  { participantId: "p1", endpoint: "/api/stream/p1", ... },
  { participantId: "p2", endpoint: "/api/stream/p2", ... },
]);
```

## 🎭 State Machine

```
CONFIGURING → (startDebate) → RUNNING
                                  ↓
                            (pauseDebate)
                                  ↓
                              PAUSED
                                  ↓
                            (resumeDebate)
                                  ↓
                              RUNNING
                                  ↓
                (stopDebate / round limit / convergence)
                                  ↓
                              COMPLETED
                                  ↓
                            (resetDebate)
                                  ↓
                            CONFIGURING
```

## 🎨 Participant Colors

```typescript
const PARTICIPANT_COLORS = [
  "#3b82f6", // blue
  "#ef4444", // red
  "#10b981", // green
  "#f59e0b", // amber
  "#8b5cf6", // purple (if needed)
  "#ec4899", // pink (if needed)
];
```

## 📝 Default Personas

```typescript
const DEFAULT_PERSONAS = {
  pro: "Advocate supporting the proposition...",
  con: "Skeptic challenging the proposition...",
  neutral: "Balanced analyst examining both perspectives...",
  expert: "Domain expert providing specialized knowledge..."
};
```

## 🐛 Common Issues

### Build Errors
```bash
# Clear cache and rebuild
rm -rf .next
npm run build
```

### Type Errors
```bash
# Reinstall dependencies
rm -rf node_modules
npm install
```

### Missing Components
```bash
# Install Radix UI dependencies
npm install @radix-ui/react-select @radix-ui/react-dialog @radix-ui/react-progress
```

## 🔗 Integration Points (Backend TODO)

### Required Backend Endpoints

#### Start Debate Stream
```
POST /api/debate/stream
Body: {
  participantId: string,
  roundNumber: number,
  topic: string,
  context: string,
  model: string,
  persona: string
}
Response: SSE stream
```

#### Judge Verdict
```
POST /api/debate/judge
Body: {
  topic: string,
  responses: DebateResponse[],
  roundNumber: number
}
Response: {
  winner?: string,
  reasoning: string,
  consensus: boolean,
  confidence: number
}
```

## 📚 TypeScript Interfaces

### DebateConfig
```typescript
interface DebateConfig {
  topic: string;
  participants: Participant[];
  format: DebateFormat;
  judgeModel?: LLMModel;
  maxRounds?: number;
  convergenceThreshold?: number;
  autoAssignPersonas: boolean;
}
```

### Participant
```typescript
interface Participant {
  id: string;
  model: LLMModel;
  persona: string;
  color: string;
  position?: string;
}
```

### DebateRound
```typescript
interface DebateRound {
  number: number;
  responses: DebateResponse[];
  verdict?: JudgeVerdict;
  completed: boolean;
}
```

## 🧪 Testing Checklist

- [ ] Configuration panel loads
- [ ] Participant addition/removal works
- [ ] Model selection updates correctly
- [ ] Start button triggers state change
- [ ] Debate arena displays correctly
- [ ] Cost tracker shows warnings
- [ ] Export generates files
- [ ] Reset returns to configuration

## 📦 Dependencies

```json
{
  "dependencies": {
    "zustand": "^5.0.1",
    "immer": "^11.0.1",
    "@radix-ui/react-select": "^1.x",
    "@radix-ui/react-dialog": "^1.x",
    "@radix-ui/react-progress": "^1.x"
  }
}
```

## 🎓 Learning Resources

- [Zustand Docs](https://zustand-demo.pmnd.rs/)
- [Immer Patterns](https://immerjs.github.io/immer/)
- [Radix UI](https://www.radix-ui.com/)
- [Next.js 15](https://nextjs.org/docs)
- [React 19](https://react.dev/)

---

**Last Updated:** December 2, 2025
**Phase:** 2 (Multi-LLM Debate Engine)
**Status:** ✓ Complete
