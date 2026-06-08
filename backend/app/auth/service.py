from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import security
from app.auth.models import User


class EmailTaken(Exception):
    pass


class BadCredentials(Exception):
    pass


async def register_user(session: AsyncSession, email: str, password: str) -> User:
    existing = await session.scalar(select(User).where(User.email == email))
    if existing is not None:
        raise EmailTaken(email)
    user = User(email=email, password_hash=security.hash_password(password))
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def authenticate_user(session: AsyncSession, email: str, password: str) -> User:
    user = await session.scalar(select(User).where(User.email == email))
    if user is None or not security.verify_password(password, user.password_hash):
        raise BadCredentials()
    return user
