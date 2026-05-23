from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, APIRouter
from starlette.middleware.cors import CORSMiddleware
import os
import logging
from datetime import datetime, timezone

from routes import (
    auth_router,
    users_router,
    clients_router,
    cases_router,
    lenders_router,
    commissions_router,
    notes_router,
    cases_notes_router,
    documents_router,
    dashboard_router,
    ai_router,
)
from routes.deps import db, hash_password, verify_password, init_storage, logger

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

app = FastAPI(title="BrokerOS API")
api_router = APIRouter(prefix="/api")

# Include all routers
api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(clients_router)
api_router.include_router(cases_router)
api_router.include_router(lenders_router)
api_router.include_router(commissions_router)
api_router.include_router(notes_router)
api_router.include_router(cases_notes_router)
api_router.include_router(documents_router)
api_router.include_router(dashboard_router)


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
    os.makedirs("/app/memory", exist_ok=True)
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
    from routes.deps import client
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
