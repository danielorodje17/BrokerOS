from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
import uuid
from datetime import datetime, timezone

from .deps import db, get_current_user
from .models import NoteCreate

router = APIRouter(prefix="/notes", tags=["notes"])


@router.get("")
async def list_notes(case_id: str = Query(...), user: dict = Depends(get_current_user)):
    """Get all notes for a case, sorted by created_at descending"""
    case = await db.cases.find_one({"id": case_id, "assigned_broker_id": user["id"]})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    notes = await db.notes.find({"case_id": case_id}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return {"notes": notes, "total": len(notes)}


@router.post("")
async def create_note(data: NoteCreate, user: dict = Depends(get_current_user)):
    """Create a new note (immutable - no edit or delete)"""
    case = await db.cases.find_one({"id": data.case_id, "assigned_broker_id": user["id"]})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Validate content length
    if len(data.content) > 2000:
        raise HTTPException(status_code=400, detail="Note content exceeds 2000 characters")

    # Get author name from user profile
    author_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
    if not author_name:
        author_name = user.get('email', 'Unknown')

    note_doc = {
        "id": str(uuid.uuid4()),
        "case_id": data.case_id,
        "user_id": user["id"],
        "author_name": author_name,
        "content": data.content,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.notes.insert_one(note_doc)
    note_doc.pop("_id", None)
    return note_doc


# Also provide case-specific notes endpoint
cases_notes_router = APIRouter(tags=["notes"])


@cases_notes_router.get("/cases/{case_id}/notes")
async def list_case_notes(case_id: str, user: dict = Depends(get_current_user)):
    """Get all notes for a case, sorted by created_at descending"""
    case = await db.cases.find_one({"id": case_id, "assigned_broker_id": user["id"]})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    notes = await db.notes.find({"case_id": case_id}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return {"notes": notes, "total": len(notes)}
