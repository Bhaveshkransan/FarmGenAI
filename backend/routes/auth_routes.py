from backend.repositories.user_repo import UserRepository
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from backend.services.auth_service import signup_user, login_user
from backend.schemas.auth_model import SignupRequest, LoginRequest, AuthResponse, VerificationRequest, PreferenceRequest
from backend.core.security import get_current_user
from backend.api.v1.dependencies import get_db

router = APIRouter(tags=["Auth"])

import inspect

@router.post("/signup", response_model=AuthResponse)
@router.post("/register", response_model=AuthResponse)
async def signup(data: SignupRequest, db: AsyncSession = Depends(get_db)):
    res = signup_user(data.dict())
    result = await res if inspect.isawaitable(res) else res
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    
    # We use the new UserRepository with the injected session
    repo = UserRepository(db)
    user = await repo.get_by_email(data.email)
    
    # Store the role in the database for persistence
    if user:
        user.role = data.role
        await db.commit()
        result["role"] = data.role
        
    return result

@router.post("/login", response_model=AuthResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    res = login_user(data.dict())
    result = await res if inspect.isawaitable(res) else res
    if "error" in result:
        raise HTTPException(status_code=401, detail=result["error"])
    
    # Enrich with details from database
    repo = UserRepository(db)
    user = await repo.get_by_email(data.email)
    if user:
        result["role"] = user.role
        result["verification_status"] = getattr(user, "verification_status", "PENDING")
        result["preferences"] = getattr(user, "preferences", {})

    return result

@router.get("/me", response_model=AuthResponse)
async def get_me(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    user_email = current_user.get("email") # Assuming token has email
    if not user_email:
        raise HTTPException(status_code=401, detail="Invalid token payload")
        
    repo = UserRepository(db)
    user = await repo.get_by_email(user_email)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    
    return {
        "user_id": current_user["sub"],
        "name": user.full_name,
        "email": user.email,
        "location": getattr(user, "location", ""),
        "language": getattr(user, "language", "English"),
        "role": user.role,
        "verification_status": getattr(user, "verification_status", "PENDING"),
        "preferences": getattr(user, "preferences", {}),
        "trust_score": getattr(user, "trust_score", 4.0),
        "token": "",
        "message": "User verified"
    }

@router.post("/verify")
async def verify_user(
    request: VerificationRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Skeleton implementation for Phase B
    return {"status": "success", "message": "Verification documents uploaded. Status: PENDING"}

@router.post("/preferences")
async def update_preferences(
    request: PreferenceRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return {"status": "success", "preferences": request.preferences}

@router.post("/location")
async def update_location(
    location: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return {"status": "success", "location": location}

