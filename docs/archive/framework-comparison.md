# Quorum Framework Comparison: Next.js vs Angular

**Research Date:** November 29, 2025
**Author:** Frontend Architecture Specialist
**Purpose:** Framework selection for Quorum AI debate platform

---

## Executive Summary

### Recommendation: **Next.js 15 with React**

After comprehensive research and analysis, **Next.js 15 with React** is the recommended framework for Quorum's MVP and long-term development. This recommendation is based on:

1. **Superior SSE/Streaming Support**: Native, first-class support for Server-Sent Events with minimal boilerplate
2. **Simpler State Management**: Lower complexity for managing multiple concurrent LLM streams
3. **Faster Development Velocity**: Reduced learning curve and extensive ecosystem for AI/LLM applications
4. **Strong Community Momentum**: Explosive growth in AI streaming use cases and open-source examples
5. **Better Alignment with MVP Philosophy**: Client-side-first approach with optional thin backend matches MVP requirements

**Confidence Level**: High (8/10)

---

## 1. Technical Capabilities Matrix

| Capability | Next.js 15 + React | Angular 19 | Winner |
|-----------|-------------------|-----------|--------|
| **SSE/Streaming Support** | Native with ReadableStream API, extensive documentation | Manual EventSource implementation, less documented | Next.js |
| **WebSocket Support** | Full support via libraries | Built-in RxJS integration | Tie |
| **TypeScript Support** | Excellent, first-class | Excellent, TypeScript-first | Tie |
| **SSR/SSG** | Industry-leading with streaming SSR | Full hydration support, incremental hydration | Next.js |
| **State Management** | Zustand, React Query, Jotai (minimal boilerplate) | NgRx Signal Store, Signals (more structured) | Next.js |
| **Real-time UI Updates** | React Suspense + streaming | Angular Signals + RxJS | Tie |
| **Developer Experience** | Minimal setup, zero-config routing | Opinionated, steeper learning curve | Next.js |
| **Bundle Size** | Smaller with tree-shaking | Larger initial bundle | Next.js |
| **Build Performance** | Turbopack (10x faster than Webpack) | Improved, but slower than Turbopack | Next.js |

**Score: Next.js 7 | Angular 0 | Tie 3**

---

## 2. Real-Time Streaming Analysis

### Next.js SSE Implementation

**Strengths:**
- **Native Support**: Next.js 15 App Router has built-in SSE support via Route Handlers
- **ReadableStream API**: Clean, modern streaming implementation
- **2025 Momentum**: SSE is experiencing a "glorious comeback" driven by AI/LLM applications
- **Extensive Examples**: Multiple production tutorials for ChatGPT-style streaming interfaces
- **Minimal Boilerplate**: Simple server-side implementation with fetch on client

**Example Implementation:**
```typescript
// app/api/stream/route.ts (Server)
export async function POST(req: Request) {
  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    async start(controller) {
      // Stream LLM responses
      for await (const chunk of llmStream) {
        controller.enqueue(encoder.encode(`data: ${JSON.stringify(chunk)}\n\n`));
      }
      controller.close();
    }
  });

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
    },
  });
}

// Client component
const response = await fetch('/api/stream', { method: 'POST' });
const reader = response.body.getReader();
while (true) {
  const { done, value } = await reader.read();
  if (done) break;
  // Process streaming data
}
```

**Use Case Alignment:**
- Perfect for Quorum's 2-4 concurrent LLM streams
- Widespread adoption in AI applications (every ChatGPT-style app uses SSE)
- Simple unidirectional server-to-client flow matches debate format

### Angular SSE Implementation

**Strengths:**
- **RxJS Integration**: Natural fit with Observable pattern
- **EventSource API**: Browser-native EventSource works well
- **Reactive Patterns**: Signals + RxJS excellent for complex state

**Challenges:**
- **More Boilerplate**: Requires manual EventSource setup and Observable wrapping
- **Less Documentation**: Fewer 2025 examples for multi-stream LLM use cases
- **HTTP Interceptor Limitation**: Cannot intercept SSE with standard HTTP interceptors

**Example Implementation:**
```typescript
// Angular service
export class StreamService {
  createEventSource(url: string): Observable<MessageEvent> {
    return new Observable(observer => {
      const eventSource = new EventSource(url);
      eventSource.onmessage = (event) => observer.next(event);
      eventSource.onerror = (error) => observer.error(error);
      return () => eventSource.close();
    });
  }
}

// Component
this.streamService.createEventSource('/api/stream')
  .pipe(
    map(event => JSON.parse(event.data)),
    takeUntil(this.destroy$)
  )
  .subscribe(data => this.handleStreamData(data));
```

**Use Case Alignment:**
- Good for complex state management across streams
- RxJS operators powerful for stream composition
- More verbose for simple streaming scenarios

### Verdict: Next.js wins for SSE/Streaming

**Reasoning:**
- Lower implementation complexity for MVP
- Better ecosystem alignment with AI/LLM streaming (2025 trend)
- Simpler client-side code
- More production examples to reference

---

## 3. State Management for Multiple Concurrent Streams

### Challenge: Managing 2-4 Simultaneous LLM Streams + Judge

Quorum requires managing:
- 2-4 debater streams (concurrent or sequential)
- 1 judge stream (monitoring quality)
- Conversation history for each participant
- UI state (loading, errors, turn indicators)
- Export state (Markdown/JSON formatting)

### Next.js State Management Ecosystem

#### Recommended Stack: **React Query + Zustand**

**React Query (TanStack Query):**
- **Streaming Support**: Experimental `streamedQuery` API for SSE integration
- **Cache Management**: Automatic caching and invalidation
- **Loading States**: Built-in loading/error states per query
- **Complexity**: Low to Medium

```typescript
// React Query with SSE
const { data, isLoading } = useQuery({
  queryKey: ['debate', debateId],
  queryFn: async () => {
    const response = await fetch('/api/debate/stream');
    const reader = response.body.getReader();
    // Stream handling
  }
});
```

**Zustand for UI State:**
- **Boilerplate**: Minimal (zero actions/reducers needed)
- **Learning Curve**: Very low
- **Performance**: Excellent (selective re-renders)
- **TypeScript**: First-class support

```typescript
// Zustand store
const useDebateStore = create<DebateState>((set) => ({
  debaters: [],
  judgeVerdict: null,
  addMessage: (debaterId, message) =>
    set((state) => ({
      debaters: state.debaters.map(d =>
        d.id === debaterId
          ? { ...d, messages: [...d.messages, message] }
          : d
      )
    }))
}));
```

**Strengths:**
- Minimal boilerplate (major productivity win)
- Easy to understand and maintain
- Great for rapid MVP development
- Strong community support for LLM streaming

**Weaknesses:**
- Less structure (could be issue for large teams)
- Limited built-in features (need custom code for complex logic)

### Angular State Management Ecosystem

#### Recommended Stack: **NgRx Signal Store + RxJS**

**NgRx Signal Store:**
- **Boilerplate**: Low (much improved from traditional NgRx)
- **Learning Curve**: Medium
- **Structure**: More opinionated and structured
- **TypeScript**: Excellent integration

```typescript
// NgRx Signal Store
export const DebateStore = signalStore(
  withState({
    debaters: [],
    judgeVerdict: null
  }),
  withMethods((store) => ({
    addMessage(debaterId: string, message: Message) {
      patchState(store, (state) => ({
        debaters: state.debaters.map(d =>
          d.id === debaterId
            ? { ...d, messages: [...d.messages, message] }
            : d
        )
      }));
    }
  }))
);
```

**RxJS for Streams:**
- **Perfect for SSE**: Observables naturally map to event streams
- **Powerful Operators**: merge, combineLatest, switchMap for complex flows
- **Backpressure Handling**: Built-in support

```typescript
// RxJS stream composition
combineLatest([
  debater1Stream$,
  debater2Stream$,
  judgeStream$
]).pipe(
  map(([d1, d2, judge]) => ({ d1, d2, judge })),
  takeUntil(destroy$)
).subscribe(state => updateUI(state));
```

**Strengths:**
- Excellent structure for large teams
- RxJS perfect for complex async operations
- Strong typing and DI system
- Better for enterprise-scale applications

**Weaknesses:**
- Higher learning curve (RxJS, DI, decorators)
- More boilerplate than Zustand
- Slower initial development velocity

### Verdict: Next.js (Zustand + React Query) for MVP

**Reasoning:**
- Lower complexity = faster MVP delivery
- Adequate for 2-4 concurrent streams
- Easy to refactor if complexity grows
- Better alignment with "client-side first" MVP approach

**Note:** Angular would be preferable for:
- Large, multi-team development
- Complex enterprise requirements
- Heavy emphasis on maintainability over velocity

---

## 4. Performance Considerations

### Next.js 15 Performance

**Streaming SSR:**
- Progressive page rendering with React Suspense
- Faster Time-to-First-Byte (TTFB)
- Smoother user experience during loading
- Case Study: SaaS analytics dashboard saw 60% bundle size reduction and 25% cost drop with RSC

**Build Performance:**
- Turbopack: 10x faster than Webpack for development builds
- React Server Components reduce client bundle size
- Automatic code splitting and lazy loading

**Real-World Metrics:**
- ~51 requests/second in SSR benchmarks (controlled tests)
- Excellent Core Web Vitals scores
- Optimized for streaming AI responses

### Angular 19 Performance

**Incremental Hydration:**
- Selective hydration of components on-demand
- Event replay captures user interactions during hydration
- Reduces unnecessary JavaScript downloads
- Prevents UI flicker on SSR

**Standalone Components:**
- Smaller bundle sizes with tree-shaking
- Faster initial load times
- Modular architecture

**Zoneless Change Detection:**
- Improved runtime performance
- Better for real-time applications
- Reduced overhead

**Challenges:**
- Larger initial bundle size than Next.js
- Slower build times (even with improvements)
- More complex hydration process

### Verdict: Next.js wins for performance

**Key Differentiators:**
- Better streaming performance (critical for Quorum)
- Smaller bundle sizes
- Faster development builds
- Proven performance in AI/LLM applications

---

## 5. Developer Experience Trade-offs

### Next.js Developer Experience

**Strengths:**
- **Zero-Config Routing**: File-based routing (no setup needed)
- **Learning Curve**: Low (especially for React developers)
- **Development Speed**: Prototype in hours, not days
- **TypeScript**: Excellent integration, but not mandatory
- **Tooling**: Hot reload, Fast Refresh, excellent DevTools
- **Flexibility**: Less opinionated = more freedom

**Weaknesses:**
- **Less Structure**: Can lead to inconsistency in large teams
- **Decision Fatigue**: Must choose state management, styling, etc.
- **Breaking Changes**: Faster release cycle = more migration work

**Best For:**
- Small to medium teams
- Rapid prototyping and MVPs
- Content-heavy sites with SEO needs
- AI/LLM streaming applications

### Angular Developer Experience

**Strengths:**
- **All-in-One Framework**: Router, forms, HTTP, DI built-in
- **Opinionated Structure**: Clear patterns for team consistency
- **TypeScript-First**: Mandatory TypeScript = better type safety
- **CLI & Schematics**: Powerful code generation
- **Long-Term Stability**: Slower release cycle, clear migration paths
- **Enterprise-Ready**: Scales well across large teams

**Weaknesses:**
- **Steep Learning Curve**: RxJS, decorators, DI, zones
- **More Verbose**: More boilerplate than React
- **Slower Initial Development**: Setup and learning overhead
- **Less Flexibility**: Opinionated = less freedom

**Best For:**
- Large, multi-team organizations
- Enterprise applications
- Long-term maintainability focus
- Complex state management needs

### Verdict: Next.js for Quorum's MVP

**Reasoning:**
- Quorum is MVP-focused with rapid iteration needs
- Small team (initially) benefits from lower learning curve
- Client-side-first approach aligns with Next.js flexibility
- Can always migrate to Angular later if complexity demands it

---

## 6. Community & Ecosystem Maturity

### Next.js & React Ecosystem (2025)

**Community Size:**
- React: 207,000+ GitHub stars
- React: 20+ million weekly npm downloads
- 40%+ of professional developers use React
- 36.6% of developers want to learn React

**Open Source Activity:**
- Massive ecosystem of Next.js open-source projects
- Active community sharing ChatGPT-style streaming examples
- Vercel's strong investment in framework development
- Next.js 16 released (October 2025) with Build Adapters API

**AI/LLM Ecosystem:**
- Extensive tutorials for SSE streaming with LLMs
- Production-ready examples from Upstash, Vercel, community
- Multiple state management libraries optimized for streaming
- Strong momentum in 2025 for AI applications

**Strengths:**
- Largest JavaScript ecosystem
- Fastest innovation cycle
- Best resources for AI/LLM streaming
- Most job opportunities

### Angular Ecosystem (2025)

**Community Size:**
- Angular: Active but smaller than React
- Used by large enterprises (Google, Microsoft, etc.)
- Strong in enterprise and government sectors

**Open Source Activity:**
- Angular v21 released (November 2025)
- 215 contributors since v20
- Active community projects: PeerTube (13.4k stars), Openproject (9.7k stars)
- Strong contribution guidelines and "good first issue" labels

**Tooling & Libraries:**
- Ngxtension utilities library (community-driven)
- Web Codegen Scorer open-sourced by Angular team
- Comprehensive built-in tooling

**Strengths:**
- Strong enterprise support
- Long-term stability
- Excellent documentation
- Great for large-scale applications

### Verdict: Next.js has stronger ecosystem for Quorum

**Reasoning:**
- Larger community = more resources and help
- Better AI/LLM streaming examples (critical for Quorum)
- Faster innovation cycle aligns with startup needs
- Open-source nature encourages community contributions

---

## 7. SSR/SSG Needs for Debate Features

### Quorum's SSR/SSG Requirements

**Potential Use Cases:**
- Sharing debate links with preview cards (Open Graph)
- SEO for public debates
- Debate replay functionality
- Export to static HTML for archival

### Next.js SSR/SSG Capabilities

**Strengths:**
- Industry-leading SSR with streaming
- Incremental Static Regeneration (ISR)
- On-demand revalidation
- Automatic static optimization
- Excellent for shareable content

**Implementation:**
```typescript
// Static debate replay page
export async function generateStaticParams() {
  const debates = await getDebates();
  return debates.map(d => ({ id: d.id }));
}

export default async function DebatePage({ params }) {
  const debate = await getDebate(params.id);
  return <DebateReplay debate={debate} />;
}
```

**Benefits for Quorum:**
- Easy debate sharing with rich previews
- Fast page loads for replay viewing
- SEO-friendly public debates
- Zero-config setup

### Angular SSR/SSG Capabilities

**Strengths:**
- Full SSR support with Angular Universal
- Incremental hydration (new in v19)
- Event replay during hydration
- Prevents UI flicker

**Implementation:**
```typescript
// Angular Universal setup (more configuration needed)
import { APP_ID, Inject, PLATFORM_ID } from '@angular/core';
import { isPlatformBrowser } from '@angular/common';

export class DebateComponent {
  constructor(
    @Inject(PLATFORM_ID) private platformId: Object
  ) {}

  ngOnInit() {
    if (isPlatformBrowser(this.platformId)) {
      // Client-only code
    }
  }
}
```

**Challenges:**
- More setup complexity
- Requires Angular Universal configuration
- More complex than Next.js

### Verdict: Next.js for SSR/SSG

**Reasoning:**
- Zero-config SSR/SSG
- Better for shareable content
- Simpler implementation
- Industry-leading performance

---

## 8. Risk Assessment

### Next.js Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Breaking changes in future versions | Medium | Pin versions, gradual upgrades, follow changelog |
| Vercel vendor lock-in | Low | Next.js is open-source, can deploy anywhere |
| Less structure may lead to technical debt | Medium | Establish coding standards early, use linting |
| React's frequent API changes | Medium | Use stable patterns, avoid experimental features |

### Angular Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Steeper learning curve slows MVP | High | Invest in training, hire experienced devs |
| Smaller pool of Angular developers | Medium | Plan for longer hiring times |
| Overkill for MVP scope | Medium | Accept initial complexity for long-term benefits |
| Slower development velocity | Medium | Use CLI generators, leverage opinionated patterns |

### Overall Risk Winner: Next.js

Next.js presents lower risks for MVP development, with mitigation strategies that are easier to implement.

---

## 9. Final Recommendation

### Choose Next.js 15 + React for Quorum

**Primary Reasons:**

1. **SSE/Streaming Excellence**: Native support for Server-Sent Events with extensive AI/LLM examples
2. **Faster MVP Development**: Lower learning curve and minimal boilerplate accelerate delivery
3. **Superior Ecosystem for AI Apps**: 2025 momentum in LLM streaming, extensive community resources
4. **Better Performance**: Smaller bundles, faster builds, optimized for streaming
5. **Alignment with MVP Philosophy**: Client-side-first approach, optional thin backend
6. **Open Source Appeal**: Larger community encourages contributions and engagement

**Recommended Tech Stack:**

```
Frontend Framework: Next.js 15 (App Router)
UI Library: React 19
State Management: Zustand (UI state) + React Query (server state)
Streaming: Server-Sent Events (SSE) via Route Handlers
TypeScript: Yes (strict mode)
Styling: Tailwind CSS (rapid development)
API Abstraction: Custom layer over LLM providers
Export: Markdown/JSON utilities
```

### When to Reconsider Angular

Consider switching to Angular if:
- Team grows beyond 10+ developers
- Multiple product teams need strict consistency
- Enterprise customers demand Angular
- Complexity exceeds MVP scope significantly
- Need for comprehensive built-in tooling becomes critical

### Implementation Roadmap

**Phase 1: MVP (Weeks 1-4)**
- Set up Next.js 15 with App Router
- Implement SSE streaming for single LLM
- Build basic UI with Zustand state management
- Create API abstraction layer

**Phase 2: Multi-Stream Support (Weeks 5-8)**
- Add support for 2-4 concurrent debater streams
- Implement judge monitoring stream
- Build React Query integration for caching
- Add export functionality

**Phase 3: Enhancement (Weeks 9-12)**
- Implement debate replay with SSG
- Add social sharing with Open Graph
- Optimize performance and bundle size
- Gather user feedback for iteration

---

## 10. Sources & References

### Next.js & SSE Streaming
- [Streaming in Next.js 15: WebSockets vs Server-Sent Events | HackerNoon](https://hackernoon.com/streaming-in-nextjs-15-websockets-vs-server-sent-events)
- [Using Server-Sent Events (SSE) to stream LLM responses in Next.js | Upstash Blog](https://upstash.com/blog/sse-streaming-llm-responses)
- [Real-Time Updates with Server-Sent Events (SSE) in Next.js 15 - Damian Hodgkiss](https://damianhodgkiss.com/tutorials/real-time-updates-sse-nextjs)
- [SSE's Glorious Comeback: Why 2025 is the Year of Server-Sent Events - portalZINE NMN](https://portalzine.de/sses-glorious-comeback-why-2025-is-the-year-of-server-sent-events/)

### Angular Streaming & Real-Time
- [Real-Time Communication in Angular: SSE vs WebSocket](https://aptuz.com/blog/a-dive-into-sse-and-web-sockets-in-angular/)
- [Streaming Resources for a Chat with Web Sockets - ANGULARarchitects](https://www.angulararchitects.io/blog/streaming-resources-for-a-chat-with-web-sockets-messages-in-a-glitch-free-world/)
- [WebSocket in Angular & How to Build Real-Time Applications](https://angulargems.beehiiv.com/p/web-sockets-in-angular)

### State Management
- [React Query and Server Side Events - Fragmented Thought](https://fragmentedthought.com/blog/2025/react-query-caching-with-server-side-events)
- [TanStack Query - streamedQuery](https://tanstack.com/query/latest/docs/reference/streamedQuery)
- [Angular State Management for 2025 | Nx Blog](https://nx.dev/blog/angular-state-management-2025)
- [NgRx vs Signal Store: Which One Should You Use in 2025? | Stackademic](https://blog.stackademic.com/ngrx-vs-signal-store-which-one-should-you-use-in-2025-d7c9c774b09d)
- [Mastering State Management with Zustand in Next.js and React - DEV Community](https://dev.to/mrsupercraft/mastering-state-management-with-zustand-in-nextjs-and-react-1g26)

### Framework Comparisons
- [Next.js Vs Angular In 2025: How To Choose With Real Data - DEV Community](https://dev.to/pullflow/nextjs-vs-angular-in-2025-how-to-choose-with-real-data-1odm)
- [Next.js vs Angular: Complete Framework Comparison Guide 2025 - Criztec Technologies](https://criztec.com/nextjs-vs-angular)

### Performance & Features
- [Next.js Streaming Explained: Faster Rendering vs CSR & SSR | u11d](https://u11d.com/blog/nextjs-streaming-vs-csr-vs-ssr/)
- [React & Next.js in 2025 - Modern Best Practices](https://strapi.io/blog/react-and-nextjs-in-2025-modern-best-practices)
- [Angular 19 Hydration Documentation](https://angular.dev/guide/hydration)
- [Latest Angular 19 Enhancements](https://www.grazitti.com/blog/from-performance-gains-to-developer-friendly-features-all-about-angular-19/)

### LLM Streaming Implementation
- [Optimizing Frontend for AI Integration: Best Practices for Consuming LLM-Powered APIs in Angular/React | Medium](https://medium.com/@prashantraghav9649/optimizing-frontend-for-ai-integration-best-practices-for-consuming-llm-powered-apis-in-afb8c3eb516e)
- [Consuming Streamed LLM Responses on the Frontend: A Deep Dive into SSE and Fetch](https://tpiros.dev/blog/streaming-llm-responses-a-deep-dive/)

### Community & Ecosystem
- [The Future of React: Top Trends Shaping Frontend Development in 2025](https://www.netguru.com/blog/react-js-trends)
- [Next.js GitHub Repository](https://github.com/vercel/next.js)
- [Announcing Angular v21 | Angular Blog](https://blog.angular.dev/announcing-angular-v21-57946c34f14b)
- [New Open Source Tool from Angular Scores Vibe Code Quality - The New Stack](https://thenewstack.io/new-open-source-tool-from-angular-scores-vibe-code-quality/)

---

## Appendix: Code Examples

### Example: Managing 4 Concurrent LLM Streams in Next.js

```typescript
// app/api/debate/route.ts
import { OpenAI } from 'openai';
import Anthropic from '@anthropic-ai/sdk';

export async function POST(req: Request) {
  const { topic, debaters } = await req.json();

  const encoder = new TextEncoder();
  const stream = new ReadableStream({
    async start(controller) {
      // Create concurrent streams for all debaters
      const streams = debaters.map(async (debater) => {
        const client = createLLMClient(debater.provider);
        const stream = await client.streamResponse({
          prompt: debater.prompt,
          model: debater.model
        });

        for await (const chunk of stream) {
          const message = {
            debaterId: debater.id,
            content: chunk.content,
            timestamp: Date.now()
          };
          controller.enqueue(
            encoder.encode(`data: ${JSON.stringify(message)}\n\n`)
          );
        }
      });

      await Promise.all(streams);
      controller.close();
    }
  });

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
    },
  });
}

// components/DebateInterface.tsx
'use client';

import { useEffect, useState } from 'react';
import { useDebateStore } from '@/stores/debate';

export function DebateInterface({ debateId }: { debateId: string }) {
  const { debaters, addMessage } = useDebateStore();
  const [isStreaming, setIsStreaming] = useState(false);

  useEffect(() => {
    const startDebate = async () => {
      setIsStreaming(true);
      const response = await fetch('/api/debate', {
        method: 'POST',
        body: JSON.stringify({ debateId }),
      });

      const reader = response.body!.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const text = decoder.decode(value);
        const lines = text.split('\n').filter(line => line.startsWith('data:'));

        for (const line of lines) {
          const data = JSON.parse(line.slice(5));
          addMessage(data.debaterId, data.content);
        }
      }

      setIsStreaming(false);
    };

    startDebate();
  }, [debateId]);

  return (
    <div className="debate-container">
      {debaters.map(debater => (
        <DebaterPanel key={debater.id} debater={debater} />
      ))}
      {isStreaming && <LoadingIndicator />}
    </div>
  );
}

// stores/debate.ts (Zustand)
import { create } from 'zustand';

interface Message {
  content: string;
  timestamp: number;
}

interface Debater {
  id: string;
  name: string;
  messages: Message[];
  color: string;
}

interface DebateState {
  debaters: Debater[];
  judgeVerdict: string | null;
  addMessage: (debaterId: string, content: string) => void;
  setJudgeVerdict: (verdict: string) => void;
}

export const useDebateStore = create<DebateState>((set) => ({
  debaters: [],
  judgeVerdict: null,

  addMessage: (debaterId, content) =>
    set((state) => ({
      debaters: state.debaters.map((d) =>
        d.id === debaterId
          ? {
              ...d,
              messages: [
                ...d.messages,
                { content, timestamp: Date.now() }
              ],
            }
          : d
      ),
    })),

  setJudgeVerdict: (verdict) => set({ judgeVerdict: verdict }),
}));
```

### Example: Managing 4 Concurrent LLM Streams in Angular

```typescript
// services/debate-stream.service.ts
import { Injectable } from '@angular/core';
import { Observable, merge } from 'rxjs';
import { map, shareReplay } from 'rxjs/operators';

interface StreamMessage {
  debaterId: string;
  content: string;
  timestamp: number;
}

@Injectable({ providedIn: 'root' })
export class DebateStreamService {
  createDebateStream(debaters: Debater[]): Observable<StreamMessage> {
    const streams = debaters.map(debater =>
      this.createEventSource(`/api/debate/${debater.id}`).pipe(
        map(event => ({
          debaterId: debater.id,
          content: JSON.parse(event.data).content,
          timestamp: Date.now()
        }))
      )
    );

    return merge(...streams).pipe(shareReplay(1));
  }

  private createEventSource(url: string): Observable<MessageEvent> {
    return new Observable(observer => {
      const eventSource = new EventSource(url);

      eventSource.onmessage = (event) => observer.next(event);
      eventSource.onerror = (error) => observer.error(error);

      return () => eventSource.close();
    });
  }
}

// stores/debate.store.ts (NgRx Signal Store)
import { signalStore, withState, withMethods, patchState } from '@ngrx/signals';

interface Message {
  content: string;
  timestamp: number;
}

interface Debater {
  id: string;
  name: string;
  messages: Message[];
  color: string;
}

interface DebateState {
  debaters: Debater[];
  judgeVerdict: string | null;
  isStreaming: boolean;
}

export const DebateStore = signalStore(
  { providedIn: 'root' },
  withState<DebateState>({
    debaters: [],
    judgeVerdict: null,
    isStreaming: false
  }),
  withMethods((store) => ({
    addMessage(debaterId: string, content: string) {
      patchState(store, (state) => ({
        debaters: state.debaters.map(d =>
          d.id === debaterId
            ? {
                ...d,
                messages: [
                  ...d.messages,
                  { content, timestamp: Date.now() }
                ]
              }
            : d
        )
      }));
    },
    setJudgeVerdict(verdict: string) {
      patchState(store, { judgeVerdict: verdict });
    },
    setStreaming(isStreaming: boolean) {
      patchState(store, { isStreaming });
    }
  }))
);

// components/debate-interface.component.ts
import { Component, OnInit, OnDestroy, inject } from '@angular/core';
import { Subject } from 'rxjs';
import { takeUntil } from 'rxjs/operators';
import { DebateStreamService } from '../services/debate-stream.service';
import { DebateStore } from '../stores/debate.store';

@Component({
  selector: 'app-debate-interface',
  standalone: true,
  template: `
    <div class="debate-container">
      @for (debater of store.debaters(); track debater.id) {
        <app-debater-panel [debater]="debater" />
      }
      @if (store.isStreaming()) {
        <app-loading-indicator />
      }
    </div>
  `
})
export class DebateInterfaceComponent implements OnInit, OnDestroy {
  private streamService = inject(DebateStreamService);
  protected store = inject(DebateStore);
  private destroy$ = new Subject<void>();

  ngOnInit() {
    this.store.setStreaming(true);

    this.streamService
      .createDebateStream(this.store.debaters())
      .pipe(takeUntil(this.destroy$))
      .subscribe({
        next: (message) => {
          this.store.addMessage(message.debaterId, message.content);
        },
        error: (error) => {
          console.error('Stream error:', error);
          this.store.setStreaming(false);
        },
        complete: () => {
          this.store.setStreaming(false);
        }
      });
  }

  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
  }
}
```

---

**End of Framework Comparison Document**

*This document should be treated as a living document and updated as new information becomes available or project requirements change.*
