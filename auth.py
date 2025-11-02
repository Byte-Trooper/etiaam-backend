import os, hashlib
from datetime import datetime, timedelta
from jose import jwt
from passlib.context import CryptContext

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change")
JWT_ALG = "HS256"
JWT_EXP_MIN = int(os.getenv("JWT_EXP_MIN", "120"))

def hash_password(p): return pwd_ctx.hash(p)
def verify_password(p, h): return pwd_ctx.verify(p, h)

def create_access_token(data: dict):
    to_encode = data.copy()
    to_encode.update({"exp": datetime.utcnow() + timedelta(minutes=JWT_EXP_MIN)})
    return jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALG)

def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
