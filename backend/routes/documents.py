from fastapi import APIRouter, HTTPException, Depends, Query, File, UploadFile
from fastapi.responses import Response
from typing import Optional
import uuid
from datetime import datetime, timezone

from .deps import db, get_current_user, put_object, get_object, logger, APP_NAME

router = APIRouter(tags=["documents"])


@router.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    client_id: str = Query(...),
    case_id: Optional[str] = None,
    document_type: str = Query("other"),
    expiry_date: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    # Verify client exists
    client = await db.clients.find_one({"id": client_id, "user_id": user["id"]})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    ext = file.filename.split(".")[-1] if "." in file.filename else "bin"
    path = f"{APP_NAME}/documents/{user['id']}/{uuid.uuid4()}.{ext}"
    data = await file.read()

    try:
        result = put_object(path, data, file.content_type or "application/octet-stream")
        doc = {
            "id": str(uuid.uuid4()),
            "client_id": client_id,
            "case_id": case_id,
            "document_type": document_type,
            "filename": file.filename,
            "file_path": result["path"],
            "content_type": file.content_type,
            "size": result.get("size", len(data)),
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "expiry_date": expiry_date,
            "user_id": user["id"],
            "is_deleted": False
        }
        await db.documents.insert_one(doc)
        doc.pop("_id", None)
        return {"success": True, "data": doc, "message": None}
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail="Upload failed")


@router.get("/documents")
async def list_documents(
    client_id: Optional[str] = None,
    case_id: Optional[str] = None,
    user: dict = Depends(get_current_user)
):
    query = {"user_id": user["id"], "is_deleted": False}
    if client_id:
        query["client_id"] = client_id
    if case_id:
        query["case_id"] = case_id

    docs = await db.documents.find(query, {"_id": 0}).to_list(100)
    return {"success": True, "data": docs, "message": None}


@router.get("/documents/{doc_id}/download")
async def download_document(doc_id: str, user: dict = Depends(get_current_user)):
    doc = await db.documents.find_one({"id": doc_id, "user_id": user["id"], "is_deleted": False})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    try:
        data, content_type = get_object(doc["file_path"])
        return Response(content=data, media_type=doc.get("content_type", content_type),
                        headers={"Content-Disposition": f"attachment; filename={doc['filename']}"})
    except Exception as e:
        logger.error(f"Download failed: {e}")
        raise HTTPException(status_code=500, detail="Download failed")


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str, user: dict = Depends(get_current_user)):
    result = await db.documents.update_one(
        {"id": doc_id, "user_id": user["id"]},
        {"$set": {"is_deleted": True}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"success": True, "data": None, "message": "Document deleted"}
