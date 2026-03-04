"""Authentication endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
import pyotp
from typing import Optional
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_current_user_id,
    hash_password,
    verify_password,
)
from app.models.models import User
from app.schemas.schemas import (
    ChangePasswordRequest,
    MessageResponse,
    TokenResponse,
    TwoFactorDisableRequest,
    TwoFactorEnableRequest,
    TwoFactorSetupRequest,
    TwoFactorSetupResponse,
    UpdateEmailRequest,
    UserLogin,
    UserRegister,
    UserResponse,
)

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()

ACCESS_COOKIE = "access_token"
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


def _normalize_otp(code: Optional[str]) -> str:
    return (code or "").replace(" ", "").strip()


def _require_valid_otp(user: User, otp_code: Optional[str]) -> None:
    if not user.twofa_enabled:
        return

    code = _normalize_otp(otp_code)
    if not code:
        raise HTTPException(401, "Введите код двухфакторной авторизации")

    secret = user.twofa_secret
    if not secret:
        raise HTTPException(401, "2FA не настроена корректно. Отключите и настройте заново")

    totp = pyotp.TOTP(secret)
    if not totp.verify(code, valid_window=1):
        raise HTTPException(401, "Неверный код двухфакторной авторизации")


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(body: UserRegister, response: Response, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(400, "Эта почта уже зарегистрирована")
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(400, "Имя пользователя уже занято")

    user = User(
        email=body.email,
        username=body.username,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    _set_cookies(response, user.id)
    return {"message": "Регистрация выполнена", "user": user}


@router.post("/login", response_model=TokenResponse)
def login(body: UserLogin, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(401, "Неверная почта или пароль")

    _require_valid_otp(user, body.otp_code)

    _set_cookies(response, user.id)
    return {"message": "Вход выполнен", "user": user}


@router.post("/logout", response_model=MessageResponse)
def logout(response: Response):
    response.delete_cookie(ACCESS_COOKIE)
    response.delete_cookie(REFRESH_COOKIE)
    return {"message": "Вы вышли из аккаунта"}


@router.get("/me", response_model=UserResponse)
def get_me(request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user_id(request)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "Пользователь не найден")
    return user


@router.post("/change-email", response_model=TokenResponse)
def change_email(body: UpdateEmailRequest, request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user_id(request)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "Пользователь не найден")

    if not verify_password(body.current_password, user.hashed_password):
        raise HTTPException(400, "Неверный текущий пароль")

    if user.email == body.new_email:
        raise HTTPException(400, "Новая почта совпадает с текущей")

    if db.query(User).filter(User.email == body.new_email, User.id != user.id).first():
        raise HTTPException(400, "Эта почта уже используется")

    user.email = body.new_email
    db.commit()
    db.refresh(user)
    return {"message": "Почта обновлена", "user": user}


@router.post("/change-password", response_model=MessageResponse)
def change_password(body: ChangePasswordRequest, request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user_id(request)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "Пользователь не найден")

    if not verify_password(body.current_password, user.hashed_password):
        raise HTTPException(400, "Неверный текущий пароль")

    if verify_password(body.new_password, user.hashed_password):
        raise HTTPException(400, "Новый пароль должен отличаться от текущего")

    user.hashed_password = hash_password(body.new_password)
    db.commit()
    return {"message": "Пароль успешно изменен"}


@router.post("/2fa/setup", response_model=TwoFactorSetupResponse)
def setup_two_factor(body: TwoFactorSetupRequest, request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user_id(request)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "Пользователь не найден")

    if not verify_password(body.current_password, user.hashed_password):
        raise HTTPException(400, "Неверный текущий пароль")

    secret = pyotp.random_base32()
    user.twofa_pending_secret = secret
    db.commit()

    issuer = "FmtSwap"
    otpauth_url = pyotp.TOTP(secret).provisioning_uri(name=user.email, issuer_name=issuer)
    return {"secret": secret, "otpauth_url": otpauth_url}


@router.post("/2fa/enable", response_model=TokenResponse)
def enable_two_factor(body: TwoFactorEnableRequest, request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user_id(request)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "Пользователь не найден")

    pending_secret = user.twofa_pending_secret
    if not pending_secret:
        raise HTTPException(400, "Сначала выполните настройку 2FA")

    code = _normalize_otp(body.otp_code)
    if not code:
        raise HTTPException(400, "Введите код подтверждения")

    if not pyotp.TOTP(pending_secret).verify(code, valid_window=1):
        raise HTTPException(400, "Неверный код подтверждения")

    user.twofa_secret = pending_secret
    user.twofa_pending_secret = None
    user.twofa_enabled = True
    db.commit()
    db.refresh(user)
    return {"message": "Двухфакторная авторизация включена", "user": user}


@router.post("/2fa/disable", response_model=TokenResponse)
def disable_two_factor(body: TwoFactorDisableRequest, request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user_id(request)
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "Пользователь не найден")

    if not user.twofa_enabled or not user.twofa_secret:
        raise HTTPException(400, "Двухфакторная авторизация уже отключена")

    if not verify_password(body.current_password, user.hashed_password):
        raise HTTPException(400, "Неверный текущий пароль")

    code = _normalize_otp(body.otp_code)
    if not code:
        raise HTTPException(400, "Введите код двухфакторной авторизации")

    if not pyotp.TOTP(user.twofa_secret).verify(code, valid_window=1):
        raise HTTPException(400, "Неверный код двухфакторной авторизации")

    user.twofa_enabled = False
    user.twofa_secret = None
    user.twofa_pending_secret = None
    db.commit()
    db.refresh(user)
    return {"message": "Двухфакторная авторизация отключена", "user": user}
