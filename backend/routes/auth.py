from fastapi import APIRouter, HTTPException, Request, Response, Depends
from bson import ObjectId
import secrets
from datetime import datetime, timezone, timedelta

from .deps import (
    db, logger,
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    get_current_user, JWT_SECRET, JWT_ALGORITHM
)
from .models import UserRegister, UserLogin, UserUpdate, ForgotPassword, ResetPassword
import jwt

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
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


@router.post("/login")
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


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/")
    response.delete_cookie("refresh_token", path="/")
    return {"message": "Logged out successfully"}


@router.get("/me")
async def get_me(user: dict = Depends(get_current_user)):
    return user


@router.post("/refresh")
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


@router.post("/forgot-password")
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


@router.post("/reset-password")
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


# User profile endpoints
users_router = APIRouter(prefix="/users", tags=["users"])


@users_router.put("/me")
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


@users_router.put("/me/onboarding")
async def complete_onboarding(user: dict = Depends(get_current_user)):
    await db.users.update_one({"_id": ObjectId(user["id"])}, {"$set": {"onboarding_completed": True}})
    return {"message": "Onboarding completed"}
