from __future__ import annotations

import uuid
from datetime import UTC, datetime

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import get_db
from ..core.security import create_access_token, encrypt_token
from ..dependencies import get_current_user
from ..models.user import User
from ..services.github import GitHubOAuthService, create_github_service

router = APIRouter(prefix="/auth", tags=["auth"])
logger = structlog.get_logger(__name__)


class LoginResponse(BaseModel):
    authorization_url: str
    state: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserResponse(BaseModel):
    id: str
    login: str
    name: str | None
    avatar_url: str | None


@router.get("/github/login", response_model=LoginResponse)
async def github_login(
    github: GitHubOAuthService = Depends(create_github_service),
) -> LoginResponse:
    state = uuid.uuid4().hex
    url = github.get_authorization_url(state)
    return LoginResponse(authorization_url=url, state=state)


@router.get("/github/callback", response_model=TokenResponse)
async def github_callback(
    code: str = Query(...),
    state: str = Query(""),
    session: AsyncSession = Depends(get_db),
    github: GitHubOAuthService = Depends(create_github_service),
) -> TokenResponse:
    token_data = await github.exchange_code(code)
    if not token_data:
        raise HTTPException(status_code=400, detail="Failed to exchange code")

    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="No access token received")

    user_info = await github.get_user_info(access_token)
    if not user_info:
        raise HTTPException(status_code=400, detail="Failed to get user info")

    github_id = str(user_info["id"])
    login = user_info["login"]

    stmt = select(User).where(User.provider_id == github_id, User.deleted_at.is_(None))
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if user:
        user.access_token = encrypt_token(access_token)
        user.login = login
        user.name = user_info.get("name")
        user.avatar_url = user_info.get("avatar_url")
        user.email = user_info.get("email")
        user.last_login_at = datetime.now(UTC)
    else:
        user = User(
            provider_id=github_id,
            login=login,
            name=user_info.get("name"),
            email=user_info.get("email"),
            avatar_url=user_info.get("avatar_url"),
            access_token=encrypt_token(access_token),
        )
        session.add(user)
        await session.flush()

    jwt_token = create_access_token(str(user.id))
    return TokenResponse(
        access_token=jwt_token,
        user={
            "id": str(user.id),
            "login": user.login,
            "name": user.name,
            "avatar_url": user.avatar_url,
        },
    )


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        login=user.login,
        name=user.name,
        avatar_url=user.avatar_url,
    )


class DevLoginRequest(BaseModel):
    login: str = "developer"
    name: str = "Developer"


@router.post("/dev/login", response_model=TokenResponse)
async def dev_login(
    body: DevLoginRequest = DevLoginRequest(),
    session: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Convenience endpoint for local/self-hosted environments without GitHub OAuth."""
    stmt = select(User).where(User.login == body.login, User.deleted_at.is_(None))
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        user = User(
            provider_id=f"local-{body.login}",
            login=body.login,
            name=body.name,
            email=f"{body.login}@local.dev",
            avatar_url="",
        )
        session.add(user)
        await session.flush()
        await session.commit()
    else:
        user.last_login_at = datetime.now(UTC)
        await session.flush()
        await session.commit()

    jwt_token = create_access_token(str(user.id))
    return TokenResponse(
        access_token=jwt_token,
        user={
            "id": str(user.id),
            "login": user.login,
            "name": user.name,
            "avatar_url": user.avatar_url,
        },
    )
