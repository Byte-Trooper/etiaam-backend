from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional, List

# --- AUTENTICACIÓN / REGISTRO ---
class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    user_type: str
    consent_version: str
    consent_text: str

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class TokenOut(BaseModel):
    access_token: str
    user_type: str
    full_name: Optional[str] = None
    email: Optional[str] = None

# --- PERFIL ---
class ProfileIn(BaseModel):
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    edad: Optional[int] = None
    genero: Optional[str] = None
    especialidad: Optional[str] = None
    telefono: Optional[str] = None
    direccion: Optional[str] = None

class ProfileOut(ProfileIn):
    id: int
    class Config:
        from_attributes = True   # Pydantic v2 (reemplaza orm_mode)

# --- EVALUACIÓN ---
class EvaluationIn(BaseModel):
    user_id: int
    test_type: str
    score: float
    observaciones: Optional[str] = None

class EvaluationOut(EvaluationIn):
    id: int
    fecha_aplicacion: datetime
    class Config:
        from_attributes = True
