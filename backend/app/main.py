"""
FastAPI application entry point.
"""
import hmac
import logging
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.database import create_tables
from app.routers import auth, convert, file_hosting
from app.services.file_hosting import get_hosting_dir, start_hosting_cleanup_scheduler, stop_hosting_cleanup_scheduler

logging.basicConfig(level=logging.INFO)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    get_hosting_dir()
    start_hosting_cleanup_scheduler()
    logging.getLogger("app.main").info("Database tables initialised")
    yield
    stop_hosting_cleanup_scheduler()


app = FastAPI(title="FmtSwap API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CSRF_SAFE = {"GET", "HEAD", "OPTIONS"}
CSRF_HEADER = "x-csrf-token"
CSRF_COOKIE = "csrf_token"
CSRF_EXEMPT = {
    "/auth/login",
    "/auth/register",
    "/auth/logout",
    "/csrf-token",
    "/health",
    "/docs",
    "/openapi.json",
}


@app.middleware("http")
async def csrf_middleware(request: Request, call_next):
    if request.method not in CSRF_SAFE and request.url.path not in CSRF_EXEMPT:
        cookie_token = request.cookies.get(CSRF_COOKIE, "")
        header_token = request.headers.get(CSRF_HEADER, "")
        if not cookie_token or not header_token or not hmac.compare_digest(cookie_token, header_token):
            return JSONResponse({"detail": "CSRF-токен отсутствует или неверен"}, status_code=403)
    return await call_next(request)


@app.get("/csrf-token")
def get_csrf_token(request: Request):
    existing = request.cookies.get(CSRF_COOKIE)
    token = existing or secrets.token_hex(32)
    response = JSONResponse({"csrf_token": token})
    if not existing:
        response.set_cookie(CSRF_COOKIE, token, httponly=False, samesite="lax", secure=False)
    return response


app.include_router(auth.router)
app.include_router(convert.router)
app.include_router(file_hosting.router)


@app.get("/health")
def health():
    return {"status": "ok"}
