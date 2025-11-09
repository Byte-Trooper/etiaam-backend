# schemas.py
from pydantic import BaseModel, EmailStr
from typing import Optional, List

# ================================================================
# 🧩 AUTH (Login / Registro / Token)
# ================================================================
class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    user_type: str
    consent_text: str
    consent_version: str


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class TokenOut(BaseModel):
    access_token: str
    user_type: str
    full_name: str
    email: str


# ================================================================
# 🧩 PERFIL (unificado)
# ================================================================
class ProfileIn(BaseModel):
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    edad: Optional[int] = None
    genero: Optional[str] = None
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    especialidad: Optional[str] = None
    fecha_nacimiento: Optional[str] = None
    nss: Optional[str] = None
    alergias: Optional[str] = None


class ProfileOut(ProfileIn):
    id: int
    user_id: int

    class Config:
        from_attributes = True


# ================================================================
# 🧩 EVALUACIONES
# ================================================================
class EvaluationIn(BaseModel):
    test_type: str
    score: float
    observaciones: Optional[str] = None


class EvaluationOut(EvaluationIn):
    id: int
    user_id: int
    fecha_aplicacion: str

    class Config:
        from_attributes = True


class UserOut(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    user_type: str

    class Config:
        from_attributes = True
