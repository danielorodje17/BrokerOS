"""
routes/retention.py — Rate Expiry and Retention module (Phase 2.5)
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from datetime import datetime, timezone, timedelta, date as date_type
from pydantic import BaseModel

from .deps import db, get_current_user, get_case_filter

router = APIRouter(prefix="/retention", tags=["retention"])


# ── Helpers ────────────────────────────────────────────────────────────────────

def _parse_date(value) -> Optional[date_type]:
    """Parse ISO date string or datetime string to a date object."""
    if not value:
        return None
    try:
        s = str(value)
        if "T" in s:
            return datetime.fromisoformat(s.replace("Z", "+00:00")).date()
        return datetime.strptime(s, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _fmt_date(d: Optional[date_type]) -> Optional[str]:
    """Format date object as DD/MM/YYYY."""
    return d.strftime("%d/%m/%Y") if d else None


async def _enrich_case(c: dict, today: date_type) -> dict:
    """Enrich a raw case document for the retention response shape."""
    expiry = _parse_date(c.get("rate_expiry_date"))
    days = (expiry - today).days if expiry else None

    client = await db.clients.find_one(
        {"id": c.get("client_id")}, {"_id": 0, "first_name": 1, "last_name": 1}
    )
    client_name = (
        f"{client['first_name']} {client['last_name']}" if client else "Unknown"
    )

    lender_name = "Not assigned"
    if c.get("lender_id"):
        lender = await db.lenders.find_one({"id": c["lender_id"]}, {"_id": 0, "name": 1})
        if lender:
            lender_name = lender["name"]

    return {
        "id": c["id"],
        "client_name": client_name,
        "lender_name": lender_name,
        "mortgage_type": c.get("mortgage_type", ""),
        "loan_amount": c.get("loan_amount"),
        "rate_percent": c.get("rate_percent"),
        "rate_type": c.get("rate_type", ""),
        "rate_expiry_date": _fmt_date(expiry),
        "days_until_expiry": days,
        "retention_status": c.get("retention_status") or "none",
        "actual_completion_date": _fmt_date(_parse_date(c.get("actual_completion_date"))),
    }


def _base_query(user: dict) -> dict:
    """Base MongoDB query for monitored cases."""
    return {
        **get_case_filter(user),
        "stage": "completion",
        "rate_expiry_date": {"$exists": True, "$nin": [None, ""]},
    }


# ── Pydantic models ────────────────────────────────────────────────────────────

class RetentionStatusUpdate(BaseModel):
    retention_status: str


VALID_STATUSES = {"none", "flagged", "contacted", "new_case_created"}


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get("/cases")
async def list_retention_cases(
    window: Optional[int] = None,
    status: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    """
    GET /api/retention/cases
    Returns completed cases that have a rate_expiry_date set,
    sorted by days_until_expiry ascending.
    """
    today = datetime.now(timezone.utc).date()

    query = _base_query(user)
    if status:
        query["retention_status"] = status

    raw_cases = await db.cases.find(query, {"_id": 0}).to_list(2000)

    results = []
    for c in raw_cases:
        expiry = _parse_date(c.get("rate_expiry_date"))
        if not expiry:
            continue
        days = (expiry - today).days

        # Apply window filter
        if window is not None:
            if window == -1:          # "Already Expired" pseudo-window
                if days >= 0:
                    continue
            else:
                if days > window:
                    continue

        results.append(await _enrich_case(c, today))

    results.sort(key=lambda x: x["days_until_expiry"] if x["days_until_expiry"] is not None else 9999)

    # Summary — always computed from the full unfiltered monitored set
    all_monitored = await db.cases.find(_base_query(user), {"_id": 0, "rate_expiry_date": 1}).to_list(2000)
    total_monitored = 0
    expiring_90 = 0
    expiring_90_180 = 0
    already_expired = 0
    for c in all_monitored:
        expiry = _parse_date(c.get("rate_expiry_date"))
        if not expiry:
            continue
        total_monitored += 1
        d = (expiry - today).days
        if d < 0:
            already_expired += 1
        elif d <= 90:
            expiring_90 += 1
        elif d <= 180:
            expiring_90_180 += 1

    return {
        "success": True,
        "data": {
            "cases": results,
            "summary": {
                "total_monitored": total_monitored,
                "expiring_90_days": expiring_90,
                "expiring_180_days": expiring_90_180,
                "already_expired": already_expired,
            },
        },
        "message": None,
    }


@router.patch("/cases/{case_id}/status")
async def update_retention_status(
    case_id: str,
    body: RetentionStatusUpdate,
    user: dict = Depends(get_current_user),
):
    """PATCH /api/retention/cases/{case_id}/status"""
    if body.retention_status not in VALID_STATUSES:
        raise HTTPException(status_code=422, detail="Invalid retention_status value")

    existing = await db.cases.find_one({"id": case_id}, {"_id": 0})
    if not existing:
        raise HTTPException(status_code=404, detail="Case not found")

    # Adviser access check
    if user.get("role") == "adviser" and existing.get("assigned_broker_id") != user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    await db.cases.update_one(
        {"id": case_id},
        {
            "$set": {
                "retention_status": body.retention_status,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        },
    )
    updated = await db.cases.find_one({"id": case_id}, {"_id": 0})
    return {"success": True, "data": updated, "message": None}


@router.get("/alerts")
async def retention_alerts(user: dict = Depends(get_current_user)):
    """
    GET /api/retention/alerts
    Returns cases expiring within 30 days where retention_status is
    'none', 'flagged', or unset.
    """
    today = datetime.now(timezone.utc).date()

    query = {
        **_base_query(user),
        "retention_status": {"$in": ["none", "flagged", None]},
    }

    raw_cases = await db.cases.find(query, {"_id": 0}).to_list(2000)

    alerts = []
    for c in raw_cases:
        expiry = _parse_date(c.get("rate_expiry_date"))
        if not expiry:
            continue
        days = (expiry - today).days
        if days > 30:
            continue

        client = await db.clients.find_one(
            {"id": c.get("client_id")}, {"_id": 0, "first_name": 1, "last_name": 1}
        )
        client_name = (
            f"{client['first_name']} {client['last_name']}" if client else "Unknown"
        )

        lender_name = "Not assigned"
        if c.get("lender_id"):
            lender = await db.lenders.find_one({"id": c["lender_id"]}, {"_id": 0, "name": 1})
            if lender:
                lender_name = lender["name"]

        alerts.append({
            "id": c["id"],
            "client_name": client_name,
            "lender_name": lender_name,
            "rate_expiry_date": _fmt_date(expiry),
            "days_until_expiry": days,
        })

    alerts.sort(key=lambda x: x["days_until_expiry"])
    return {"success": True, "data": {"alerts": alerts}, "message": None}
