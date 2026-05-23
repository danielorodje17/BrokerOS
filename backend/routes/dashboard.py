from fastapi import APIRouter, Depends
from datetime import datetime, timezone, timedelta

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

    # ---- Commission alerts ----
    today = datetime.now(timezone.utc).date()
    fourteen_days_later = today + timedelta(days=14)
    thirty_days_ago = today - timedelta(days=30)

    pending_comms = await db.commission_records.find(
        {"user_id": user["id"], "status": {"$ne": "received"}, "expected_payment_date": {"$ne": None}},
        {"_id": 0, "expected_payment_date": 1}
    ).to_list(1000)

    due_soon_count = 0
    overdue_count = 0
    for c in pending_comms:
        date_str = c.get("expected_payment_date")
        if not date_str:
            continue
        try:
            expected_date = (
                datetime.fromisoformat(str(date_str).replace("Z", "+00:00")).date()
                if "T" in str(date_str)
                else datetime.strptime(str(date_str), "%Y-%m-%d").date()
            )
            if today <= expected_date <= fourteen_days_later:
                due_soon_count += 1
            elif expected_date < thirty_days_ago:
                overdue_count += 1
        except (ValueError, TypeError):
            continue

    clawback_risk_count = await db.commission_records.count_documents({
        "user_id": user["id"],
        "clawback_risk_until": {"$ne": None, "$gt": today.isoformat()}
    })

    # ---- Recent cases (last 5) ----
    recent_cases_raw = await db.cases.find(
        {"assigned_broker_id": user["id"]},
        {"_id": 0, "id": 1, "client_id": 1, "lender_id": 1, "stage": 1, "loan_amount": 1, "created_at": 1, "mortgage_type": 1}
    ).sort("created_at", -1).limit(5).to_list(5)

    recent_cases = []
    for case in recent_cases_raw:
        client = await db.clients.find_one({"id": case.get("client_id")}, {"_id": 0, "first_name": 1, "last_name": 1})
        lender = await db.lenders.find_one({"id": case.get("lender_id")}, {"_id": 0, "name": 1})
        recent_cases.append({
            "id": case["id"],
            "client_name": f"{client['first_name']} {client['last_name']}" if client else "Unknown",
            "lender_name": lender.get("name") if lender else "-",
            "stage": case.get("stage"),
            "loan_amount": case.get("loan_amount"),
            "mortgage_type": case.get("mortgage_type"),
            "created_at": case.get("created_at"),
        })

    return {
        "clients_count": clients_count,
        "cases_count": cases_count,
        "pipeline": pipeline,
        "commissions": {
            "pending": pending_total,
            "received": received_total
        },
        "alerts": {
            "overdue_count": overdue_count,
            "due_soon_count": due_soon_count,
            "clawback_risk_count": clawback_risk_count,
        },
        "recent_cases": recent_cases,
    }


@router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}
