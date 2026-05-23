from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, APIRouter, HTTPException, Request, Response, Depends, File, UploadFile, Query
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.middleware.cors import CORSMiddleware
from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Table, TableStyle
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
import os
import logging
import bcrypt
import jwt
import uuid
import secrets
import requests
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ.get('DB_NAME', 'brokeros')]

# JWT Configuration
JWT_SECRET = os.environ.get('JWT_SECRET', 'brokeros_secure_jwt_secret_key_64chars_0123456789abcdef0123456789')
JWT_ALGORITHM = "HS256"

# Storage Configuration
STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")
APP_NAME = "brokeros"
storage_key = None

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="BrokerOS API")
api_router = APIRouter(prefix="/api")

# ========== PASSWORD HASHING ==========
def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

# ========== JWT TOKEN MANAGEMENT ==========
def create_access_token(user_id: str, email: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=15),
        "type": "access"
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=7),
        "type": "refresh"
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

# ========== AUTH HELPER ==========
async def get_current_user(request: Request) -> dict:
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        user["id"] = str(user["_id"])
        user.pop("_id", None)
        user.pop("password_hash", None)
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ========== STORAGE FUNCTIONS ==========
def init_storage():
    global storage_key
    if storage_key:
        return storage_key
    if not EMERGENT_KEY:
        logger.warning("EMERGENT_LLM_KEY not set, storage disabled")
        return None
    try:
        resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_KEY}, timeout=30)
        resp.raise_for_status()
        storage_key = resp.json()["storage_key"]
        return storage_key
    except Exception as e:
        logger.error(f"Storage init failed: {e}")
        return None

def put_object(path: str, data: bytes, content_type: str) -> dict:
    key = init_storage()
    if not key:
        raise HTTPException(status_code=503, detail="Storage not available")
    resp = requests.put(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key, "Content-Type": content_type},
        data=data, timeout=120
    )
    resp.raise_for_status()
    return resp.json()

def get_object(path: str) -> tuple:
    key = init_storage()
    if not key:
        raise HTTPException(status_code=503, detail="Storage not available")
    resp = requests.get(
        f"{STORAGE_URL}/objects/{path}",
        headers={"X-Storage-Key": key}, timeout=60
    )
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")

# ========== PYDANTIC MODELS ==========
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

# ========== AUTH ENDPOINTS ==========
@api_router.post("/auth/register")
async def register(user_data: UserRegister, response: Response):
    email = user_data.email.lower()
    existing = await db.users.find_one({"email": email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed = hash_password(user_data.password)
    user_doc = {
        "email": email,
        "password_hash": hashed,
        "first_name": user_data.first_name,
        "last_name": user_data.last_name,
        "fca_number": None,
        "role": "adviser",
        "team_id": None,
        "onboarding_completed": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "last_login": datetime.now(timezone.utc).isoformat()
    }
    result = await db.users.insert_one(user_doc)
    user_id = str(result.inserted_id)
    
    access_token = create_access_token(user_id, email)
    refresh_token = create_refresh_token(user_id)
    
    response.set_cookie(key="access_token", value=access_token, httponly=True, secure=False, samesite="lax", max_age=900, path="/")
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=False, samesite="lax", max_age=604800, path="/")
    
    return {
        "id": user_id,
        "email": email,
        "first_name": user_data.first_name,
        "last_name": user_data.last_name,
        "role": "adviser",
        "onboarding_completed": False
    }

@api_router.post("/auth/login")
async def login(user_data: UserLogin, request: Request, response: Response):
    email = user_data.email.lower()
    ip = request.client.host
    identifier = f"{ip}:{email}"
    
    # Check brute force
    attempt = await db.login_attempts.find_one({"identifier": identifier})
    if attempt and attempt.get("count", 0) >= 5:
        lockout_until = attempt.get("lockout_until")
        if lockout_until and datetime.fromisoformat(lockout_until) > datetime.now(timezone.utc):
            raise HTTPException(status_code=429, detail="Too many login attempts. Try again in 15 minutes.")
    
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(user_data.password, user["password_hash"]):
        # Increment failed attempts
        await db.login_attempts.update_one(
            {"identifier": identifier},
            {
                "$inc": {"count": 1},
                "$set": {"lockout_until": (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()}
            },
            upsert=True
        )
        raise HTTPException(status_code=401, detail="Invalid email or password")
    
    # Clear failed attempts
    await db.login_attempts.delete_one({"identifier": identifier})
    
    # Update last login
    await db.users.update_one({"_id": user["_id"]}, {"$set": {"last_login": datetime.now(timezone.utc).isoformat()}})
    
    user_id = str(user["_id"])
    access_token = create_access_token(user_id, email)
    refresh_token = create_refresh_token(user_id)
    
    response.set_cookie(key="access_token", value=access_token, httponly=True, secure=False, samesite="lax", max_age=900, path="/")
    response.set_cookie(key="refresh_token", value=refresh_token, httponly=True, secure=False, samesite="lax", max_age=604800, path="/")
    
    return {
        "id": user_id,
        "email": user["email"],
        "first_name": user.get("first_name", ""),
        "last_name": user.get("last_name", ""),
        "role": user.get("role", "adviser"),
        "fca_number": user.get("fca_number"),
        "onboarding_completed": user.get("onboarding_completed", False)
    }

@api_router.post("/auth/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"message": "Logged out successfully"}

@api_router.get("/auth/me")
async def get_me(user: dict = Depends(get_current_user)):
    return user

@api_router.post("/auth/refresh")
async def refresh_token(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(status_code=401, detail="No refresh token")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await db.users.find_one({"_id": ObjectId(payload["sub"])})
        if not user:
            raise HTTPException(status_code=401, detail="User not found")
        
        user_id = str(user["_id"])
        access_token = create_access_token(user_id, user["email"])
        response.set_cookie(key="access_token", value=access_token, httponly=True, secure=False, samesite="lax", max_age=900, path="/")
        return {"message": "Token refreshed"}
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Refresh token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

@api_router.post("/auth/forgot-password")
async def forgot_password(data: ForgotPassword):
    email = data.email.lower()
    user = await db.users.find_one({"email": email})
    if user:
        token = secrets.token_urlsafe(32)
        await db.password_reset_tokens.insert_one({
            "token": token,
            "user_id": str(user["_id"]),
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=1),
            "used": False
        })
        logger.info(f"Password reset link: /reset-password?token={token}")
    return {"message": "If the email exists, a reset link has been sent"}

@api_router.post("/auth/reset-password")
async def reset_password(data: ResetPassword):
    reset_doc = await db.password_reset_tokens.find_one({"token": data.token, "used": False})
    if not reset_doc:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")
    
    if datetime.fromisoformat(str(reset_doc["expires_at"])) < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Reset token expired")
    
    hashed = hash_password(data.new_password)
    await db.users.update_one({"_id": ObjectId(reset_doc["user_id"])}, {"$set": {"password_hash": hashed}})
    await db.password_reset_tokens.update_one({"token": data.token}, {"$set": {"used": True}})
    return {"message": "Password reset successfully"}

# ========== USER PROFILE ==========
@api_router.put("/users/me")
async def update_profile(data: UserUpdate, user: dict = Depends(get_current_user)):
    update_doc = {}
    if data.first_name:
        update_doc["first_name"] = data.first_name
    if data.last_name:
        update_doc["last_name"] = data.last_name
    if data.fca_number is not None:
        update_doc["fca_number"] = data.fca_number
    
    if data.new_password:
        if not data.current_password:
            raise HTTPException(status_code=400, detail="Current password required")
        db_user = await db.users.find_one({"_id": ObjectId(user["id"])})
        if not verify_password(data.current_password, db_user["password_hash"]):
            raise HTTPException(status_code=400, detail="Current password incorrect")
        update_doc["password_hash"] = hash_password(data.new_password)
    
    if update_doc:
        await db.users.update_one({"_id": ObjectId(user["id"])}, {"$set": update_doc})
    
    updated = await db.users.find_one({"_id": ObjectId(user["id"])}, {"_id": 0, "password_hash": 0})
    updated["id"] = user["id"]
    return updated

@api_router.put("/users/me/onboarding")
async def complete_onboarding(user: dict = Depends(get_current_user)):
    await db.users.update_one({"_id": ObjectId(user["id"])}, {"$set": {"onboarding_completed": True}})
    return {"message": "Onboarding completed"}

# ========== CLIENTS ==========
@api_router.get("/clients")
async def list_clients(
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    user: dict = Depends(get_current_user)
):
    query = {"user_id": user["id"]}
    if search:
        query["$or"] = [
            {"first_name": {"$regex": search, "$options": "i"}},
            {"last_name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}}
        ]
    
    total = await db.clients.count_documents(query)
    clients = await db.clients.find(query, {"_id": 0}).skip((page-1)*limit).limit(limit).to_list(limit)
    return {"clients": clients, "total": total, "page": page, "limit": limit}

@api_router.post("/clients")
async def create_client(data: ClientCreate, user: dict = Depends(get_current_user)):
    client_doc = data.model_dump()
    client_doc["id"] = str(uuid.uuid4())
    client_doc["user_id"] = user["id"]
    client_doc["created_at"] = datetime.now(timezone.utc).isoformat()
    client_doc["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.clients.insert_one(client_doc)
    client_doc.pop("_id", None)
    return client_doc

@api_router.get("/clients/{client_id}")
async def get_client(client_id: str, user: dict = Depends(get_current_user)):
    client = await db.clients.find_one({"id": client_id, "user_id": user["id"]}, {"_id": 0})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client

@api_router.put("/clients/{client_id}")
async def update_client(client_id: str, data: ClientCreate, user: dict = Depends(get_current_user)):
    update_doc = data.model_dump()
    update_doc["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await db.clients.update_one(
        {"id": client_id, "user_id": user["id"]},
        {"$set": update_doc}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Client not found")
    return await db.clients.find_one({"id": client_id}, {"_id": 0})

@api_router.delete("/clients/{client_id}")
async def delete_client(client_id: str, user: dict = Depends(get_current_user)):
    result = await db.clients.delete_one({"id": client_id, "user_id": user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Client not found")
    return {"message": "Client deleted"}

# ========== CASES ==========
@api_router.get("/cases")
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

@api_router.post("/cases")
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

@api_router.get("/cases/{case_id}")
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

@api_router.put("/cases/{case_id}")
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

@api_router.patch("/cases/{case_id}/stage")
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

@api_router.delete("/cases/{case_id}")
async def delete_case(case_id: str, user: dict = Depends(get_current_user)):
    result = await db.cases.delete_one({"id": case_id, "assigned_broker_id": user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Case not found")
    return {"message": "Case deleted"}

# ========== LENDERS ==========
@api_router.get("/lenders")
async def list_lenders(
    search: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    user: dict = Depends(get_current_user)
):
    query = {"user_id": user["id"]}
    if search:
        query["name"] = {"$regex": search, "$options": "i"}
    
    total = await db.lenders.count_documents(query)
    lenders = await db.lenders.find(query, {"_id": 0}).skip((page-1)*limit).limit(limit).to_list(limit)
    return {"lenders": lenders, "total": total, "page": page, "limit": limit}

@api_router.post("/lenders")
async def create_lender(data: LenderCreate, user: dict = Depends(get_current_user)):
    lender_doc = data.model_dump()
    lender_doc["id"] = str(uuid.uuid4())
    lender_doc["user_id"] = user["id"]
    lender_doc["created_at"] = datetime.now(timezone.utc).isoformat()
    lender_doc["updated_at"] = datetime.now(timezone.utc).isoformat()
    await db.lenders.insert_one(lender_doc)
    lender_doc.pop("_id", None)
    return lender_doc

@api_router.get("/lenders/{lender_id}")
async def get_lender(lender_id: str, user: dict = Depends(get_current_user)):
    lender = await db.lenders.find_one({"id": lender_id, "user_id": user["id"]}, {"_id": 0})
    if not lender:
        raise HTTPException(status_code=404, detail="Lender not found")
    return lender

@api_router.put("/lenders/{lender_id}")
async def update_lender(lender_id: str, data: LenderCreate, user: dict = Depends(get_current_user)):
    update_doc = data.model_dump()
    update_doc["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await db.lenders.update_one(
        {"id": lender_id, "user_id": user["id"]},
        {"$set": update_doc}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Lender not found")
    return await db.lenders.find_one({"id": lender_id}, {"_id": 0})

@api_router.delete("/lenders/{lender_id}")
async def delete_lender(lender_id: str, user: dict = Depends(get_current_user)):
    result = await db.lenders.delete_one({"id": lender_id, "user_id": user["id"]})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Lender not found")
    return {"message": "Lender deleted"}

# ========== COMMISSIONS ==========
@api_router.get("/commissions")
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

@api_router.post("/commissions")
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

@api_router.put("/commissions/{commission_id}")
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

@api_router.delete("/commissions/{commission_id}")
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
    from reportlab.pdfbase.pdfmetrics import stringWidth
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

@api_router.get("/commissions/{commission_id}/invoice")
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

# ========== NOTES ==========
@api_router.get("/notes")
async def list_notes(case_id: str = Query(...), user: dict = Depends(get_current_user)):
    """Get all notes for a case, sorted by created_at descending"""
    case = await db.cases.find_one({"id": case_id, "assigned_broker_id": user["id"]})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    notes = await db.notes.find({"case_id": case_id}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return {"notes": notes, "total": len(notes)}

@api_router.get("/cases/{case_id}/notes")
async def list_case_notes(case_id: str, user: dict = Depends(get_current_user)):
    """Get all notes for a case, sorted by created_at descending"""
    case = await db.cases.find_one({"id": case_id, "assigned_broker_id": user["id"]})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    notes = await db.notes.find({"case_id": case_id}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return {"notes": notes, "total": len(notes)}

@api_router.post("/notes")
async def create_note(data: NoteCreate, user: dict = Depends(get_current_user)):
    """Create a new note (immutable - no edit or delete)"""
    case = await db.cases.find_one({"id": data.case_id, "assigned_broker_id": user["id"]})
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Validate content length
    if len(data.content) > 2000:
        raise HTTPException(status_code=400, detail="Note content exceeds 2000 characters")
    
    # Get author name from user profile
    author_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
    if not author_name:
        author_name = user.get('email', 'Unknown')
    
    note_doc = {
        "id": str(uuid.uuid4()),
        "case_id": data.case_id,
        "user_id": user["id"],
        "author_name": author_name,
        "content": data.content,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    await db.notes.insert_one(note_doc)
    note_doc.pop("_id", None)
    return note_doc

# ========== DOCUMENTS ==========
@api_router.post("/documents/upload")
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
        return doc
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail="Upload failed")

@api_router.get("/documents")
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
    return {"documents": docs}

@api_router.get("/documents/{doc_id}/download")
async def download_document(doc_id: str, user: dict = Depends(get_current_user)):
    doc = await db.documents.find_one({"id": doc_id, "user_id": user["id"], "is_deleted": False})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    try:
        data, content_type = get_object(doc["file_path"])
        from fastapi.responses import Response
        return Response(content=data, media_type=doc.get("content_type", content_type),
                       headers={"Content-Disposition": f"attachment; filename={doc['filename']}"})
    except Exception as e:
        logger.error(f"Download failed: {e}")
        raise HTTPException(status_code=500, detail="Download failed")

@api_router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str, user: dict = Depends(get_current_user)):
    result = await db.documents.update_one(
        {"id": doc_id, "user_id": user["id"]},
        {"$set": {"is_deleted": True}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"message": "Document deleted"}

# ========== DASHBOARD STATS ==========
@api_router.get("/dashboard/stats")
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

# ========== HEALTH CHECK ==========
@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

# ========== STARTUP ==========
@app.on_event("startup")
async def startup():
    # Create indexes
    await db.users.create_index("email", unique=True)
    await db.login_attempts.create_index("identifier")
    await db.clients.create_index("user_id")
    await db.cases.create_index("assigned_broker_id")
    await db.cases.create_index("stage")
    await db.lenders.create_index("user_id")
    await db.commission_records.create_index("user_id")
    await db.documents.create_index("user_id")
    await db.notes.create_index([("case_id", 1), ("created_at", -1)])
    await db.invoice_sequences.create_index("user_id", unique=True)
    
    # Seed admin
    admin_email = os.environ.get("ADMIN_EMAIL", "admin@brokeros.com")
    admin_password = os.environ.get("ADMIN_PASSWORD", "Admin123!")
    existing = await db.users.find_one({"email": admin_email})
    if existing is None:
        hashed = hash_password(admin_password)
        await db.users.insert_one({
            "email": admin_email,
            "password_hash": hashed,
            "first_name": "Admin",
            "last_name": "User",
            "fca_number": "123456",
            "role": "admin",
            "team_id": None,
            "onboarding_completed": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_login": None
        })
        logger.info(f"Admin user created: {admin_email}")
    elif not verify_password(admin_password, existing["password_hash"]):
        await db.users.update_one({"email": admin_email}, {"$set": {"password_hash": hash_password(admin_password)}})
        logger.info("Admin password updated")
    
    # Write test credentials
    os_module = __import__('os')
    os_module.makedirs("/app/memory", exist_ok=True)
    with open("/app/memory/test_credentials.md", "w") as f:
        f.write("# Test Credentials\n\n")
        f.write("## Admin Account\n")
        f.write(f"- Email: {admin_email}\n")
        f.write(f"- Password: {admin_password}\n")
        f.write("- Role: admin\n\n")
        f.write("## Auth Endpoints\n")
        f.write("- POST /api/auth/register\n")
        f.write("- POST /api/auth/login\n")
        f.write("- POST /api/auth/logout\n")
        f.write("- GET /api/auth/me\n")
        f.write("- POST /api/auth/refresh\n")
    
    # Init storage
    try:
        init_storage()
        logger.info("Storage initialized")
    except Exception as e:
        logger.warning(f"Storage init skipped: {e}")
    
    logger.info("BrokerOS API started")

@app.on_event("shutdown")
async def shutdown():
    client.close()

# Include router
app.include_router(api_router)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=[os.environ.get("FRONTEND_URL", "http://localhost:3000"), "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)
