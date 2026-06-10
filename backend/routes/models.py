# Pydantic models for request/response validation
from pydantic import BaseModel, Field, EmailStr
from typing import Optional


class UserRegister(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    fca_number: Optional[str] = None
    current_password: Optional[str] = None
    new_password: Optional[str] = None


class ClientCreate(BaseModel):
    first_name: str
    last_name: str
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    date_of_birth: Optional[str] = None
    ni_number: Optional[str] = None
    employment_type: Optional[str] = "employed"
    employer_name: Optional[str] = None
    annual_income: Optional[float] = None
    credit_profile: Optional[str] = "clean"
    consent_date: Optional[str] = None


class CaseCreate(BaseModel):
    client_id: str
    mortgage_type: str = "residential"
    stage: str = "new_enquiry"
    loan_amount: Optional[float] = None
    property_value: Optional[float] = None
    term_years: Optional[int] = None
    lender_id: Optional[str] = None
    rate_type: Optional[str] = None
    rate_percent: Optional[float] = None
    rate_expiry_date: Optional[str] = None
    expected_completion_date: Optional[str] = None
    notes: Optional[str] = None
    retention_status: Optional[str] = "none"


class LenderCreate(BaseModel):
    name: str
    bdm_name: Optional[str] = None
    bdm_email: Optional[str] = None
    bdm_phone: Optional[str] = None
    proc_fee_purchase: Optional[float] = None
    proc_fee_remortgage: Optional[float] = None
    proc_fee_btl: Optional[float] = None
    min_loan: Optional[float] = None
    max_loan: Optional[float] = None
    max_ltv: Optional[float] = None
    min_income: Optional[float] = None
    accepts_self_employed: bool = False
    accepts_contractors: bool = False
    accepts_adverse: bool = False
    avg_processing_days: Optional[int] = None
    broker_success_rate: Optional[float] = None
    notes: Optional[str] = None


class CommissionCreate(BaseModel):
    case_id: str
    expected_amount: Optional[float] = None
    expected_payment_date: Optional[str] = None
    received_amount: Optional[float] = None
    received_date: Optional[str] = None
    status: str = "pending"
    clawback_risk_until: Optional[str] = None


class NoteCreate(BaseModel):
    case_id: str
    content: str = Field(..., max_length=2000)


class ForgotPassword(BaseModel):
    email: EmailStr


class ResetPassword(BaseModel):
    token: str
    new_password: str
