# auth.py
import os
import hashlib
from datetime import datetime, timedelta

from jose import jwt, JWTError
from passlib.context import CryptContext
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer


# ================================================================
# CONFIGURACIÓN DE CONTRASEÑAS
# ================================================================
# Usa Argon2 en lugar de bcrypt
pwd_ctx = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
    # Opcional: endurecer parámetros
    # scheme_specific_settings={
    #     "argon2__memory_cost": 102400,
    #     "argon2__time_cost": 2,
    #     "argon2__parallelism": 8
    # }
)


# ================================================================
# CONFIGURACIÓN JWT
# ================================================================
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change")
JWT_ALG = "HS256"
JWT_EXP_MIN = int(os.getenv("JWT_EXP_MIN", "120"))


# ================================================================
# FUNCIONES DE CONTRASEÑA
# ================================================================
def hash_password(p: str) -> str:
    return pwd_ctx.hash(p)


def verify_password(p: str, h: str) -> bool:
    return pwd_ctx.verify(p, h)


# ================================================================
# CREAR TOKEN JWT
# ================================================================
def create_access_token(data: dict):
    to_encode = data.copy()
    to_encode.update(
        {
            "exp": datetime.utcnow() + timedelta(minutes=JWT_EXP_MIN)
        }
    )
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALG)


# ================================================================
# HASH SHA256 PARA CONSENTIMIENTO
# ================================================================
def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ================================================================
# OAUTH2
# ================================================================
# Se mantiene tokenUrl="login" porque tu endpoint actual parece ser /login
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


# ================================================================
# USUARIO ACTUAL DESDE TOKEN
# ================================================================
def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])

        user_id = payload.get("sub")
        user_type = payload.get("user_type")

        if user_id is None:
            raise HTTPException(
                status_code=401,
                detail="Token inválido: usuario no encontrado",
            )

        return {
            "id": int(user_id),
            "user_type": user_type,
        }

    except JWTError:
        raise HTTPException(
            status_code=401,
            detail="Token inválido o expirado",
        )
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        return {"id": int(payload.get("sub")), "user_type": payload.get("user_type")}
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido o expirado")