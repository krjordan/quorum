# Quorum - Phase 1 Setup Guide

This guide will help you set up and run the Quorum Phase 1 single-LLM streaming chat interface.

## Prerequisites

- Docker and Docker Compose installed
- At least one API key (OpenAI or Anthropic recommended)

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/quorum.git
cd quorum
```

### 2. Configure Environment Variables

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your API keys
nano .env  # or use your preferred editor
```

**Minimum required**: Add at least one API key:
```bash
OPENAI_API_KEY=sk-proj-your-key-here
# OR
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

### 3. Start the Application

```bash
docker-compose -f docker/development/docker-compose.yml up --build
```

Wait for the containers to start. You should see:
```
✅ OpenAI API key configured
🚀 Starting Quorum API
```

### 4. Access the Application

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## Development Workflow

### Frontend Development

```bash
cd frontend
npm install
npm run dev
```

Access at http://localhost:3000

**Available Scripts:**
- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run lint` - Run ESLint
- `npm run test` - Run tests

### Backend Development

```bash
cd backend
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Access at http://localhost:8000

**Available Commands:**
- `uvicorn app.main:app --reload` - Start with hot reload
- `pytest` - Run tests
- `black .` - Format code
- `ruff check .` - Lint code

## Testing the Chat Interface

1. Open http://localhost:3000
2. Type a message in the input box
3. Press Enter or click "Send"
4. Watch the response stream in real-time!

**Example prompts:**
- "Explain quantum computing in simple terms"
- "Write a haiku about programming"
- "What are the pros and cons of TypeScript?"

## Architecture Overview

```
Frontend (Port 3000)
├── Next.js 15 + React 19
├── Zustand (state management)
├── SSE client (streaming)
└── Tailwind CSS + shadcn/ui

Backend (Port 8000)
├── FastAPI
├── LiteLLM (multi-provider LLM)
├── SSE streaming
└── SQLite (future debate storage)

Redis (Port 6379)
└── Rate limiting (optional, future)
```

## Troubleshooting

### Frontend not connecting to backend
- Check that backend is running: `curl http://localhost:8000/health`
- Verify CORS settings in `.env`: `CORS_ORIGINS=http://localhost:3000`

### API key errors
- Ensure API key is correctly set in `.env`
- Check backend startup logs for "✅ API key configured" messages
- Verify key format: OpenAI keys start with `sk-proj-` or `sk-`

### Docker issues
- Rebuild containers: `docker-compose down && docker-compose up --build`
- Check logs: `docker-compose logs frontend` or `docker-compose logs backend`
- Clear volumes: `docker-compose down -v`

### Streaming not working
- Check browser console for errors
- Verify SSE endpoint: `curl http://localhost:8000/api/v1/chat/stream?message=hello`
- Ensure frontend `NEXT_PUBLIC_API_URL` is set correctly

## Next Steps

Phase 1 is complete! Next phases will add:
- **Phase 2**: Multi-LLM debate support
- **Phase 3**: Judge agent with structured output
- **Phase 4**: Debate formats and export
- **Phase 5**: Production deployment

## Support

- Documentation: `/docs/`
- API Reference: http://localhost:8000/docs
- Issues: https://github.com/yourusername/quorum/issues

---

**Happy debugging!** 🎉
