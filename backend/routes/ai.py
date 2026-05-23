"""
routes/ai.py — Phase 2 AI features powered by Claude via emergentintegrations.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import uuid
import os

from emergentintegrations.llm.chat import LlmChat, UserMessage
from .deps import db, get_current_user

router = APIRouter(prefix="/ai", tags=["ai"])

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
