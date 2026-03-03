"""
Authentication endpoints: register, login, logout, /me.
Tokens stored as httpOnly cookies. No auto-refresh endpoint needed —
frontend simply redirects to /login when session expires.
"""
from fastapi import APIRouter, Depends, HTTPException, Response, Request, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    get_current_user_id,
)
from app.models.models import User
from app.schemas.schemas import (
    UserRegister, UserLogin, UserResponse, TokenResponse, MessageResponse,
)
from app.core.config import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()

ACCESS_COOKIE  = "access_token"
REFRESH_COOKIE = "refresh_token"

_COOKIE = dict(httponly=True, samesite="lax", secure=False)


def _set_cookies(response: Response, user_id: int) -> None:
    response.set_cookie(
        ACCESS_COOKIE,
        create_access_token({"sub": str(user_id)}),
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        **_COOKIE,
    )
    response.set_cookie(
        REFRESH_COOKIE,
        create_refresh_token({"sub": str(user_id)}),
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        **_COOKIE,
    )


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(body: UserRegister, response: Response, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(400, "Email already registered")
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(400, "Username already taken")
    user = User(
        email=body.email,
        username=body.username,
        hashed_password=hash_password(body.password),
    )
    db.add(user); db.commit(); db.refresh(user)
    _set_cookies(response, user.id)
    return {"message": "Registration successful", "user": user}


@router.post("/login", response_model=TokenResponse)
def login(body: UserLogin, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(401, "Invalid email or password")
    _set_cookies(response, user.id)
    return {"message": "Login successful", "user": user}


@router.post("/logout", response_model=MessageResponse)
def logout(response: Response):
    response.delete_cookie(ACCESS_COOKIE)
    response.delete_cookie(REFRESH_COOKIE)
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
def get_me(request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user_id(request)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    return user
