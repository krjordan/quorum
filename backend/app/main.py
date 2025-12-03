from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.config.settings import settings
from app.api.routes import chat, health, debate


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"🚀 Starting {settings.app_name}")
    print(f"📝 Environment: {settings.environment}")
    print(f"🔐 CORS origins: {settings.cors_origins}")

    if settings.openai_api_key:
        print("✅ OpenAI API key configured")
    if settings.anthropic_api_key:
        print("✅ Anthropic API key configured")
    if settings.google_api_key:
        print("✅ Google API key configured")
    if settings.mistral_api_key:
        print("✅ Mistral API key configured")

    print("🎭 Multi-LLM Debate Engine initialized")

    yield
    print("👋 Shutting down")


app = FastAPI(
    title=settings.app_name,
    description="Backend API for Quorum AI Debate Platform with Multi-LLM Debate Orchestration",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["Health"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])
app.include_router(debate.router, prefix="/api/v1", tags=["Debates"])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )
