"""
Health-check endpoint – also verifies DB connectivity.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.core.database import get_db

router = APIRouter()


@router.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Return system health including DB connectivity."""
    db_ok = False
    db_error = None
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception as exc:
        db_error = str(exc)

    status = "healthy" if db_ok else "degraded"
    result = {
        "status": status,
        "service": "Engineering Contribution Analytics",
        "version": "0.1.0",
        "database": {"connected": db_ok},
    }
    if db_error:
        result["database"]["error"] = db_error
    return result
