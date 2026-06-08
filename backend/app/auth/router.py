from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import security, service
from app.auth.deps import get_current_user
from app.auth.models import User
from app.auth.schemas import LoginIn, RegisterIn, TokenOut, UserOut
from app.db import get_session

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterIn, session: AsyncSession = Depends(get_session)):
    try:
        user = await service.register_user(session, body.email, body.password)
    except service.EmailTaken:
        raise HTTPException(status.HTTP_409_CONFLICT, "email already registered")
    return UserOut(id=user.id, email=user.email, tier=user.tier)


@router.post("/login", response_model=TokenOut)
async def login(body: LoginIn, session: AsyncSession = Depends(get_session)):
    try:
        user = await service.authenticate_user(session, body.email, body.password)
    except service.BadCredentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "bad credentials")
    return TokenOut(access_token=security.create_access_token(user.id))


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return UserOut(id=user.id, email=user.email, tier=user.tier)
