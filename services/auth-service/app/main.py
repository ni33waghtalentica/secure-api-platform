from fastapi import FastAPI, Depends 
from pydantic import BaseModel
from typing import Optional
from fastapi import Body, HTTPException, Request, status

def require_user(request: Request) -> str:
    token = get_bearer_token(request)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    payload = decode_token(token)
    return payload.get("sub", "")

class CreateUserRequest(BaseModel):
    username: str
    password: str

app = FastAPI(title="Auth Service")

class CreateUserResponse(BaseModel):
    id: int
    username: str


# GET /users (protected, list users)
@app.get("/users")
def list_users(username: str = Depends(require_user)) -> dict:
    conn = get_db()
    try:
        rows = conn.execute("SELECT id, username FROM users").fetchall()
        return {
            "requested_by": username,
            "users": [{"id": row["id"], "username": row["username"]} for row in rows],
        }
    finally:
        conn.close()

# POST /users (admin only, create user)
@app.post("/users", response_model=CreateUserResponse, status_code=201)
def create_user(
    body: CreateUserRequest = Body(...),
    current_user: Optional[str] = Depends(require_user),
) -> CreateUserResponse:
    """
    Create a new user. Requires JWT (admin) authentication. Only admin can create users.
    """
    if current_user != "admin":
        raise HTTPException(status_code=403, detail="Only admin can create users")
    if not body.username or not body.password:
        raise HTTPException(status_code=400, detail="Username and password required")
    conn = get_db()
    try:
        # Check if user exists
        existing = conn.execute(
            "SELECT id FROM users WHERE username = ?", (body.username,)
        ).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="Username already exists")
        password_hash = pwd_context.hash(body.password)
        cur = conn.execute(
            "INSERT INTO users (username, password_hash) VALUES (?, ?)",
            (body.username, password_hash),
        )
        conn.commit()
        user_id = cur.lastrowid
        return CreateUserResponse(id=user_id, username=body.username)
    finally:
        conn.close()
from datetime import datetime, timedelta, timezone
import os
import sqlite3
from typing import Optional

import jwt
from fastapi import Depends, FastAPI, HTTPException, Request, status
from passlib.context import CryptContext
from pydantic import BaseModel

DB_PATH = os.getenv("DB_PATH", "/data/app.db")
JWT_KEY = os.getenv("JWT_KEY", "local-dev-key")
JWT_SECRET = os.getenv("JWT_SECRET", "local-dev-secret")
JWT_ALG = os.getenv("JWT_ALG", "HS256")
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))
SEED_USER = os.getenv("SEED_USER", "admin")
SEED_USER_PASSWORD = os.getenv("SEED_USER_PASSWORD", "admin123").strip()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = get_db()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
            """
        )
        conn.commit()

        existing = conn.execute(
            "SELECT id FROM users WHERE username = ?", (SEED_USER,)
        ).fetchone()
        if existing is None:
            password_hash = pwd_context.hash(SEED_USER_PASSWORD)
            conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (SEED_USER, password_hash),
            )
            conn.commit()
    finally:
        conn.close()


@app.on_event("startup")
def on_startup() -> None:
    init_db()


def verify_password(plain_password: str, password_hash: str) -> bool:
    return pwd_context.verify(plain_password, password_hash)


def create_access_token(subject: str) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {
        "sub": subject,
        "iss": JWT_KEY,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)
    return token


def decode_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALG],
            options={"require": ["exp", "iss"]},
        )
        if payload.get("iss") != JWT_KEY:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid issuer")
        return payload
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc


def get_bearer_token(request: Request) -> Optional[str]:
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None
    parts = auth_header.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    return parts[1]


def require_user(request: Request) -> str:
    token = get_bearer_token(request)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")
    payload = decode_token(token)
    return payload.get("sub", "")


@app.post("/login", response_model=TokenResponse)
def login(body: LoginRequest) -> TokenResponse:
    conn = get_db()
    try:
        row = conn.execute(
            "SELECT username, password_hash FROM users WHERE username = ?",
            (body.username,),
        ).fetchone()
        if row is None or not verify_password(body.password, row["password_hash"]):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        token = create_access_token(row["username"])
        return TokenResponse(
            access_token=token,
            expires_in=JWT_EXPIRE_MINUTES * 60,
        )
    finally:
        conn.close()



@app.get("/verify")
@app.post("/verify")
def verify(request: Request) -> dict:
    token = get_bearer_token(request)
    if not token:
        return {"status": "ok", "token_provided": False}
    payload = decode_token(token)
    return {"status": "ok", "token_provided": True, "subject": payload.get("sub")}


@app.get("/users")
def list_users(username: str = Depends(require_user)) -> dict:
    conn = get_db()
    try:
        rows = conn.execute("SELECT id, username FROM users").fetchall()
        return {
            "requested_by": username,
            "users": [{"id": row["id"], "username": row["username"]} for row in rows],
        }
    finally:
        conn.close()


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
