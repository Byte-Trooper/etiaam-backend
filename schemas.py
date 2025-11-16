# schemas.py
from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any

# ================================================================
# AUTH (Login / Registro / Token)
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
# PERFIL (unificado)
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
    cedula_profesional: Optional[str] = None
    unidad_medica: Optional[str] = None

class ProfileOut(ProfileIn):
    id: int
    user_id: int

    class Config:
        from_attributes = True


# ================================================================
# EVALUACIONES (Automanejo Paciente / Profesional)
# ================================================================
class EvaluationIn(BaseModel):
    user_id: Optional[int] = None
    test_type: str
    score: float
    respuestas: Optional[dict] = None
    observaciones: Optional[str] = None

class EvaluationOut(EvaluationIn):
    id: int
    user_id: int
    fecha_aplicacion: str
    respuestas: Optional[dict]

    class Config:
        from_attributes = True


class UserOut(BaseModel):
    id: int
    email: str
    full_name: Optional[str]
    user_type: str

    class Config:
        from_attributes = True


# ================================================================
# TEST DE COMPETENCIAS PROFESIONALES
# ================================================================
class CompetenciasIn(BaseModel):
    user_id: int
    respuestas: Dict[str, Any]      # JSON de respuestas completas
    f1_promedio: float
    f2_promedio: float
    f3_promedio: float
    f4_promedio: float
    puntaje_total: float            # promedio total


class CompetenciasOut(BaseModel):
    id: int
    user_id: int
    respuestas: Dict[str, Any]
    f1_promedio: float
    f2_promedio: float
    f3_promedio: float
    f4_promedio: float
    puntaje_total: float
    fecha_aplicacion: Optional[str] = None

    class Config:
        orm_mode = True
