from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from datetime import datetime, timedelta
from jose import jwt, JWTError
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from app.core.config import GOOGLE_CLIENT_ID, JWT_SECRET, JWT_ALGORITHM, JWT_EXPIRE_DAYS
from app.services import user_service

router = APIRouter(prefix="/api/auth")
bearer = HTTPBearer(auto_error=False)


class GoogleTokenRequest(BaseModel):
    token: str


class BookmarkRequest(BaseModel):
    bookmarks: list[str]


def create_jwt(email: str) -> str:
    expire = datetime.utcnow() + timedelta(days=JWT_EXPIRE_DAYS)
    return jwt.encode({"sub": email, "exp": expire}, JWT_SECRET, algorithm=JWT_ALGORITHM)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    if not credentials:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다")
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=401, detail="유효하지 않은 토큰")
        user = user_service.get_user(email)
        if not user:
            raise HTTPException(status_code=401, detail="사용자를 찾을 수 없습니다")
        return user
    except JWTError:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰")


@router.post("/google")
def google_login(body: GoogleTokenRequest):
    try:
        info = id_token.verify_oauth2_token(
            body.token,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
        )
    except Exception:
        raise HTTPException(status_code=401, detail="구글 토큰 검증 실패")

    email = info["email"]
    name = info.get("name", "")
    picture = info.get("picture", "")

    user = user_service.upsert_user(email, name, picture)
    token = create_jwt(email)
    return {"token": token, "user": user}


@router.get("/me")
def me(user=Depends(get_current_user)):
    return user


@router.get("/bookmarks")
def get_bookmarks(user=Depends(get_current_user)):
    return user_service.get_bookmarks(user["email"])


@router.post("/bookmarks")
def save_bookmarks(body: BookmarkRequest, user=Depends(get_current_user)):
    return user_service.set_bookmarks(user["email"], body.bookmarks)
