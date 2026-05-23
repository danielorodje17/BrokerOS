"""
routes/ai.py — Phase 2 AI features powered by Claude via emergentintegrations.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta, date
import uuid
import os
import json
import re
import logging

from emergentintegrations.llm.chat import LlmChat, UserMessage
from .deps import db, get_current_user, get_case_filter

router = APIRouter(prefix="/ai", tags=["ai"])
logger = logging.getLogger(__name__)

EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "")


# ─────────────────────────────────────────────────────────
# Score helpers
# ─────────────────────────────────────────────────────────

_EMPLOYMENT_SCORES = {
    "employed": 30,
    "contractor": 22,
    "self_employed": 18,
    "self-employed": 18,
    "retired": 15,
}

_CREDIT_SCORES = {
    "clean": 30,
    "minor_issues": 18,
    "minor issues": 18,
    "adverse": 5,
}


def _income_pts(income) -> int:
    if not income:
        return 5
    income = float(income)
    if income > 75_000:
        return 25
    if income >= 50_000:
        return 20
    if income >= 35_000:
        return 15
    if income >= 20_000:
        return 10
    return 5


def _classify(score: int) -> tuple[str, str]:
    """Returns (classification, colour)"""
    if score >= 80:
        return "Strong", "green"
    if score >= 60:
        return "Good", "teal"
    if score >= 40:
        return "Fair", "amber"
    return "Weak", "red"


# ─────────────────────────────────────────────────────────
# Request / Response schemas
# ─────────────────────────────────────────────────────────

class BorrowerScoreRequest(BaseModel):
    client_id: str


# ─────────────────────────────────────────────────────────
# Endpoint
# ─────────────────────────────────────────────────────────

@router.post("/borrower-score")
async def borrower_score(body: BorrowerScoreRequest, user: dict = Depends(get_current_user)):
    """
    POST /api/ai/borrower-score
    Rule-based score (0-100) + Claude-generated plain-English summary.
    """
    client = await db.clients.find_one({"id": body.client_id}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # ── Score components ──────────────────────────────────
    employment_type = (client.get("employment_type") or "").lower()
    emp_pts = _EMPLOYMENT_SCORES.get(employment_type, 10)

    income = client.get("annual_income")
    inc_pts = _income_pts(income)

    credit_profile = (client.get("credit_profile") or "").lower()
    credit_pts = _CREDIT_SCORES.get(credit_profile, 5)

    gdpr_consent = bool(client.get("gdpr_consent"))
    gdpr_pts = 10 if gdpr_consent else 0

    doc_count = await db.documents.count_documents({"client_id": body.client_id})
    doc_pts = 5 if doc_count >= 1 else 0

    total_score = emp_pts + inc_pts + credit_pts + gdpr_pts + doc_pts
    classification, colour = _classify(total_score)

    # ── Build breakdown ───────────────────────────────────
    breakdown = {
        "employment": {"points": emp_pts, "max": 30,
                       "label": employment_type.replace("_", " ").title() or "Unknown"},
        "income":     {"points": inc_pts,  "max": 25,
                       "label": f"£{int(income):,}" if income else "Not stated"},
        "credit":     {"points": credit_pts, "max": 30,
                       "label": credit_profile.replace("_", " ").title() or "Unknown"},
        "gdpr":       {"points": gdpr_pts, "max": 10,
                       "label": "Yes" if gdpr_consent else "No"},
        "documents":  {"points": doc_pts,  "max": 5,
                       "label": f"{doc_count} document{'s' if doc_count != 1 else ''} on file"},
    }

    # ── Claude summary ────────────────────────────────────
    summary = ""
    try:
        prompt = (
            f"You are a UK mortgage broker assistant. A client has received a Borrower Strength "
            f"Score of {total_score}/100 ({classification}).\n\n"
            f"Score breakdown:\n"
            f"- Employment: {breakdown['employment']['label']} ({emp_pts}pts)\n"
            f"- Income: {breakdown['income']['label']} ({inc_pts}pts)\n"
            f"- Credit profile: {breakdown['credit']['label']} ({credit_pts}pts)\n"
            f"- Consent on file: {breakdown['gdpr']['label']} ({gdpr_pts}pts)\n"
            f"- Documents uploaded: {breakdown['documents']['label']} ({doc_pts}pts)\n\n"
            f"Write a 2-3 sentence plain-English summary for the broker explaining this score. "
            f"Identify the strongest factor and the main area for improvement. "
            f"Be direct and professional. Do not use bullet points."
        )

        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=str(uuid.uuid4()),
            system_message="You are a UK mortgage broker assistant providing concise, professional analysis.",
        ).with_model("anthropic", "claude-sonnet-4-5")

        summary = await chat.send_message(UserMessage(text=prompt))
    except Exception as e:
        # Gracefully degrade — return score without AI summary
        summary = f"Score computed: {total_score}/100 ({classification}). AI summary unavailable."

    return {
        "success": True,
        "data": {
            "score": total_score,
            "classification": classification,
            "colour": colour,
            "summary": summary,
            "breakdown": breakdown,
        },
    }


# ─────────────────────────────────────────────────────────
# AI Feature 2: Lender Matching Engine
# ─────────────────────────────────────────────────────────

class LenderMatchRequest(BaseModel):
    case_id: str


def _hard_filter_lenders(case: dict, client: dict, lenders: list) -> list:
    """Eliminate lenders that cannot lend on this case."""
    ltv = case.get("ltv")
    loan_amount = case.get("loan_amount")
    employment = (client.get("employment_type") or "").lower() if client else ""
    credit = (client.get("credit_profile") or "").lower() if client else ""

    eligible = []
    for lender in lenders:
        # LTV check
        if ltv is not None and lender.get("max_ltv") is not None and lender["max_ltv"] < ltv:
            continue
        # Loan size checks
        if loan_amount is not None:
            if lender.get("min_loan") is not None and lender["min_loan"] > loan_amount:
                continue
            if lender.get("max_loan") is not None and lender["max_loan"] < loan_amount:
                continue
        # Employment checks
        if employment in ("self_employed", "self-employed") and not lender.get("accepts_self_employed", False):
            continue
        if employment == "contractor" and not lender.get("accepts_contractors", False):
            continue
        # Credit check
        if credit == "adverse" and not lender.get("accepts_adverse", False):
            continue
        eligible.append(lender)
    return eligible


def _fallback_matches(eligible: list) -> list:
    """Return eligible lenders sorted by proc_fee_purchase desc when Claude fails."""
    sorted_lenders = sorted(
        eligible,
        key=lambda x: (x.get("proc_fee_purchase") or 0),
        reverse=True,
    )
    return [
        {
            "rank": idx + 1,
            "lender_id": l["id"],
            "lender_name": l["name"],
            "proc_fee_purchase": l.get("proc_fee_purchase") or 0,
            "max_ltv": l.get("max_ltv") or 0,
            "avg_processing_days": l.get("avg_processing_days") or 0,
            "broker_success_rate": l.get("broker_success_rate") or 0,
            "reason": "AI ranking unavailable",
            "watch_out": "None",
        }
        for idx, l in enumerate(sorted_lenders)
    ]


def _parse_claude_json(raw: str):
    """Extract JSON array from Claude's response, tolerating code fences."""
    if not raw:
        return None
    raw = raw.strip()
    # Strip markdown code fences
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    # Find the first '[' and matching last ']'
    start = raw.find("[")
    end = raw.rfind("]")
    if start == -1 or end == -1 or end <= start:
        return None
    try:
        return json.loads(raw[start:end + 1])
    except json.JSONDecodeError:
        return None


@router.post("/lender-match")
async def lender_match(body: LenderMatchRequest, user: dict = Depends(get_current_user)):
    """
    POST /api/ai/lender-match
    Returns an AI-ranked shortlist of suitable lenders from the broker's panel.
    """
    case = await db.cases.find_one({"id": body.case_id}, {"_id": 0})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Adviser access check
    if user.get("role") == "adviser" and case.get("assigned_broker_id") != user["id"]:
        raise HTTPException(status_code=403, detail="Access denied")

    client = await db.clients.find_one({"id": case.get("client_id")}, {"_id": 0}) or {}
    all_lenders = await db.lenders.find({"user_id": user["id"]}, {"_id": 0}).to_list(1000)
    total_lenders = len(all_lenders)

    eligible = _hard_filter_lenders(case, client, all_lenders)

    if not eligible:
        return {
            "success": True,
            "data": {
                "matches": [],
                "eligible_count": 0,
                "total_lenders": total_lenders,
                "message": "No lenders on your panel match this case's criteria. Consider reviewing the case details or expanding your lender panel.",
            },
        }

    # ── Build Claude prompt ───────────────────────────────
    lender_lines = []
    for l in eligible:
        lender_lines.append(
            f"- {l['name']} | Proc fee (purchase) {l.get('proc_fee_purchase') or 0}% "
            f"| Max LTV {l.get('max_ltv') or 0}% "
            f"| Avg processing {l.get('avg_processing_days') or 0} days "
            f"| Broker success rate {l.get('broker_success_rate') or 0}% "
            f"| Accepts SE: {'yes' if l.get('accepts_self_employed') else 'no'} "
            f"| Accepts adverse: {'yes' if l.get('accepts_adverse') else 'no'}"
        )

    prompt = (
        "You are an experienced UK mortgage broker assistant. Rank the following lenders for this mortgage case and provide commentary on each.\n\n"
        "CASE DETAILS:\n"
        f"- Mortgage type: {case.get('mortgage_type', 'n/a')}\n"
        f"- Loan amount: £{int(case.get('loan_amount') or 0):,}\n"
        f"- Property value: £{int(case.get('property_value') or 0):,}\n"
        f"- LTV: {case.get('ltv', 'n/a')}%\n"
        f"- Client employment: {client.get('employment_type', 'n/a')}\n"
        f"- Client annual income: £{int(client.get('annual_income') or 0):,}\n"
        f"- Client credit profile: {client.get('credit_profile', 'n/a')}\n"
        f"- Term: {case.get('term_years', 'n/a')} years\n\n"
        "ELIGIBLE LENDERS:\n"
        + "\n".join(lender_lines)
        + "\n\nRank these lenders from best to worst fit for this case. Consider: proc fee, processing speed, success rate, and fit with the client profile.\n\n"
        "For each lender provide:\n"
        "- rank (integer, 1 = best)\n"
        "- reason (one sentence: why this lender suits this case)\n"
        "- watch_out (one sentence: a specific risk or consideration — or exactly the string \"None\" if no concerns)\n\n"
        "Respond in valid JSON only. No preamble, no markdown, no explanation outside the JSON.\n"
        "Format: [{\"lender_name\": \"\", \"rank\": 1, \"reason\": \"\", \"watch_out\": \"\"}]"
    )

    # ── Claude ranking call ───────────────────────────────
    matches = None
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=str(uuid.uuid4()),
            system_message="You are a UK mortgage broker assistant providing concise lender-fit analysis. Always respond with valid JSON arrays only.",
        ).with_model("anthropic", "claude-sonnet-4-5")

        raw = await chat.send_message(UserMessage(text=prompt))
        parsed = _parse_claude_json(raw)

        if parsed and isinstance(parsed, list):
            # Index eligible lenders by name for merging
            by_name = {l["name"]: l for l in eligible}
            merged = []
            for item in parsed:
                name = item.get("lender_name")
                lender = by_name.get(name)
                if not lender:
                    continue
                merged.append({
                    "rank": int(item.get("rank", 99)),
                    "lender_id": lender["id"],
                    "lender_name": lender["name"],
                    "proc_fee_purchase": lender.get("proc_fee_purchase") or 0,
                    "max_ltv": lender.get("max_ltv") or 0,
                    "avg_processing_days": lender.get("avg_processing_days") or 0,
                    "broker_success_rate": lender.get("broker_success_rate") or 0,
                    "reason": item.get("reason", ""),
                    "watch_out": item.get("watch_out", "None"),
                })
            # Sort by rank ascending
            merged.sort(key=lambda x: x["rank"])
            # Re-number sequentially in case of duplicates/gaps
            for idx, m in enumerate(merged):
                m["rank"] = idx + 1
            if merged:
                matches = merged
    except Exception as e:
        logger.exception("Claude lender-match call failed: %s", e)

    if matches is None:
        matches = _fallback_matches(eligible)

    return {
        "success": True,
        "data": {
            "matches": matches,
            "eligible_count": len(eligible),
            "total_lenders": total_lenders,
            "message": None,
        },
    }


# ─────────────────────────────────────────────────────────
# AI Feature 3: Daily Briefing
# ─────────────────────────────────────────────────────────

ACTIVE_STAGES = [
    "new_enquiry", "fact_find", "aip_submitted", "aip_received",
    "full_application", "valuation", "offer", "exchange",
]

_STAGE_LABELS = {
    "new_enquiry": "New Enquiry",
    "fact_find": "Fact Find",
    "aip_submitted": "AIP Submitted",
    "aip_received": "AIP Received",
    "full_application": "Full Application",
    "valuation": "Valuation",
    "offer": "Mortgage Offer",
    "exchange": "Exchange",
    "completion": "Completion",
    "on_hold": "On Hold",
    "declined": "Declined",
}


def _parse_iso_date(value):
    if not value:
        return None
    try:
        if "T" in str(value):
            return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


@router.get("/daily-briefing")
async def daily_briefing(probe: bool = False, user: dict = Depends(get_current_user)):
    """
    GET /api/ai/daily-briefing
    Personalised AI briefing cached per user per day.
    If ?probe=true, returns the cached briefing if present or {cached:false, briefing:null}
    without calling Claude — used by the Dashboard to decide whether to show the button.
    """
    today = datetime.now(timezone.utc).date()
    today_iso = today.isoformat()

    # ── Cache check ──────────────────────────────────────
    cached = await db.daily_briefings.find_one(
        {"user_id": user["id"], "date": today_iso},
        {"_id": 0},
    )
    if cached:
        return {
            "briefing": cached["briefing"],
            "generated_at": cached["generated_at"],
            "cached": True,
        }
    if probe:
        return {"briefing": None, "generated_at": None, "cached": False}

    # ── Fetch active cases ───────────────────────────────
    case_filter = {**get_case_filter(user), "stage": {"$in": ACTIVE_STAGES}}
    cases = await db.cases.find(case_filter, {"_id": 0}).to_list(500)

    case_lines = []
    for c in cases[:30]:  # cap context size
        client = await db.clients.find_one(
            {"id": c.get("client_id")},
            {"_id": 0, "first_name": 1, "last_name": 1},
        )
        client_name = (
            f"{client['first_name']} {client['last_name']}" if client else "Unknown"
        )
        lender_name = "no lender"
        if c.get("lender_id"):
            lender = await db.lenders.find_one(
                {"id": c["lender_id"]}, {"_id": 0, "name": 1}
            )
            if lender:
                lender_name = lender["name"]

        # days in current stage
        stage_dt = c.get("stage_updated_at") or c.get("created_at")
        days_in_stage = "?"
        if stage_dt:
            try:
                d = datetime.fromisoformat(str(stage_dt).replace("Z", "+00:00")).date()
                days_in_stage = (today - d).days
            except (ValueError, TypeError):
                pass

        case_lines.append(
            f"- {client_name}: {_STAGE_LABELS.get(c.get('stage'), c.get('stage'))} "
            f"({days_in_stage} days), lender: {lender_name}"
        )

    # ── Commission alerts (overdue + due this week) ──────
    fourteen_days_later = today + timedelta(days=14)
    thirty_days_ago = today - timedelta(days=30)

    comm_query = {
        "user_id": user["id"],
        "status": {"$ne": "received"},
        "expected_payment_date": {"$ne": None},
    }
    pending_comms = await db.commission_records.find(comm_query, {"_id": 0}).to_list(1000)

    overdue_count = 0
    overdue_total = 0.0
    due_week_count = 0
    due_week_total = 0.0
    for c in pending_comms:
        d = _parse_iso_date(c.get("expected_payment_date"))
        if not d:
            continue
        amount = c.get("expected_amount") or 0
        if today <= d <= fourteen_days_later:
            due_week_count += 1
            due_week_total += amount
        elif d < thirty_days_ago:
            overdue_count += 1
            overdue_total += amount

    # ── Clawback risk within 60 days ─────────────────────
    sixty_days_later = today + timedelta(days=60)
    sixty_days_iso = sixty_days_later.isoformat()
    clawback_records = await db.commission_records.find(
        {
            "user_id": user["id"],
            "clawback_risk_until": {
                "$ne": None,
                "$gt": today_iso,
                "$lte": sixty_days_iso,
            },
        },
        {"_id": 0},
    ).sort("clawback_risk_until", 1).to_list(50)

    clawback_lines = []
    for c in clawback_records:
        case = await db.cases.find_one(
            {"id": c.get("case_id")}, {"_id": 0, "client_id": 1}
        )
        client_name = "Unknown"
        if case:
            client = await db.clients.find_one(
                {"id": case.get("client_id")},
                {"_id": 0, "first_name": 1, "last_name": 1},
            )
            if client:
                client_name = f"{client['first_name']} {client['last_name']}"
        risk_date = _parse_iso_date(c.get("clawback_risk_until"))
        days_remaining = (risk_date - today).days if risk_date else "?"
        clawback_lines.append(
            f"- {client_name}: clawback until {c.get('clawback_risk_until')} ({days_remaining} days remaining)"
        )

    # ── Build prompt ─────────────────────────────────────
    today_display = today.strftime("%A, %d %B %Y")
    pipeline_block = "\n".join(case_lines) if case_lines else "No active cases."
    clawback_block = "\n".join(clawback_lines) if clawback_lines else "None within 60 days."

    prompt = (
        "You are a UK mortgage broker assistant generating a daily briefing.\n\n"
        f"Today is {today_display}. The broker has {len(cases)} active cases.\n\n"
        "PIPELINE SNAPSHOT:\n"
        f"{pipeline_block}\n\n"
        "COMMISSION ALERTS:\n"
        f"- Overdue: {overdue_count} commissions totalling £{overdue_total:,.0f}\n"
        f"- Due this week: {due_week_count} commissions totalling £{due_week_total:,.0f}\n\n"
        "CLAWBACK RISK (expiring within 60 days):\n"
        f"{clawback_block}\n\n"
        "Generate a concise daily briefing for the broker. Structure it as:\n"
        "1. A one-sentence overall summary of where the pipeline stands today\n"
        "2. \"Today's Priorities\" — up to 3 specific actions the broker should take today, each as one sentence\n"
        "3. \"Watch List\" — up to 3 cases or commissions that need attention this week, each as one sentence\n"
        "4. One brief closing observation or encouragement\n\n"
        "Be direct, specific, and professional. Use British English. Name specific clients and lenders where relevant. Do not use generic filler phrases."
    )

    # ── Call Claude ──────────────────────────────────────
    briefing_text = ""
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=str(uuid.uuid4()),
            system_message="You are a UK mortgage broker assistant writing personalised, professional daily briefings.",
        ).with_model("anthropic", "claude-sonnet-4-5")

        briefing_text = await chat.send_message(UserMessage(text=prompt))
    except Exception as e:
        logger.exception("Claude daily-briefing call failed: %s", e)
        briefing_text = (
            f"Daily briefing unavailable (AI service error). "
            f"You have {len(cases)} active cases, {overdue_count} overdue commissions, "
            f"and {due_week_count} due this week."
        )

    generated_at = datetime.now(timezone.utc).isoformat()

    # ── Cache it ─────────────────────────────────────────
    await db.daily_briefings.update_one(
        {"user_id": user["id"], "date": today_iso},
        {
            "$set": {
                "user_id": user["id"],
                "date": today_iso,
                "briefing": briefing_text,
                "generated_at": generated_at,
            }
        },
        upsert=True,
    )

    return {
        "briefing": briefing_text,
        "generated_at": generated_at,
        "cached": False,
    }


@router.delete("/daily-briefing")
async def regenerate_daily_briefing(user: dict = Depends(get_current_user)):
    """Clear today's cached briefing so the next GET regenerates it."""
    today_iso = datetime.now(timezone.utc).date().isoformat()
    await db.daily_briefings.delete_one({"user_id": user["id"], "date": today_iso})
    return {"success": True, "message": "Briefing cache cleared"}
