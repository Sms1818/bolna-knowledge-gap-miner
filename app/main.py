from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.routes import gap_analysis, knowledge_gaps, knowledge_suggestions

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Evidence-first knowledge gap detection "
        "for completed voice-agent conversations."
    ),
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version,
    }

app.include_router(gap_analysis.router)
app.include_router(knowledge_gaps.router)
app.include_router(knowledge_gaps.detail_router)

app.include_router(knowledge_suggestions.router)
app.include_router(knowledge_suggestions.review_router)
