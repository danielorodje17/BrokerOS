from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional
import uuid
from datetime import datetime, timezone

from .deps import db, get_current_user
from .models import CaseCreate

router = APIRouter(prefix="/cases", tags=["cases"])


@router.get("")
async def list_cases(
    search: Optional[str] = None,
    stage: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    user: dict = Depends(get_current_user)
):
    query = {"assigned_broker_id": user["id"]}
    if stage:
        query["stage"] = stage
    if search:
        query["$or"] = [
            {"notes": {"$regex": search, "$options": "i"}}
        ]

    total = await db.cases.count_documents(query)
    cases = await db.cases.find(query, {"_id": 0}).skip((page-1)*limit).limit(limit).to_list(limit)

    # Enrich with client info
    for case in cases:
        client = await db.clients.find_one({"id": case.get("client_id")}, {"_id": 0, "first_name": 1, "last_name": 1})
        case["client_name"] = f"{client['first_name']} {client['last_name']}" if client else "Unknown"
        if case.get("lender_id"):
            lender = await db.lenders.find_one({"id": case["lender_id"]}, {"_id": 0, "name": 1})
            case["lender_name"] = lender["name"] if lender else None

    return {"cases": cases, "total": total, "page": page, "limit": limit}


@router.post("")
async def create_case(data: CaseCreate, user: dict = Depends(get_current_user)):
    # Verify client exists
    client = await db.clients.find_one({"id": data.client_id, "user_id": user["id"]})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    case_doc = data.model_dump()
    case_doc["id"] = str(uuid.uuid4())
    case_doc["assigned_broker_id"] = user["id"]

    # Calculate LTV
    if data.loan_amount and data.property_value and data.property_value > 0:
        case_doc["ltv"] = round((data.loan_amount / data.property_value) * 100, 2)
    else:
        case_doc["ltv"] = None

    case_doc["actual_completion_date"] = None
    case_doc["created_at"] = datetime.now(timezone.utc).isoformat()
    case_doc["updated_at"] = datetime.now(timezone.utc).isoformat()
    case_doc["stage_updated_at"] = datetime.now(timezone.utc).isoformat()

    await db.cases.insert_one(case_doc)
    case_doc.pop("_id", None)
    return case_doc


@router.get("/{case_id}")
async def get_case(case_id: str, user: dict = Depends(get_current_user)):
    case = await db.cases.find_one({"id": case_id, "assigned_broker_id": user["id"]}, {"_id": 0})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Enrich
    client = await db.clients.find_one({"id": case.get("client_id")}, {"_id": 0})
    case["client"] = client
    if case.get("lender_id"):
        lender = await db.lenders.find_one({"id": case["lender_id"]}, {"_id": 0})
        case["lender"] = lender

    return case


@router.put("/{case_id}")
async def update_case(case_id: str, data: CaseCreate, user: dict = Depends(get_current_user)):
    update_doc = data.model_dump()
    update_doc["updated_at"] = datetime.now(timezone.utc).isoformat()

    # Recalculate LTV
    if data.loan_amount and data.property_value and data.property_value > 0:
        update_doc["ltv"] = round((data.loan_amount / data.property_value) * 100, 2)

    # Check if stage changed
    existing = await db.cases.find_one({"id": case_id, "assigned_broker_id": user["id"]})
    if existing and existing.get("stage") != data.stage:
        update_doc["stage_updated_at"] = datetime.now(timezone.utc).isoformat()

    result = await db.cases.update_one(
        {"id": case_id, "assigned_broker_id": user["id"]},
        {"$set": update_doc}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Case not found")
    return await db.cases.find_one({"id": case_id}, {"_id": 0})


@router.patch("/{case_id}/stage")
async def update_case_stage(case_id: str, stage: str = Query(...), user: dict = Depends(get_current_user)):
    update_doc = {
        "stage": stage,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "stage_updated_at": datetime.now(timezone.utc).isoformat()
    }
    if stage == "completion":
        update_doc["actual_completion_date"] = datetime.now(timezone.utc).isoformat()

    result = await db.cases.update_one(
        {"id": case_id, "assigned_broker_id": user["id"]},
        {"$set": update_doc}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Case not found")
    return await db.cases.find_one({"id": case_id}, {"_id": 0})


@router.delete("/{case_id}")
async def delete_case(case_id: str, user: dict = Depends(get_current_user)):
    result = await db.cases.delete_one({"id": case_id, "assigned_broker_id": user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Case not found")
    return {"message": "Case deleted"}
