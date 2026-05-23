from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
import uuid
from datetime import datetime, timezone

from .deps import db, get_current_user
from .models import ClientCreate

router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("")
async def list_clients(
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    user: dict = Depends(get_current_user)
):
    query = {"user_id": user["id"]}
    if search:
        query["$or"] = [
            {"first_name": {"$regex": search, "$options": "i"}},
            {"last_name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}}
        ]

    total = await db.clients.count_documents(query)
    clients = await db.clients.find(query, {"_id": 0}).skip((page-1)*limit).limit(limit).to_list(limit)
    return {"clients": clients, "total": total, "page": page, "limit": limit}


@router.post("")
async def create_client(data: ClientCreate, user: dict = Depends(get_current_user)):
    client_doc = data.model_dump()
    client_doc["id"] = str(uuid.uuid4())
    client_doc["user_id"] = user["id"]
    client_doc["created_at"] = datetime.now(timezone.utc).isoformat()
    client_doc["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.clients.insert_one(client_doc)
    client_doc.pop("_id", None)
    return client_doc


@router.get("/{client_id}")
async def get_client(client_id: str, user: dict = Depends(get_current_user)):
    client = await db.clients.find_one({"id": client_id, "user_id": user["id"]}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.put("/{client_id}")
async def update_client(client_id: str, data: ClientCreate, user: dict = Depends(get_current_user)):
    update_doc = data.model_dump()
    update_doc["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await db.clients.update_one(
        {"id": client_id, "user_id": user["id"]},
        {"$set": update_doc}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Client not found")
    return await db.clients.find_one({"id": client_id}, {"_id": 0})


@router.delete("/{client_id}")
async def delete_client(client_id: str, user: dict = Depends(get_current_user)):
    result = await db.clients.delete_one({"id": client_id, "user_id": user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Client not found")
    return {"message": "Client deleted"}
