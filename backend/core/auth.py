from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from core.config import settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)


@dataclass(frozen=True)
class UserRecord:
    username: str
    password_hash: str
    role: str
    source: str


@dataclass(frozen=True)
class TokenClaims:
    sub: str
    role: str
    exp: int
    source: str


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * ((4 - len(value) % 4) % 4)
    return base64.urlsafe_b64decode(value + padding)


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 200_000)
    return f"pbkdf2_sha256${salt}${derived.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        scheme, salt, digest = password_hash.split("$", 2)
    except ValueError:
        return False
    if scheme != "pbkdf2_sha256":
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 200_000)
    return hmac.compare_digest(candidate.hex(), digest)


def _user_store_path() -> Path:
    return Path(settings.user_store_file)


def _bootstrap_demo_user() -> UserRecord:
    return UserRecord(
        username=settings.demo_username,
        password_hash=hash_password(settings.demo_password),
        role=settings.demo_role,
        source="bootstrap",
    )


def _load_persisted_users() -> dict[str, UserRecord]:
    path = _user_store_path()
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    users: dict[str, UserRecord] = {}
    for item in payload.get("users", []):
        username = str(item.get("username", "")).strip()
        password_hash = str(item.get("password_hash", "")).strip()
        role = str(item.get("role", "operator")).strip() or "operator"
        if not username or not password_hash:
            continue
        users[username] = UserRecord(username=username, password_hash=password_hash, role=role, source="file")
    return users


def _save_users(users: dict[str, UserRecord]) -> None:
    path = _user_store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "users": [
            {
                "username": user.username,
                "password_hash": user.password_hash,
                "role": user.role,
            }
            for user in sorted(users.values(), key=lambda user: user.username)
            if user.source == "file"
        ]
    }
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)


def get_user_registry() -> dict[str, UserRecord]:
    users = _load_persisted_users()
    if settings.demo_username not in users:
        users[settings.demo_username] = _bootstrap_demo_user()
    return users


def register_user(username: str, password: str, role: str = "operator") -> UserRecord:
    normalized = username.strip().lower()
    if len(normalized) < 3:
        raise ValueError("Username must be at least 3 characters long.")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long.")

    users = get_user_registry()
    if normalized in users:
        raise ValueError("User already exists.")

    user = UserRecord(username=normalized, password_hash=hash_password(password), role=role, source="file")
    users[normalized] = user
    _save_users(users)
    return user


def authenticate_user(username: str, password: str) -> UserRecord | None:
    normalized = username.strip().lower()
    user = get_user_registry().get(normalized)
    if user is None:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def create_access_token(user: UserRecord) -> str:
    header = {"alg": settings.jwt_algorithm, "typ": "JWT"}
    exp_dt = _utc_now() + timedelta(minutes=settings.token_expiration_minutes)
    payload = {
        "sub": user.username,
        "role": user.role,
        "source": user.source,
        "exp": int(exp_dt.timestamp()),
    }
    header_segment = _b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_segment = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(
        settings.jwt_secret.encode("utf-8"),
        f"{header_segment}.{payload_segment}".encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return f"{header_segment}.{payload_segment}.{_b64url_encode(signature)}"


def decode_access_token(token: str) -> TokenClaims:
    try:
        header_segment, payload_segment, signature_segment = token.split(".", 2)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed bearer token.") from exc

    expected = hmac.new(
        settings.jwt_secret.encode("utf-8"),
        f"{header_segment}.{payload_segment}".encode("utf-8"),
        hashlib.sha256,
    ).digest()
    if not hmac.compare_digest(expected, _b64url_decode(signature_segment)):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid bearer token signature.")

    payload = json.loads(_b64url_decode(payload_segment))
    exp = int(payload.get("exp", 0))
    if exp <= int(_utc_now().timestamp()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bearer token expired.")

    sub = str(payload.get("sub", "")).strip()
    role = str(payload.get("role", "viewer")).strip() or "viewer"
    source = str(payload.get("source", "jwt")).strip() or "jwt"
    if not sub:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token subject is missing.")

    return TokenClaims(sub=sub, role=role, exp=exp, source=source)


async def require_authenticated_user(token: str | None = Depends(oauth2_scheme)) -> TokenClaims:
    if not settings.auth_required and not token:
        return TokenClaims(
            sub="anonymous",
            role="viewer",
            exp=int((_utc_now() + timedelta(minutes=settings.token_expiration_minutes)).timestamp()),
            source="public-dev-bypass",
        )

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return decode_access_token(token)


async def get_optional_claims(token: str | None = Depends(oauth2_scheme)) -> TokenClaims | None:
    if not token:
        return None
    return decode_access_token(token)


def token_response(user: UserRecord) -> dict[str, object]:
    token = create_access_token(user)
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": settings.token_expiration_minutes * 60,
        "username": user.username,
        "role": user.role,
    }
