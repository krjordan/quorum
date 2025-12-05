# MVP Scope: Interactive Conversation Platform

**Status:** Phase 3 - In Planning
**Timeline:** 4-6 weeks
**Goal:** Transform from debate platform to interactive conversation platform

---

## 🎯 MVP Vision

Build a multi-agent AI conversation platform where users can naturally participate in intelligent discussions with 3-5 specialized AI agents that:
- **Maintain conversation quality** (no contradictions, no loops)
- **Remember context** across sessions (get smarter over time)
- **Work for everyone** (zero technical knowledge required)

---

## ✅ What's In Scope (MVP)

### **1. Conversation Quality Management** 🏆

**Why:** Solves the #1 frustration in existing platforms

#### Core Features:
1. **Anti-Contradiction Engine**
   - Detect when agents make conflicting statements
   - Flag contradictions to user in real-time
   - Force agents to reconcile differences
   - Confidence scoring (how sure is each agent?)

2. **Loop Detection & Breaking**
   - Identify when conversation is going in circles
   - Auto-intervene after 2-3 repetitive turns
   - Inject fresh context to break the loop
   - Protect user from wasting tokens/money

3. **Conversation Health Score**
   - Real-time quality indicator (0-100)
   - Factors: coherence, progress, productivity
   - Visual indicator in UI (green/yellow/red)
   - Recommendations when quality drops

4. **Evidence Grounding (Basic)**
   - Agents cite sources for factual claims
   - Citation format: [Source: URL/reference]
   - Track citations in conversation
   - Warning when agents make unsupported claims

#### Success Metrics:
- Contradiction rate: <5%
- Loop rate: <2%
- Average health score: >75/100
- User satisfaction with conversation quality: >4/5

---

### **2. Intelligent Memory Architecture** 🧠

**Why:** Creates compound value and user lock-in

#### Core Features:
1. **Three-Tier Memory System**
   - **Short-term:** Current conversation (full context)
   - **Medium-term:** Recent conversations (summarized, last 7 days)
   - **Long-term:** Historical knowledge (indexed, >7 days)

2. **Automatic Context Retrieval**
   - Detect when past conversations are relevant
   - Surface related discussions automatically
   - "We talked about this before..." references
   - Show source conversation link

3. **Basic Personalization**
   - Track user's preferred communication style
   - Remember domain expertise level
   - Adapt agent formality based on history
   - Store custom terminology/definitions

4. **Memory Dashboard (Basic)**
   - View recent conversation history
   - Search past conversations (text search)
   - Delete conversations
   - Export conversation as Markdown

#### Success Metrics:
- Context recall accuracy: >80%
- Relevant context surfaced: >60% of conversations
- User reports agents "remember them": >70%
- Week-over-week retention: >40%

---

### **3. Non-Technical User Experience** 🎨

**Why:** Opens to 100x larger non-technical market

#### Core Features:
1. **Zero-Config Start**
   - Land on page → type message → get response
   - Default 3-agent panel auto-selected
   - No account required for first conversation
   - One-click to begin

2. **Agent Personalities (5 Presets)**
   - **The Analyst:** Logical, data-driven, structured
   - **The Creative:** Imaginative, lateral thinking, innovative
   - **The Critic:** Skeptical, devil's advocate, rigorous
   - **The Optimist:** Positive, solution-focused, encouraging
   - **The Mediator:** Balanced, synthesis-focused, diplomatic

3. **Template Library (10 Templates)**
   - "Brainstorm business ideas"
   - "Debug my thinking on [topic]"
   - "Research [subject] comprehensively"
   - "Plan [project] step-by-step"
   - "Analyze pros and cons of [decision]"
   - "Learn about [topic] from scratch"
   - "Get feedback on [idea/plan]"
   - "Solve a problem creatively"
   - "Prepare for [meeting/presentation]"
   - "Make a difficult decision"

4. **Simple Agent Configuration**
   - Select agent personality from dropdown
   - Choose model (GPT-4, Claude, Gemini)
   - Set temperature (slider: focused ↔ creative)
   - Optional: Add custom instructions (textarea)

5. **Interactive Tutorial**
   - 3-step walkthrough on first visit
   - Skip-able at any time
   - Contextual tooltips on hover
   - Example conversation to demonstrate

#### Success Metrics:
- Time to first message: <30 seconds
- Users complete first conversation: >90%
- Users who customize agents: >30%
- User satisfaction with ease of use: >4.5/5

---

## 🚫 What's Out of Scope (MVP)

### Features Deferred to Post-MVP:
- ❌ Voice input/output
- ❌ Real-time WebSocket streaming (stay with SSE for MVP)
- ❌ Multi-user collaboration
- ❌ Advanced voting/consensus mechanisms
- ❌ Argument mapping visualization
- ❌ Mobile apps
- ❌ Enterprise SSO/team features
- ❌ Custom agent marketplace
- ❌ API access for developers
- ❌ Conversation forking/branching
- ❌ Document upload and analysis
- ❌ Semantic search (text search only for MVP)
- ❌ Advanced memory controls (keep it simple)
- ❌ AI moderator role (defer to Phase 4)

### Simplifications for MVP:
- **Memory:** Text search only (not semantic/vector search)
- **Models:** Support top 3 providers only (OpenAI, Anthropic, Google)
- **Agents:** Max 5 agents per conversation (not unlimited)
- **Templates:** 10 pre-built only (no custom template creation)
- **Export:** Markdown only (no PDF/JSON)
- **Sharing:** Copy/paste transcript (no direct sharing features)

---

## 🏗️ Technical Architecture (MVP)

### Backend Changes:
```
Existing:
- FastAPI + LiteLLM
- Redis caching
- Sequential debate system

New:
+ PostgreSQL database (conversation history, memory)
+ Embedding service (basic, for contradiction detection)
+ Memory service (CRUD for conversations)
+ Quality scoring service
+ Simple loop detection (pattern matching)
```

### Frontend Changes:
```
Existing:
- Next.js 15 + React
- Zustand state management
- shadcn/ui components

New:
+ Conversation history panel
+ Agent personality selector
+ Template library UI
+ Health score indicator
+ Memory dashboard page
+ Tutorial/onboarding flow
```

### Database Schema:
```sql
-- Conversations
conversations (
  id, user_id, title, created_at, updated_at, archived
)

-- Messages
messages (
  id, conversation_id, agent_name, role, content,
  citations, cost, tokens, health_score, timestamp
)

-- User preferences
user_preferences (
  user_id, default_agents, communication_style, expertise_level
)

-- Memory summaries
memory_summaries (
  conversation_id, summary, key_points, embedding (defer)
)
```

---

## 📋 Development Phases

### **Week 1-2: Conversation Quality**
- [ ] Database schema design and migration
- [ ] Anti-contradiction detection (embedding similarity)
- [ ] Loop detection (pattern matching)
- [ ] Health scoring algorithm
- [ ] UI indicators for quality issues
- [ ] Citation format standardization
- [ ] Backend tests for quality features

### **Week 3-4: Intelligent Memory**
- [ ] Conversation CRUD operations
- [ ] Automatic summarization of old conversations
- [ ] Context retrieval logic
- [ ] Memory dashboard UI
- [ ] Conversation search (text-based)
- [ ] Export to Markdown
- [ ] Backend tests for memory features

### **Week 5-6: User Experience**
- [ ] Agent personality system
- [ ] Template library implementation
- [ ] Zero-config first experience
- [ ] Interactive tutorial/onboarding
- [ ] Agent configuration UI
- [ ] Polish and refinement
- [ ] End-to-end testing
- [ ] Beta user testing

---

## 🎯 Success Criteria

### Must-Have for MVP Launch:
1. ✅ Users can start conversation with zero configuration
2. ✅ Agents detect and flag contradictions
3. ✅ System prevents costly loops
4. ✅ Conversation history persists across sessions
5. ✅ Agents reference past conversations when relevant
6. ✅ 5 agent personalities work as expected
7. ✅ 10 templates launch conversations effectively
8. ✅ Health score accurately reflects conversation quality
9. ✅ Tutorial guides new users successfully
10. ✅ >90% of test users complete first conversation

### Quality Bar:
- No critical bugs
- <2s average response start time (SSE)
- Mobile responsive (even if not native app)
- Accessible (WCAG AA compliance)
- 90%+ backend test coverage
- 80%+ frontend test coverage

---

## 📊 Key Metrics to Track

### Engagement:
- Time to first message
- Messages per conversation
- Conversations per user per week
- Week-over-week retention

### Quality:
- Contradiction detection rate
- Loop intervention rate
- Average health score
- User satisfaction ratings

### Memory:
- Context retrieval accuracy
- Relevant context surfaced %
- Conversation search usage

### Growth:
- New signups per week
- Activation rate (completed first conversation)
- Referral rate

---

## 🚀 Launch Strategy

### Private Beta (Week 5):
- 50 hand-picked users
- Technical early adopters
- Gather detailed feedback
- Fix critical issues

### Public Beta (Week 6):
- Product Hunt launch
- HackerNews post
- Twitter/social promotion
- 500-1000 users

### Metrics for Go/No-Go:
- <5 critical bugs reported
- >4/5 average user satisfaction
- >40% week 1 retention
- Health score system working reliably

---

## 💡 Open Questions

### Technical:
- Which embedding model for contradiction detection? (OpenAI vs. Anthropic vs. open-source)
- How to handle very long conversations? (summarization strategy)
- Database scaling approach? (single instance vs. sharding)

### Product:
- Default agent combination? (Analyst + Creative + Critic?)
- How prominently to show health score? (always visible vs. on-demand)
- Account required from day 1 or allow anonymous? (lean toward optional account)

### Business:
- Pricing for MVP? (free only vs. introduce paid tier)
- API keys: user provides vs. we subsidize? (we subsidize for MVP)
- Data retention policy? (keep forever vs. auto-delete after N days)

---

## 📝 Notes

### Assumptions:
- Most conversations will be 5-20 messages
- Users will engage 2-3 times per week
- Primary use case is "thinking partner" not "task automation"
- Desktop/web is primary surface (mobile is secondary)

### Constraints:
- 6-week timeline is firm (for funding/team reasons)
- Must ship with quality (no broken MVP)
- Backend must scale to 10K users (not 100K yet)
- Budget: $5K/month in LLM API costs (subsidized)

---

**Last Updated:** December 4, 2024
**Owner:** Product & Engineering
**Status:** Approved for Implementation
