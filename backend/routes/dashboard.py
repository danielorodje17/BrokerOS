from fastapi import APIRouter, Depends
from datetime import datetime, timezone

from .deps import db, get_current_user

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/stats")
async def get_dashboard_stats(user: dict = Depends(get_current_user)):
    clients_count = await db.clients.count_documents({"user_id": user["id"]})
    cases_count = await db.cases.count_documents({"assigned_broker_id": user["id"]})

    # Pipeline summary
    stages = ["new_enquiry", "fact_find", "aip_submitted", "aip_received", "full_application",
              "valuation", "offer", "exchange", "completion", "on_hold", "declined"]
    pipeline = {}
    for stage in stages:
        pipeline[stage] = await db.cases.count_documents({"assigned_broker_id": user["id"], "stage": stage})

    # Commission summary
    pending = await db.commission_records.find({"user_id": user["id"], "status": "pending"}, {"expected_amount": 1}).to_list(1000)
    received = await db.commission_records.find({"user_id": user["id"], "status": "received"}, {"received_amount": 1}).to_list(1000)

    pending_total = sum(c.get("expected_amount", 0) or 0 for c in pending)
    received_total = sum(c.get("received_amount", 0) or 0 for c in received)

    return {
        "clients_count": clients_count,
        "cases_count": cases_count,
        "pipeline": pipeline,
        "commissions": {
            "pending": pending_total,
            "received": received_total
        }
    }


@router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}
