# Documentation Archive

This directory contains research, analysis, and decision documents that led to the current Quorum architecture. These files are preserved for historical context and reference but are not part of the active documentation.

---

## Contents

### Framework & Tech Stack Research

**Frontend Framework Research:**
- `framework-comparison.md` - Comparison of React, Vue, and Svelte for Quorum
- `frontend-framework-research-analysis.md` - Detailed analysis of frontend framework options
- **Decision:** Next.js 15 with React 19 (see [TECH_STACK_CONSENSUS.md](../TECH_STACK_CONSENSUS.md))

**Backend Language Research:**
- `backend-language-comparison.md` - Comparison of Python, Node.js, and Go
- `backend-research-deep-dive.md` - Deep dive into backend architecture decisions
- **Decision:** FastAPI (Python) with LiteLLM (see [TECH_STACK_CONSENSUS.md](../TECH_STACK_CONSENSUS.md))

---

### State Management Research

**Research Documents:**
- `STATE_MANAGEMENT_README.md` - State management overview and options
- `state-architecture-diagrams.md` - Visual diagrams of state architecture
- `state-implementation-guide.md` - Implementation guide for state management
- `state-management-decisions.md` - Decision rationale for state management approach

**Decision:** Zustand for Phase 1, Zustand + XState for Phase 2+ (see [state-management-specification.md](../state-management-specification.md))

---

### Phase 1 Research

- `phase1-research-findings.md` - Research findings and recommendations for Phase 1 implementation
- **Outcome:** See [PHASE1_COMPLETE.md](../PHASE1_COMPLETE.md) for implementation results

---

### Analysis & Summaries

**Coordination Summaries:**
- `HIVE_MIND_SUMMARY.md` - Summary of Hive Mind swarm coordination used during development
- `ARCHITECTURE_UPDATE_SUMMARY.md` - Architecture update summaries

**Technical Analysis:**
- `STREAMING_ANALYSIS.md` - In-depth analysis of SSE streaming implementation options
- `ANALYSIS_SUMMARY.md` - Overall project analysis summary

---

## Why These Files Are Archived

These documents served their purpose in:
1. **Researching** technology options
2. **Analyzing** architectural approaches
3. **Making** informed decisions
4. **Documenting** the decision-making process

The **outcomes** of this research are captured in the main documentation:
- [TECH_STACK_CONSENSUS.md](../TECH_STACK_CONSENSUS.md) - Final tech decisions
- [PHASE1_COMPLETE.md](../PHASE1_COMPLETE.md) - Implementation results
- [state-management-specification.md](../state-management-specification.md) - State management approach

---

## Using Archived Documentation

**When to reference these files:**
- Understanding **why** specific technology choices were made
- Reviewing **alternative approaches** that were considered
- Learning from **research methodology** used in the project
- **Onboarding** new team members who want full context

**When NOT to reference these files:**
- For current implementation details (use main docs)
- For setup instructions (use [SETUP.md](../SETUP.md))
- For API specifications (use [api-integration-spec.md](../api-integration-spec.md))

---

**Note:** These files are preserved for historical reference and should not be updated. Current documentation lives in the main [docs/](../) directory.
