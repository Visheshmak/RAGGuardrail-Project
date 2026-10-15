from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.v1 import health, auth, projects, documents, rag, datasets, guardrails, evaluations

def create_app() -> FastAPI:
    app = FastAPI(
        title="RAGGuard API",
        version="0.1.0",
        description="Regression-Safe RAG Guardrails Evaluation Platform"
    )

    # Configure CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(health.router, prefix="/api/v1", tags=["Health"])
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
    app.include_router(projects.router, prefix="/api/v1/projects", tags=["Projects"])
    app.include_router(documents.router, prefix="/api/v1/projects", tags=["Documents"])
    app.include_router(rag.router, prefix="/api/v1/projects", tags=["RAG"])
    app.include_router(datasets.router, prefix="/api/v1", tags=["Datasets"])
    app.include_router(guardrails.router, prefix="/api/v1/projects", tags=["Guardrails"])
    app.include_router(evaluations.router, prefix="/api/v1", tags=["Evaluations & Baselines"])

    return app

app = create_app()
