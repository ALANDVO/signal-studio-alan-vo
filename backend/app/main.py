from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings, verify_startup_safety
from app.core.database import init_db
from app.api.auth_routes import router as auth_router
from app.api.chat_routes import router as chat_router
from app.api.notes_routes import router as notes_router
from app.api.knowledge_routes import router as knowledge_router
from app.api.tools_routes import router as tools_router
from app.api.eval_routes import router as eval_router
from app.api.audit_routes import router as audit_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Enforce production security check on startup
    verify_startup_safety()
    # Initialize database tables
    init_db()
    yield


def create_app() -> FastAPI:
    application = FastAPI(
        title="Signal Studio API",
        version="1.0.0",
        description="Reasoning model workbench featuring conversational tree validation, thought tag isolation, user-scoped tool credentials, and multi-strategy knowledge retrieval.",
        lifespan=lifespan,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @application.get("/api/health", tags=["System"])
    def health_check():
        return {
            "status": "healthy",
            "environment": settings.ENVIRONMENT,
            "demo_mode": settings.AUTH_DEMO_MODE,
            "llm_provider": settings.LLM_PROVIDER,
            "version": "1.0.0",
        }

    application.include_router(auth_router)
    application.include_router(chat_router)
    application.include_router(notes_router)
    application.include_router(knowledge_router)
    application.include_router(tools_router)
    application.include_router(eval_router)
    application.include_router(audit_router)

    return application


app = create_app()
