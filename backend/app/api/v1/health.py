from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.database import get_db
import redis.asyncio as redis
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/health")
async def health_check():
    return {"status": "healthy"}

@router.get("/ready")
async def ready_check(db: AsyncSession = Depends(get_db)):
    """Check connections to dependencies"""
    status = {"db": "unknown", "redis": "unknown"}
    
    # Check DB
    try:
        await db.execute(text("SELECT 1"))
        status["db"] = "ok"
    except Exception as e:
        logger.error(f"Database readiness check failed: {e}")
        status["db"] = "error"

    # Check Redis
    try:
        r = redis.from_url(settings.REDIS_URL)
        await r.ping()
        status["redis"] = "ok"
        await r.aclose()
    except Exception as e:
        logger.error(f"Redis readiness check failed: {e}")
        status["redis"] = "error"
        
    is_ready = status["db"] == "ok" and status["redis"] == "ok"
    return {
        "status": "ready" if is_ready else "not_ready",
        "dependencies": status
    }
