"""
routes/ai.py — Phase 2 AI features powered by Claude via emergentintegrations.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import uuid
import os
import json
import re
import logging

from emergentintegrations.llm.chat import LlmChat, UserMessage
from .deps import db, get_current_user

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
