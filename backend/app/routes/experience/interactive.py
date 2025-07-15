from fastapi import APIRouter, HTTPException
from uuid import uuid4
from datetime import datetime

router = APIRouter()

# In-memory storage for interactive sessions
INTERACTIVE_SESSIONS: dict[str, dict] = {}


@router.get("/interactive", tags=["Experience"])
async def list_interactive_sessions():
    """List all scheduled interactive sessions."""
    try:
        return {"interactive_sessions": list(INTERACTIVE_SESSIONS.values())}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Failed to list interactive sessions"
        ) from e


@router.post("/interactive", tags=["Experience"])
async def schedule_interactive_session(session: dict):
    """
    Schedule a new interactive session (e.g., trivia or game event).
    Expects JSON payload with 'type' (trivia/game) and
    'scheduled_time' (ISO format), and optionally a 'description' field.
    """
    try:
        session_type = session.get("type")
        scheduled_time = session.get("scheduled_time")
        if not session_type or not scheduled_time:
            raise HTTPException(
                status_code=400,
                detail="Missing required fields: type, scheduled_time"
            )
        try:
            scheduled_dt = datetime.fromisoformat(scheduled_time)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Invalid scheduled_time format. Use ISO format."
            )
        session_id = str(uuid4())
        new_session = {
            "id": session_id,
            "type": session_type,
            "scheduled_time": scheduled_dt.isoformat(),
            "description": session.get("description", "")
        }
        INTERACTIVE_SESSIONS[session_id] = new_session
        return new_session
    except HTTPException as he:
        raise he
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Failed to schedule interactive session"
        ) from e


@router.delete("/interactive/{session_id}", tags=["Experience"])
async def delete_interactive_session(session_id: str):
    """Delete an interactive session by ID."""
    try:
        session = INTERACTIVE_SESSIONS.pop(session_id, None)
        if not session:
            raise HTTPException(
                status_code=404,
                detail="Interactive session not found"
            )
        return {"detail": "Interactive session deleted successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="Failed to delete interactive session"
        ) from e 