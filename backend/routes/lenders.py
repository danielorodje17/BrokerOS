from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
import uuid
from datetime import datetime, timezone

from .deps import db, get_current_user
from .models import LenderCreate

router = APIRouter(prefix="/lenders", tags=["lenders"])


@router.get("")
async def list_lenders(
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    user: dict = Depends(get_current_user)
):
    query = {"user_id": user["id"]}
    if search:
        query["name"] = {"$regex": search, "$options": "i"}

    total = await db.lenders.count_documents(query)
    lenders = await db.lenders.find(query, {"_id": 0}).skip((page-1)*limit).limit(limit).to_list(limit)
    return {"success": True, "data": lenders, "total": total, "page": page, "limit": limit, "message": None}


@router.post("")
async def create_lender(data: LenderCreate, user: dict = Depends(get_current_user)):
    lender_doc = data.model_dump()
    lender_doc["id"] = str(uuid.uuid4())
    lender_doc["user_id"] = user["id"]
    lender_doc["created_at"] = datetime.now(timezone.utc).isoformat()
    lender_doc["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.lenders.insert_one(lender_doc)
    lender_doc.pop("_id", None)
    return {"success": True, "data": lender_doc, "message": None}


@router.get("/{lender_id}")
async def get_lender(lender_id: str, user: dict = Depends(get_current_user)):
    lender = await db.lenders.find_one({"id": lender_id, "user_id": user["id"]}, {"_id": 0})
    if not lender:
        raise HTTPException(status_code=404, detail="Lender not found")
    return {"success": True, "data": lender, "message": None}


@router.put("/{lender_id}")
async def update_lender(lender_id: str, data: LenderCreate, user: dict = Depends(get_current_user)):
    update_doc = data.model_dump()
    update_doc["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await db.lenders.update_one(
        {"id": lender_id, "user_id": user["id"]},
        {"$set": update_doc}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Lender not found")
    updated = await db.lenders.find_one({"id": lender_id}, {"_id": 0})
    return {"success": True, "data": updated, "message": None}


@router.delete("/{lender_id}")
async def delete_lender(lender_id: str, user: dict = Depends(get_current_user)):
    result = await db.lenders.delete_one({"id": lender_id, "user_id": user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Lender not found")
    return {"success": True, "data": None, "message": "Lender deleted"}
