import os
import re
import time
import uuid
import datetime
from typing import Optional

import bcrypt
import jwt
from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from database.dbmysql import get_db_conn


# ---------------------------------------------------------------------------
# Konfigurasi JWT (ambil dari .env, fallback default DEV)
# ---------------------------------------------------------------------------
JWT_SECRET = os.environ.get("JWT_SECRET", "ganti-secret-ini-di-production-please")
JWT_ALGORITHM = os.environ.get("JWT_ALGORITHM", "HS256")
JWT_EXPIRES_MIN = int(os.environ.get("JWT_EXPIRES_MIN", "720"))  # default 12 jam


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------
class LoginRequest(BaseModel):
    identity: str = Field(..., min_length=1, max_length=100,
                          description="Email atau username (wajib)")
    password: str = Field(..., min_length=1, max_length=255,
                          description="Password (wajib)")


class RegisterRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=100,
                       description="Email user (wajib)")
    password: str = Field(..., min_length=6, max_length=255,
                          description="Password (wajib, min 6 karakter)")
    username: Optional[str] = Field(None, max_length=100,
                                    description="Username (opsional, auto-generate dari email kalau kosong)")
    first_name: Optional[str] = Field(None, max_length=50)
    last_name: Optional[str] = Field(None, max_length=50)
    phone: Optional[str] = Field(None, max_length=20)
    company: Optional[str] = Field(None, max_length=100)


# ---------------------------------------------------------------------------
# API Router
# ---------------------------------------------------------------------------
router = APIRouter(prefix="/api/auth", tags=["Auth"])

# HTTPBearer: auto_error=False supaya kita bisa custom message saat 401
bearer_scheme = HTTPBearer(auto_error=False)


# ---------------------------------------------------------------------------
# Password & token utilities
# ---------------------------------------------------------------------------
def verify_password(plain: str, hashed: str) -> bool:
    if not plain or not hashed:
        return False
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except Exception:
        return False


def hash_password(plain: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(plain.encode("utf-8"), salt).decode("utf-8")


def _is_email(s: str) -> bool:
    return bool(re.match(r"[^@]+@[^@]+\.[^@]+", s))


def _now_utc() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def create_access_token(user_id: int, username: str) -> dict:
    """
    Buat JWT untuk user. Return dict {token, jti, exp_iso}.
    """
    jti = uuid.uuid4().hex
    iat = _now_utc()
    exp = iat + datetime.timedelta(minutes=JWT_EXPIRES_MIN)
    payload = {
        "sub": str(user_id),
        "username": username,
        "jti": jti,
        "iat": int(iat.timestamp()),
        "exp": int(exp.timestamp()),
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    # PyJWT >=2 mengembalikan str
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return {"token": token, "jti": jti, "exp": exp}


def decode_token(token: str) -> dict:
    """
    Decode + validasi tanda tangan & expiry. Raises jwt.PyJWTError jika invalid.
    """
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------
def _find_user_by_identity(cursor, identity: str):
    """
    Cari user berdasarkan email (jika identity berbentuk email) atau username.
    """
    identity = identity.strip()
    if _is_email(identity):
        cursor.execute("""
            SELECT id, username, password, email, active, first_name, last_name
            FROM users WHERE email = %s LIMIT 1
        """, (identity,))
    else:
        cursor.execute("""
            SELECT id, username, password, email, active, first_name, last_name
            FROM users WHERE username = %s LIMIT 1
        """, (identity,))
    return cursor.fetchone()


def _is_token_revoked(cursor, jti: str) -> bool:
    cursor.execute("SELECT jti FROM auth_revoked_tokens WHERE jti = %s LIMIT 1", (jti,))
    return cursor.fetchone() is not None


def _revoke_token(cursor, jti: str, user_id: int, exp_ts: int):
    exp_dt = datetime.datetime.utcfromtimestamp(exp_ts).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("""
        INSERT IGNORE INTO auth_revoked_tokens (jti, user_id, expires_at)
        VALUES (%s, %s, %s)
    """, (jti, user_id, exp_dt))


def _cleanup_expired_revoked(cursor):
    """Best-effort: hapus token blacklist yang sudah lewat expiry-nya."""
    try:
        cursor.execute("DELETE FROM auth_revoked_tokens WHERE expires_at < NOW()")
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Dependency: protect endpoints (gunakan di module lain via Depends(get_current_user))
# ---------------------------------------------------------------------------
def get_current_user(
    response: Response,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
):
    """
    Verifikasi Bearer token & kembalikan user dict.
    Pasang sebagai dependency endpoint yang butuh auth:
        @router.get("/...")
        def handler(user = Depends(get_current_user)): ...
    """
    if not credentials or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return {"status": False, "message": "Token tidak ditemukan"}

    try:
        payload = decode_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return {"status": False, "message": "Token sudah kadaluarsa"}
    except jwt.PyJWTError:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return {"status": False, "message": "Token tidak valid"}

    jti = payload.get("jti")
    sub = payload.get("sub")
    if not jti or not sub:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return {"status": False, "message": "Token tidak valid"}

    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            if _is_token_revoked(cursor, jti):
                response.status_code = status.HTTP_401_UNAUTHORIZED
                return {"status": False, "message": "Token sudah di-revoke (logout)"}

            cursor.execute("""
                SELECT id, username, email, active, first_name, last_name
                FROM users WHERE id = %s LIMIT 1
            """, (int(sub),))
            user = cursor.fetchone()

            if not user:
                response.status_code = status.HTTP_401_UNAUTHORIZED
                return {"status": False, "message": "User tidak ditemukan"}

            if not user.get("active"):
                response.status_code = status.HTTP_403_FORBIDDEN
                return {"status": False, "message": "Akun user dinonaktifkan"}

            user_dict = dict(user)
            user_dict["_token_jti"] = jti
            user_dict["_token_exp"] = int(payload.get("exp", 0))
            return user_dict
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# POST /api/auth/register
# ---------------------------------------------------------------------------
@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(request: Request, body: RegisterRequest, response: Response):
    """
    Body: {email, password, username?, first_name?, last_name?, phone?, company?}
    Membuat akun baru + langsung mengembalikan token JWT (auto-login).
    """
    email = body.email.strip().lower()
    if not _is_email(email):
        response.status_code = status.HTTP_400_BAD_REQUEST
        return {"status": False, "message": "Format email tidak valid"}

    # Tentukan username: dari input, atau auto-generate dari nama/email
    raw_username = (body.username or "").strip()
    if not raw_username:
        raw_username = f"{body.first_name or ''} {body.last_name or ''}".strip().lower()
        if not raw_username:
            raw_username = email.split("@")[0].lower()
    # Sanitasi: hilangkan spasi ganda
    username = re.sub(r"\s+", " ", raw_username)

    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            # Cek email unik
            cursor.execute("SELECT id FROM users WHERE email = %s LIMIT 1", (email,))
            if cursor.fetchone():
                response.status_code = status.HTTP_409_CONFLICT
                return {"status": False, "message": "Email sudah terdaftar"}

            # Cek username unik
            cursor.execute("SELECT id FROM users WHERE username = %s LIMIT 1", (username,))
            if cursor.fetchone():
                response.status_code = status.HTTP_409_CONFLICT
                return {"status": False, "message": "Username sudah terdaftar"}

            ip_address = request.client.host if request.client else "127.0.0.1"
            hashed_pwd = hash_password(body.password)
            created_on = int(time.time())

            cursor.execute("""
                INSERT INTO users
                    (ip_address, username, password, email, created_on, active,
                     first_name, last_name, company, phone)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                ip_address,
                username,
                hashed_pwd,
                email,
                created_on,
                1,  # default active
                body.first_name,
                body.last_name,
                body.company,
                body.phone,
            ))
            new_id = cursor.lastrowid

            issued = create_access_token(new_id, username)
            return {
                "status": True,
                "message": "Registrasi berhasil",
                "data": {
                    "token": issued["token"],
                    "token_type": "Bearer",
                    "expires_at": issued["exp"].strftime("%Y-%m-%d %H:%M:%S"),
                    "user": {
                        "id": new_id,
                        "username": username,
                        "email": email,
                        "first_name": body.first_name,
                        "last_name": body.last_name,
                    },
                },
            }
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"status": False, "message": f"Gagal registrasi: {str(e)}"}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# POST /api/auth/login
# ---------------------------------------------------------------------------
@router.post("/login")
def login(request: Request, body: LoginRequest, response: Response):
    """
    Body: {identity, password}
      - `identity` boleh email atau username.
    Return: token JWT + data user.
    """
    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            user = _find_user_by_identity(cursor, body.identity)

            # Gunakan pesan generik untuk mencegah user enumeration
            if not user:
                response.status_code = status.HTTP_401_UNAUTHORIZED
                return {"status": False, "message": "Identitas atau password salah"}

            if not verify_password(body.password, user["password"]):
                response.status_code = status.HTTP_401_UNAUTHORIZED
                return {"status": False, "message": "Identitas atau password salah"}

            if not user.get("active"):
                response.status_code = status.HTTP_403_FORBIDDEN
                return {"status": False, "message": "Akun user dinonaktifkan"}

            # Update last_login (best effort — kolom mungkin belum ada di schema lama)
            try:
                cursor.execute(
                    "UPDATE users SET last_login = %s WHERE id = %s",
                    (int(time.time()), user["id"]),
                )
            except Exception:
                pass

            issued = create_access_token(user["id"], user["username"])
            return {
                "status": True,
                "message": "Login berhasil",
                "data": {
                    "token": issued["token"],
                    "token_type": "Bearer",
                    "expires_at": issued["exp"].strftime("%Y-%m-%d %H:%M:%S"),
                    "user": {
                        "id": user["id"],
                        "username": user["username"],
                        "email": user["email"],
                        "first_name": user.get("first_name"),
                        "last_name": user.get("last_name"),
                    },
                },
            }
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"status": False, "message": f"Gagal login: {str(e)}"}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# POST /api/auth/logout
# ---------------------------------------------------------------------------
@router.post("/logout")
def logout(response: Response, credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)):
    """
    Header: `Authorization: Bearer <token>`
    Menambahkan jti token ke blacklist agar tidak bisa dipakai lagi.
    """
    if not credentials or credentials.scheme.lower() != "bearer" or not credentials.credentials:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return {"status": False, "message": "Token tidak ditemukan"}

    try:
        payload = decode_token(credentials.credentials)
    except jwt.ExpiredSignatureError:
        # Sudah expired = sudah invalid → anggap logout sukses
        return {"status": True, "message": "Token sudah kadaluarsa, logout dianggap sukses"}
    except jwt.PyJWTError:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return {"status": False, "message": "Token tidak valid"}

    jti = payload.get("jti")
    sub = payload.get("sub")
    exp = int(payload.get("exp", 0))
    if not jti or not sub or not exp:
        response.status_code = status.HTTP_401_UNAUTHORIZED
        return {"status": False, "message": "Token tidak valid"}

    conn = get_db_conn()
    try:
        with conn.cursor() as cursor:
            _revoke_token(cursor, jti, int(sub), exp)
            _cleanup_expired_revoked(cursor)
            return {"status": True, "message": "Logout berhasil"}
    except Exception as e:
        response.status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        return {"status": False, "message": f"Gagal logout: {str(e)}"}
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# GET /api/auth/me
# ---------------------------------------------------------------------------
@router.get("/me")
def me(user=Depends(get_current_user)):
    """
    Header: `Authorization: Bearer <token>`
    Mengembalikan data user yang sedang login.
    """
    # Jika dependency mengembalikan error (status False), passthrough
    if isinstance(user, dict) and user.get("status") is False:
        return user

    return {
        "status": True,
        "data": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "first_name": user.get("first_name"),
            "last_name": user.get("last_name"),
            "active": bool(user.get("active")),
        },
    }
