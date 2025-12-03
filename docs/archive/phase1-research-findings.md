# Phase 1 Project Structure Research - Quorum

**Research Date:** November 30, 2025
**Agent:** Researcher (Hive Mind Swarm)
**Objective:** Design optimal project structure for Next.js 15 + FastAPI + Docker Compose

---

## Executive Summary

Based on comprehensive research of 2025 best practices, I recommend a **monorepo structure** with clear separation of concerns, featuring:

- Next.js 15 frontend with App Router and TypeScript strict mode
- FastAPI backend with modular architecture
- Docker Compose for unified development and production environments
- Shared type definitions for end-to-end type safety
- shadcn/ui + Tailwind CSS for UI components

---

## Recommended Directory Structure

```
quorum/
├── .swarm/                      # Claude Flow coordination memory
├── docs/                        # Documentation (this file)
├── docker/                      # Docker configurations
│   ├── development/
│   │   └── docker-compose.yml
│   └── production/
│       └── docker-compose.yml
├── frontend/                    # Next.js 15 application
│   ├── public/
│   ├── src/
│   │   ├── app/                # App Router (Next.js 15)
│   │   │   ├── (auth)/        # Route group - authenticated routes
│   │   │   │   ├── dashboard/
│   │   │   │   └── layout.tsx
│   │   │   ├── (public)/      # Route group - public routes
│   │   │   │   ├── login/
│   │   │   │   └── layout.tsx
│   │   │   ├── api/           # API routes (if needed)
│   │   │   ├── layout.tsx     # Root layout
│   │   │   └── page.tsx       # Home page
│   │   ├── components/        # React components
│   │   │   ├── ui/           # shadcn/ui components
│   │   │   ├── features/     # Feature-specific components
│   │   │   └── shared/       # Shared/common components
│   │   ├── lib/              # Utility functions
│   │   │   ├── api/          # API client functions
│   │   │   ├── hooks/        # Custom React hooks
│   │   │   └── utils.ts      # Helper functions
│   │   ├── styles/           # Global styles
│   │   │   └── globals.css   # Tailwind imports
│   │   └── types/            # TypeScript type definitions
│   ├── .env.local            # Environment variables
│   ├── .eslintrc.js
│   ├── components.json       # shadcn/ui config
│   ├── next.config.ts        # Next.js 15 uses TypeScript config
│   ├── package.json
│   ├── postcss.config.js
│   ├── tailwind.config.ts
│   └── tsconfig.json
├── backend/                     # FastAPI application
│   ├── app/
│   │   ├── api/                # API layer
│   │   │   ├── v1/            # API versioning
│   │   │   │   ├── endpoints/ # Route handlers
│   │   │   │   │   ├── auth.py
│   │   │   │   │   ├── chat.py
│   │   │   │   │   └── agents.py
│   │   │   │   └── router.py  # Main v1 router
│   │   │   └── deps.py        # Dependencies
│   │   ├── core/              # Core functionality
│   │   │   ├── config.py      # Settings & config
│   │   │   ├── security.py    # Auth/security
│   │   │   └── logging.py     # Logging setup
│   │   ├── models/            # Database models (if using DB)
│   │   ├── schemas/           # Pydantic schemas
│   │   │   ├── requests/      # Request models
│   │   │   └── responses/     # Response models
│   │   ├── services/          # Business logic layer
│   │   │   ├── litellm_service.py
│   │   │   └── agent_service.py
│   │   ├── db/                # Database configuration
│   │   │   ├── session.py
│   │   │   └── base.py
│   │   └── main.py            # FastAPI app initialization
│   ├── tests/
│   │   ├── api/
│   │   ├── services/
│   │   └── conftest.py
│   ├── .env
│   ├── pyproject.toml         # Python project config (UV)
│   ├── requirements.txt       # Pip fallback
│   └── Dockerfile
├── shared/                      # Shared code (optional)
│   └── types/                  # Shared TypeScript/Python types
├── .gitignore
├── .dockerignore
├── README.md
└── CLAUDE.md                   # This configuration file
```

---

## Architecture Decision: Monorepo vs Multi-Repo

### Recommendation: **Monorepo**

**Rationale:**
- Simplified dependency management
- Better code sharing between frontend/backend
- Single Docker Compose for entire stack
- Easier local development setup
- Type-safe API client generation (FastAPI → TypeScript)
- Unified CI/CD pipeline

**Key Benefits:**
- Reuse types between FastAPI (Pydantic) and Next.js (TypeScript/Zod)
- Single source of truth for API contracts
- Consistent tooling (ESLint, Prettier, TypeScript)
- Easier onboarding for developers

**Considerations:**
- Use Turborepo's `turbo prune` for optimized Docker builds
- Separate deployment strategies (frontend to Vercel, backend to cloud)
- Use workspace structure if adding more apps later

---

## Frontend Configuration

### package.json Dependencies

```json
{
  "name": "quorum-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "next": "^15.0.3",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "@tanstack/react-query": "^5.59.0",
    "axios": "^1.7.7",
    "zod": "^3.23.8",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.1.1",
    "tailwind-merge": "^2.5.4",
    "lucide-react": "^0.451.0"
  },
  "devDependencies": {
    "@types/node": "^22.8.6",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "typescript": "^5.6.3",
    "eslint": "^9.13.0",
    "eslint-config-next": "^15.0.3",
    "tailwindcss": "^3.4.14",
    "postcss": "^8.4.47",
    "autoprefixer": "^10.4.20",
    "@shadcn/ui": "^0.0.4"
  }
}
```

### Key Configuration Files

**next.config.ts:**
```typescript
import type { NextConfig } from 'next';

const nextConfig: NextConfig = {
  output: 'standalone', // For Docker optimization
  reactStrictMode: true,
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
  },
  // Enable experimental features if needed
  experimental: {
    serverActions: {
      bodySizeLimit: '2mb',
    },
  },
};

export default nextConfig;
```

**tsconfig.json:**
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [
      {
        "name": "next"
      }
    ],
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

**tailwind.config.ts:**
```typescript
import type { Config } from 'tailwindcss';

const config: Config = {
  darkMode: ['class'],
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        // ... shadcn/ui color variables
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },
    },
  },
  plugins: [require('tailwindcss-animate')],
};

export default config;
```

**components.json (shadcn/ui):**
```json
{
  "$schema": "https://ui.shadcn.com/schema.json",
  "style": "default",
  "rsc": true,
  "tsx": true,
  "tailwind": {
    "config": "tailwind.config.ts",
    "css": "src/styles/globals.css",
    "baseColor": "slate",
    "cssVariables": true
  },
  "aliases": {
    "components": "@/components",
    "utils": "@/lib/utils"
  }
}
```

---

## Backend Configuration

### requirements.txt

```txt
# Core Framework
fastapi[standard]==0.115.4
uvicorn[standard]==0.32.0
pydantic==2.9.2
pydantic-settings==2.6.0

# LLM Integration
litellm==1.51.3

# Async & Performance
httpx==0.27.2
redis==5.2.0

# Security & Auth
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.12

# Database (optional - if needed)
sqlalchemy==2.0.36
asyncpg==0.30.0
alembic==1.13.3

# Utilities
python-dotenv==1.0.1
loguru==0.7.2

# Development
pytest==8.3.3
pytest-asyncio==0.24.0
pytest-cov==6.0.0
httpx-sse==0.4.0
```

### pyproject.toml (UV Package Manager)

```toml
[project]
name = "quorum-backend"
version = "0.1.0"
description = "FastAPI backend for Quorum"
requires-python = ">=3.11"
dependencies = [
    "fastapi[standard]>=0.115.4",
    "uvicorn[standard]>=0.32.0",
    "pydantic>=2.9.2",
    "pydantic-settings>=2.6.0",
    "litellm>=1.51.3",
    "httpx>=0.27.2",
    "redis>=5.2.0",
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    "python-multipart>=0.0.12",
    "python-dotenv>=1.0.1",
    "loguru>=0.7.2",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.3",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=6.0.0",
    "httpx-sse>=0.4.0",
    "ruff>=0.7.3",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

### Key Backend Files

**app/main.py:**
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import setup_logging
from app.api.v1.router import api_router

# Setup logging
setup_logging()

# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

**app/core/config.py:**
```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True
    )

    # API
    PROJECT_NAME: str = "Quorum API"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"

    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]

    # LiteLLM
    LITELLM_API_BASE: str = "https://api.openai.com/v1"
    LITELLM_API_KEY: str
    LITELLM_MODEL: str = "gpt-4"

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Redis (optional)
    REDIS_URL: str = "redis://localhost:6379"

settings = Settings()
```

---

## Docker Compose Configuration

### Development (docker/development/docker-compose.yml)

```yaml
version: '3.9'

services:
  frontend:
    build:
      context: ../../frontend
      dockerfile: Dockerfile
      target: development
    container_name: quorum-frontend-dev
    ports:
      - "3000:3000"
    volumes:
      - ../../frontend:/app
      - /app/node_modules
      - /app/.next
    environment:
      - NODE_ENV=development
      - NEXT_PUBLIC_API_URL=http://backend:8000
    depends_on:
      - backend
    networks:
      - quorum-network

  backend:
    build:
      context: ../../backend
      dockerfile: Dockerfile
      target: development
    container_name: quorum-backend-dev
    ports:
      - "8000:8000"
    volumes:
      - ../../backend:/app
      - /app/__pycache__
    environment:
      - ENVIRONMENT=development
      - ALLOWED_ORIGINS=http://localhost:3000
      - LITELLM_API_KEY=${LITELLM_API_KEY}
      - SECRET_KEY=${SECRET_KEY}
    env_file:
      - ../../backend/.env
    networks:
      - quorum-network
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  redis:
    image: redis:7-alpine
    container_name: quorum-redis
    ports:
      - "6379:6379"
    networks:
      - quorum-network
    volumes:
      - redis-data:/data

networks:
  quorum-network:
    driver: bridge

volumes:
  redis-data:
```

### Production (docker/production/docker-compose.yml)

```yaml
version: '3.9'

services:
  frontend:
    build:
      context: ../../frontend
      dockerfile: Dockerfile
      target: production
    container_name: quorum-frontend-prod
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
    restart: unless-stopped
    networks:
      - quorum-network
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:3000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  backend:
    build:
      context: ../../backend
      dockerfile: Dockerfile
      target: production
    container_name: quorum-backend-prod
    ports:
      - "8000:8000"
    environment:
      - ENVIRONMENT=production
      - WORKERS=4
    env_file:
      - ../../backend/.env.production
    restart: unless-stopped
    networks:
      - quorum-network
    healthcheck:
      test: ["CMD", "wget", "--quiet", "--tries=1", "--spider", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

  redis:
    image: redis:7-alpine
    container_name: quorum-redis-prod
    restart: unless-stopped
    networks:
      - quorum-network
    volumes:
      - redis-data:/data

networks:
  quorum-network:
    driver: bridge

volumes:
  redis-data:
```

---

## Dockerfiles

### Frontend Dockerfile

```dockerfile
# Base stage
FROM node:20-alpine AS base
WORKDIR /app
COPY package*.json ./

# Development stage
FROM base AS development
RUN npm install
COPY . .
EXPOSE 3000
CMD ["npm", "run", "dev"]

# Build stage
FROM base AS builder
RUN npm ci
COPY . .
RUN npm run build

# Production stage
FROM node:20-alpine AS production
WORKDIR /app
ENV NODE_ENV=production

# Copy standalone build
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000
CMD ["node", "server.js"]
```

### Backend Dockerfile

```dockerfile
# Base stage
FROM python:3.11-slim AS base
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Install UV package manager
RUN pip install uv

# Development stage
FROM base AS development
COPY requirements.txt .
RUN uv pip install --system -r requirements.txt
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# Build stage
FROM base AS builder
COPY requirements.txt .
RUN uv pip install --system -r requirements.txt

# Production stage
FROM python:3.11-slim AS production
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

---

## Additional Configuration Files

### .gitignore

```gitignore
# Dependencies
node_modules/
__pycache__/
*.pyc
.venv/
venv/

# Build outputs
.next/
out/
dist/
build/

# Environment
.env
.env.local
.env.production
.env.*.local

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Testing
coverage/
.pytest_cache/

# Logs
*.log
logs/

# Docker
docker-compose.override.yml

# Claude Flow
.swarm/
```

### .dockerignore

```dockerignore
# Frontend
node_modules
.next
npm-debug.log
.env*.local

# Backend
__pycache__
*.pyc
.venv
venv
.pytest_cache

# Git
.git
.gitignore

# Documentation
README.md
docs/

# IDE
.vscode
.idea

# Docker
Dockerfile
docker-compose*.yml
```

---

## Setup Instructions

### Initial Setup

```bash
# 1. Clone repository
cd quorum

# 2. Setup frontend
cd frontend
npm install
npx shadcn@latest init
npx shadcn@latest add button card input # Add components as needed
cd ..

# 3. Setup backend
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install uv
uv pip install -r requirements.txt
cd ..

# 4. Create environment files
cp frontend/.env.example frontend/.env.local
cp backend/.env.example backend/.env

# 5. Start development environment
cd docker/development
docker-compose up --build
```

### Development Workflow

```bash
# Start all services
docker-compose -f docker/development/docker-compose.yml up

# Frontend only
cd frontend && npm run dev

# Backend only
cd backend && uvicorn app.main:app --reload

# Run tests
cd frontend && npm test
cd backend && pytest

# Type checking
cd frontend && npm run typecheck
cd backend && mypy app/
```

---

## Best Practices Summary

### Next.js 15 Best Practices

1. **Use `src/` directory** for better organization
2. **Route groups** `(auth)`, `(public)` for logical organization without URL impact
3. **Feature-based components** in `src/components/features/`
4. **Server Components by default**, Client Components only when needed
5. **TypeScript strict mode** for type safety
6. **Absolute imports** with `@/` path alias

### FastAPI Best Practices

1. **Module-functionality structure** for scalability
2. **Separate API versions** (`/api/v1`, `/api/v2`)
3. **Pydantic schemas** for validation and documentation
4. **Service layer** for business logic separation
5. **Async/await** for all I/O operations
6. **Dependency injection** via FastAPI's `Depends()`

### Docker Best Practices

1. **Multi-stage builds** for optimized images
2. **Separate dev/prod** configurations
3. **Volume mounts** for development hot-reload
4. **Health checks** for production
5. **`.dockerignore`** to reduce context size
6. **Non-root user** in production images

### LiteLLM Integration

1. **Separate service layer** for LLM operations
2. **Health endpoints** on separate port for production
3. **Rate limiting** via Redis
4. **Master key & salt key** for security
5. **Batched spend updates** (60s intervals)
6. **Fallbacks and retries** configured

---

## Technology Versions (Verified Current)

| Technology | Version | Release Date |
|------------|---------|--------------|
| Next.js | 15.0.3 | Nov 2024 |
| React | 19.0.0 | Dec 2024 |
| TypeScript | 5.6.3 | Current |
| Tailwind CSS | 3.4.14 | Current |
| shadcn/ui | Latest | Current |
| FastAPI | 0.115.4 | Nov 2024 |
| Python | 3.11+ | Required |
| LiteLLM | 1.51.3 | Current |
| Pydantic | 2.9.2 | Current |
| UV | Latest | Current |
| Node.js | 20 LTS | Stable |
| Redis | 7-alpine | Current |

---

## Research Sources

### Next.js 15 & Project Structure
- [Best Practices for Organizing Your Next.js 15 2025](https://dev.to/bajrayejoon/best-practices-for-organizing-your-nextjs-15-2025-53ji)
- [Next.js Official Project Structure Docs](https://nextjs.org/docs/app/getting-started/project-structure)
- [The Battle-Tested NextJS Project Structure I Use in 2025](https://medium.com/@burpdeepak96/the-battle-tested-nextjs-project-structure-i-use-in-2025-f84c4eb5f426)
- [The Ultimate Guide to Organizing Your Next.js 15 Project Structure](https://www.wisp.blog/blog/the-ultimate-guide-to-organizing-your-nextjs-15-project-structure)
- [Scalable Next.js 15 App Router Project Structure](https://levelup.gitconnected.com/how-to-set-up-a-scalable-next-js-15-app-router-project-structure-pro-tips-3c42778cd737)

### FastAPI Best Practices
- [FastAPI Best Practices (GitHub)](https://github.com/zhanymkanov/fastapi-best-practices)
- [FastAPI Official Docs - Bigger Applications](https://fastapi.tiangolo.com/tutorial/bigger-applications/)
- [How to Structure Your FastAPI Projects](https://medium.com/@amirm.lavasani/how-to-structure-your-fastapi-projects-0219a6600a8f)
- [Structuring a FastAPI Project: Best Practices](https://dev.to/mohammad222pr/structuring-a-fastapi-project-best-practices-53l6)
- [The Perfect Structure for a Large Production-Ready FastAPI App](https://medium.com/@devsumitg/the-perfect-structure-for-a-large-production-ready-fastapi-app-78c55271d15c)

### Monorepo & Docker Integration
- [Generating API clients in monorepos with FastAPI & Next.js](https://www.vintasoftware.com/blog/nextjs-fastapi-monorepo)
- [Next.js Monorepo Example (belgattitude)](https://github.com/belgattitude/nextjs-monorepo-example)
- [Using Docker Compose with Nx Monorepo](https://www.codefeetime.com/post/using-docker-compose-with-nx-monorepo-for-multi-apps-development/)

### shadcn/ui Setup
- [shadcn/ui Official Next.js Installation](https://ui.shadcn.com/docs/installation/next)
- [Next.js 15: Starter with Tailwind 4.0 & Shadcn](https://medium.com/@rikunaru/nextjs-starter-with-tailwind-shadcn-6e0eda2dd520)
- [2025: Complete Guide for Next.js 15, Tailwind v4, React 19, shadcn](https://medium.com/@dilit/building-a-modern-application-2025-a-complete-guide-for-next-js-1b9f278df10c)

### LiteLLM Integration
- [LiteLLM FastAPI Integration Guide](https://www.restack.io/p/litellm-answer-fastapi-integration-cat-ai)
- [Best Practices for Production - LiteLLM](https://docs.litellm.ai/docs/proxy/prod)
- [LiteLLM Official Docs](https://docs.litellm.ai/docs/)
- [LiteLLM GitHub Repository](https://github.com/BerriAI/litellm)

### Docker & Docker Compose
- [FastAPI + Next.js Full Stack Template](https://github.com/Nneji123/fastapi-nextjs)
- [How to Develop Full Stack Next.js + FastAPI with Docker](https://www.travisluong.com/how-to-develop-a-full-stack-next-js-fastapi-postgresql-app-using-docker/)
- [Next.js FastAPI Template (Vinta Software)](https://www.vintasoftware.com/blog/next-js-fastapi-template)
- [Next.js FastAPI Docker Example](https://github.com/YsrajSingh/nextjs-fastapi-docker)

---

## Next Steps

1. **Phase 1 Implementation** - Create project structure
2. **Environment Setup** - Configure all environment variables
3. **Docker Testing** - Verify development environment
4. **shadcn/ui Components** - Install initial UI components
5. **API Scaffolding** - Create basic FastAPI endpoints
6. **Type Safety** - Setup shared types between frontend/backend
7. **Testing Setup** - Configure Jest (frontend) and Pytest (backend)
8. **CI/CD Pipeline** - Setup GitHub Actions

---

**Research Completed:** November 30, 2025
**Confidence Level:** High (based on 2025 current best practices)
**Ready for Implementation:** Yes
