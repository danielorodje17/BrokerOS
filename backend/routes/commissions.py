from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import StreamingResponse
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.pdfbase.pdfmetrics import stringWidth
from typing import Optional
import uuid
from datetime import datetime, timezone, timedelta

from .deps import db, get_current_user
from .models import CommissionCreate

router = APIRouter(prefix="/commissions", tags=["commissions"])


# ========== REMINDERS ENDPOINT ==========
@router.get("/reminders")
async def get_commission_reminders(user: dict = Depends(get_current_user)):
    """Get commission reminders - due soon (within 14 days) and overdue (past 30 days)"""
    today = datetime.now(timezone.utc).date()
    fourteen_days_later = today + timedelta(days=14)
    thirty_days_ago = today - timedelta(days=30)

    # Get all non-received commissions with expected_payment_date
    query = {
        "user_id": user["id"],
        "status": {"$ne": "received"},
        "expected_payment_date": {"$ne": None}
    }
    commissions = await db.commission_records.find(query, {"_id": 0}).to_list(1000)

    due_soon = []
    overdue = []

    for comm in commissions:
        expected_date_str = comm.get("expected_payment_date")
        if not expected_date_str:
            continue

        try:
            # Parse date - handle both YYYY-MM-DD and ISO format
            if "T" in expected_date_str:
                expected_date = datetime.fromisoformat(expected_date_str.replace("Z", "+00:00")).date()
            else:
                expected_date = datetime.strptime(expected_date_str, "%Y-%m-%d").date()
        except (ValueError, TypeError):
            continue

        # Get case and enrich with client/lender info
        case = await db.cases.find_one({"id": comm.get("case_id")}, {"_id": 0, "client_id": 1, "lender_id": 1})
        if not case:
            continue

        client = await db.clients.find_one({"id": case.get("client_id")}, {"_id": 0, "first_name": 1, "last_name": 1})
        lender = await db.lenders.find_one({"id": case.get("lender_id")}, {"_id": 0, "name": 1})

        client_name = f"{client['first_name']} {client['last_name']}" if client else "Unknown"
        lender_name = lender.get("name") if lender else "Unknown"

        # Format date as DD/MM/YYYY
        formatted_date = expected_date.strftime("%d/%m/%Y")

        # Check if due soon (between today and 14 days from now)
        if today <= expected_date <= fourteen_days_later:
            days_until_due = (expected_date - today).days
            due_soon.append({
                "id": comm.get("id"),
                "client_name": client_name,
                "lender_name": lender_name,
                "expected_amount": comm.get("expected_amount"),
                "expected_payment_date": formatted_date,
                "days_until_due": days_until_due
            })
        # Check if overdue (more than 30 days in the past)
        elif expected_date < thirty_days_ago:
            days_overdue = (today - expected_date).days
            overdue.append({
                "id": comm.get("id"),
                "client_name": client_name,
                "lender_name": lender_name,
                "expected_amount": comm.get("expected_amount"),
                "expected_payment_date": formatted_date,
                "days_overdue": days_overdue
            })

    # Sort by days (most urgent first)
    due_soon.sort(key=lambda x: x["days_until_due"])
    overdue.sort(key=lambda x: x["days_overdue"])

    return {
        "success": True,
        "data": {
            "due_soon": due_soon,
            "overdue": overdue
        }
    }


@router.get("")
async def list_commissions(
    status: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    user: dict = Depends(get_current_user)
):
    query = {"user_id": user["id"]}
    if status:
        query["status"] = status

    total = await db.commission_records.count_documents(query)
    commissions = await db.commission_records.find(query, {"_id": 0}).skip((page-1)*limit).limit(limit).to_list(limit)

    # Enrich with case info
    for comm in commissions:
        case = await db.cases.find_one({"id": comm.get("case_id")}, {"_id": 0, "client_id": 1, "lender_id": 1, "loan_amount": 1})
        if case:
            client = await db.clients.find_one({"id": case.get("client_id")}, {"_id": 0, "first_name": 1, "last_name": 1})
            lender = await db.lenders.find_one({"id": case.get("lender_id")}, {"_id": 0, "name": 1})
            comm["client_name"] = f"{client['first_name']} {client['last_name']}" if client else "Unknown"
            comm["lender_name"] = lender["name"] if lender else "Unknown"
            comm["loan_amount"] = case.get("loan_amount")

    return {"commissions": commissions, "total": total, "page": page, "limit": limit}


@router.post("")
async def create_commission(data: CommissionCreate, user: dict = Depends(get_current_user)):
    # Verify case exists
    case = await db.cases.find_one({"id": data.case_id, "assigned_broker_id": user["id"]})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    comm_doc = data.model_dump()
    comm_doc["id"] = str(uuid.uuid4())
    comm_doc["user_id"] = user["id"]
    comm_doc["created_at"] = datetime.now(timezone.utc).isoformat()
    comm_doc["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.commission_records.insert_one(comm_doc)
    comm_doc.pop("_id", None)
    return comm_doc


@router.put("/{commission_id}")
async def update_commission(commission_id: str, data: CommissionCreate, user: dict = Depends(get_current_user)):
    update_doc = data.model_dump()
    update_doc["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await db.commission_records.update_one(
        {"id": commission_id, "user_id": user["id"]},
        {"$set": update_doc}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Commission not found")
    return await db.commission_records.find_one({"id": commission_id}, {"_id": 0})


@router.delete("/{commission_id}")
async def delete_commission(commission_id: str, user: dict = Depends(get_current_user)):
    result = await db.commission_records.delete_one({"id": commission_id, "user_id": user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Commission not found")
    return {"message": "Commission deleted"}


# ========== INVOICE GENERATION ==========
def format_currency_pdf(value):
    """Format currency for PDF display"""
    if not value:
        return "£0.00"
    return f"£{value:,.2f}"


def generate_invoice_pdf(invoice_data: dict) -> BytesIO:
    """Generate a professional PDF invoice"""
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Colors
    navy = colors.HexColor("#0A2342")
    grey = colors.HexColor("#6B7280")
    dark = colors.HexColor("#111827")

    # Top left: BrokerOS branding
    c.setFillColor(navy)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(40, height - 50, "BrokerOS")
    c.setFillColor(grey)
    c.setFont("Helvetica", 10)
    c.drawString(40, height - 65, "Invoice")

    # Top right: Invoice details
    c.setFillColor(dark)
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(width - 40, height - 50, f"Invoice Number: {invoice_data['invoice_number']}")
    c.setFont("Helvetica", 10)
    c.drawRightString(width - 40, height - 65, f"Invoice Date: {invoice_data['invoice_date']}")
    c.drawRightString(width - 40, height - 80, f"Payment Due: {invoice_data['payment_due_date']}")

    # Divider line
    c.setStrokeColor(colors.HexColor("#E5E7EB"))
    c.line(40, height - 100, width - 40, height - 100)

    # FROM section
    y_pos = height - 130
    c.setFillColor(grey)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(40, y_pos, "FROM")
    c.setFillColor(dark)
    c.setFont("Helvetica", 11)
    y_pos -= 18
    c.drawString(40, y_pos, invoice_data['broker_name'])
    y_pos -= 15
    c.setFont("Helvetica", 10)
    c.drawString(40, y_pos, f"FCA Number: {invoice_data['fca_number'] or 'N/A'}")

    # TO section
    y_pos -= 35
    c.setFillColor(grey)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(40, y_pos, "TO")
    c.setFillColor(dark)
    c.setFont("Helvetica", 11)
    y_pos -= 18
    c.drawString(40, y_pos, invoice_data['lender_name'] or "N/A")

    # RE section (Case details)
    y_pos -= 35
    c.setFillColor(grey)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(40, y_pos, "RE")
    c.setFillColor(dark)
    c.setFont("Helvetica", 11)
    y_pos -= 18
    c.drawString(40, y_pos, f"Client: {invoice_data['client_name']}")
    y_pos -= 15
    c.setFont("Helvetica", 10)
    c.drawString(40, y_pos, f"Case Reference: {invoice_data['case_id']}")
    y_pos -= 15
    c.drawString(40, y_pos, f"Loan Amount: {format_currency_pdf(invoice_data['loan_amount'])}")

    # Fee table
    y_pos -= 50

    # Table header
    c.setFillColor(colors.HexColor("#F9FAFB"))
    c.rect(40, y_pos - 5, width - 80, 25, fill=True, stroke=False)
    c.setFillColor(grey)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(50, y_pos + 5, "DESCRIPTION")
    c.drawRightString(width - 50, y_pos + 5, "AMOUNT")

    # Table row
    y_pos -= 35
    c.setFillColor(dark)
    c.setFont("Helvetica", 10)
    c.drawString(50, y_pos, "Mortgage Arrangement / Proc Fee")
    c.drawRightString(width - 50, y_pos, format_currency_pdf(invoice_data['commission_amount']))

    # Bottom border
    c.setStrokeColor(colors.HexColor("#E5E7EB"))
    c.line(40, y_pos - 15, width - 40, y_pos - 15)

    # Total row
    y_pos -= 40
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y_pos, "Total Due")
    c.drawRightString(width - 50, y_pos, format_currency_pdf(invoice_data['commission_amount']))

    # Footer
    c.setFillColor(grey)
    c.setFont("Helvetica-Oblique", 9)
    footer_text = f"This invoice is issued by {invoice_data['broker_name']}, FCA Number {invoice_data['fca_number'] or 'N/A'}. Payment should be made within 30 days of the date of this invoice."

    # Word wrap footer
    max_width = width - 80
    words = footer_text.split()
    lines = []
    current_line = ""
    for word in words:
        test_line = current_line + " " + word if current_line else word
        if stringWidth(test_line, "Helvetica-Oblique", 9) < max_width:
            current_line = test_line
        else:
            lines.append(current_line)
            current_line = word
    if current_line:
        lines.append(current_line)

    y_pos = 80
    for line in lines:
        c.drawString(40, y_pos, line)
        y_pos -= 12

    c.save()
    buffer.seek(0)
    return buffer


@router.get("/{commission_id}/invoice")
async def generate_commission_invoice(commission_id: str, user: dict = Depends(get_current_user)):
    """Generate and download a PDF invoice for a commission record"""
    # Get commission record
    commission = await db.commission_records.find_one({"id": commission_id, "user_id": user["id"]}, {"_id": 0})
    if not commission:
        raise HTTPException(status_code=404, detail="Commission not found")

    # Get case details
    case = await db.cases.find_one({"id": commission.get("case_id")}, {"_id": 0})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Get client details
    client = await db.clients.find_one({"id": case.get("client_id")}, {"_id": 0})
    client_name = f"{client['first_name']} {client['last_name']}" if client else "Unknown Client"

    # Get lender details
    lender = await db.lenders.find_one({"id": case.get("lender_id")}, {"_id": 0})
    lender_name = lender.get("name") if lender else "Unknown Lender"

    # Get or create invoice sequence for this broker
    sequence = await db.invoice_sequences.find_one({"user_id": user["id"]})
    current_year = datetime.now(timezone.utc).year

    if sequence:
        if sequence.get("year") != current_year:
            # Reset sequence for new year
            next_num = 1
            await db.invoice_sequences.update_one(
                {"user_id": user["id"]},
                {"$set": {"year": current_year, "last_number": 1}}
            )
        else:
            next_num = sequence.get("last_number", 0) + 1
            await db.invoice_sequences.update_one(
                {"user_id": user["id"]},
                {"$set": {"last_number": next_num}}
            )
    else:
        next_num = 1
        await db.invoice_sequences.insert_one({
            "user_id": user["id"],
            "year": current_year,
            "last_number": 1
        })

    invoice_number = f"INV-{current_year}-{next_num:04d}"

    # Persist invoice_number to the commission record (for searching by invoice ref)
    await db.commission_records.update_one(
        {"id": commission_id, "user_id": user["id"]},
        {"$set": {"invoice_number": invoice_number, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )

    # Prepare invoice data
    invoice_data = {
        "invoice_number": invoice_number,
        "invoice_date": datetime.now(timezone.utc).strftime("%d/%m/%Y"),
        "payment_due_date": (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%d/%m/%Y"),
        "broker_name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or user.get('email', 'Broker'),
        "fca_number": user.get("fca_number"),
        "lender_name": lender_name,
        "client_name": client_name,
        "case_id": case.get("id"),
        "loan_amount": case.get("loan_amount"),
        "commission_amount": commission.get("expected_amount", 0)
    }

    # Generate PDF
    pdf_buffer = generate_invoice_pdf(invoice_data)

    # Return as streaming response
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={invoice_number}.pdf",
            "X-Invoice-Number": invoice_number
        }
    )
