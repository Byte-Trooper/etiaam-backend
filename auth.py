# auth.py
import os, hashlib
from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

# Usa Argon2 en lugar de bcrypt
pwd_ctx = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
    # Opcional: endurecer parámetros
    # scheme_specific_settings={"argon2__memory_cost": 102400, "argon2__time_cost": 2, "argon2__parallelism": 8}
)

JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change")
JWT_ALG = "HS256"
JWT_EXP_MIN = int(os.getenv("JWT_EXP_MIN", "120"))

def hash_password(p: str) -> str:
    # puedes limitar por política (p.ej. 8–128 chars), pero Argon2 no requiere 72
    return pwd_ctx.hash(p)

def verify_password(p: str, h: str) -> bool:
    return pwd_ctx.verify(p, h)

def create_access_token(data: dict):
    to_encode = data.copy()
    to_encode.update({"exp": datetime.utcnow() + timedelta(minutes=JWT_EXP_MIN)})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALG)

def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        return {"id": int(payload.get("sub")), "user_type": payload.get("user_type")}
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")