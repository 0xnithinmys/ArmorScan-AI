from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr

from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token

router = APIRouter()


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(payload: UserRegisterRequest, db: AsyncSession = Depends(get_db)):
    # TODO: check if user exists, create user record
    hashed = get_password_hash(payload.password)
    return {"message": "User registered", "email": payload.email}


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    # TODO: look up user in DB, verify password
    # Placeholder — will be replaced in Phase 3
    token = create_access_token({"sub": form_data.username})
    return TokenResponse(access_token=token)
