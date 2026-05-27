# schemas.py
from pydantic import BaseModel, EmailStr, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime
import re


# ================================================================
# AUTH (Login / Registro / Token)
# ================================================================
class RegisterIn(BaseModel):
    email: Optional[EmailStr] = None
    password: str
    full_name: str
    user_type: str

    # Teléfono para login
    country_code: str
    phone_national: str
    phone_number: str

    consent_text: str
    consent_version: str

    @field_validator("country_code")
    @classmethod
    def validate_country_code(cls, value):
        if value not in ["+52", "+51"]:
            raise ValueError("La lada debe ser +52 para México o +51 para Perú")
        return value

    @field_validator("phone_national")
    @classmethod
    def validate_phone_national(cls, value):
        if not re.fullmatch(r"\d{10}", value):
            raise ValueError("El número celular debe tener exactamente 10 dígitos")
        return value

    @field_validator("phone_number")
    @classmethod
    def validate_phone_number(cls, value):
        if not re.fullmatch(r"\+\d{12}", value):
            raise ValueError(
                "El número completo debe incluir lada y 10 dígitos. Ejemplo: +528331234567"
            )
        return value


class LoginIn(BaseModel):
    # Puede ser correo electrónico o celular de 10 dígitos
    identifier: str
    password: str

    # Se usa cuando identifier es celular de 10 dígitos
    country_code: Optional[str] = None

    @field_validator("identifier")
    @classmethod
    def validate_identifier(cls, value):
        value = value.strip()

        if not value:
            raise ValueError("Debes ingresar correo electrónico o celular")

        is_email = "@" in value
        is_phone = re.fullmatch(r"\d{10}", value)

        if not is_email and not is_phone:
            raise ValueError("Ingresa un correo válido o un celular de 10 dígitos")

        return value

    @field_validator("country_code")
    @classmethod
    def validate_login_country_code(cls, value):
        if value is not None and value not in ["+52", "+51"]:
            raise ValueError("La lada debe ser +52 para México o +51 para Perú")
        return value


class TokenOut(BaseModel):
    access_token: str
    user_type: str
    full_name: str
    email: Optional[str] = None

    # Campos opcionales para Flutter
    country_code: Optional[str] = None
    phone_national: Optional[str] = None
    phone_number: Optional[str] = None


# ================================================================
# RECUPERACIÓN DE CONTRASEÑA
# ================================================================
class ForgotPasswordIn(BaseModel):
    email: EmailStr


class ResetPasswordIn(BaseModel):
    email: EmailStr
    code: str
    new_password: str

    @field_validator("code")
    @classmethod
    def validate_code(cls, value):
        value = value.strip()

        if not re.fullmatch(r"\d{6}", value):
            raise ValueError("El código debe tener exactamente 6 dígitos")

        return value

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, value):
        if len(value) < 6:
            raise ValueError("La contraseña debe tener mínimo 6 caracteres")

        if not re.search(r"[A-Z]", value):
            raise ValueError("La contraseña debe incluir una mayúscula")

        if not re.search(r"[0-9]", value):
            raise ValueError("La contraseña debe incluir un número")

        if not re.search(r'[!@#\$%^&*(),.?":{}|<>]', value):
            raise ValueError("La contraseña debe incluir un carácter especial")

        return value


class MessageOut(BaseModel):
    message: str


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
    id: Optional[int] = None
    user_id: int

    # Teléfono oficial de la cuenta, almacenado en users
    country_code: Optional[str] = None
    phone_national: Optional[str] = None
    phone_number: Optional[str] = None

    # Datos generales de la cuenta
    email: Optional[str] = None
    full_name: Optional[str] = None
    user_type: Optional[str] = None

    class Config:
        from_attributes = True


# ================================================================
# EVALUACIONES (Automanejo Paciente / Profesional)
# ================================================================
class EvaluationIn(BaseModel):
    user_id: Optional[int] = None
    test_type: str
    score: Optional[int] = None
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

    # Campos opcionales de teléfono
    country_code: Optional[str] = None
    phone_national: Optional[str] = None
    phone_number: Optional[str] = None

    class Config:
        from_attributes = True


# =============================================================
#     SCHEMA PARA TEST DE COMPETENCIAS PROFESIONALES
# =============================================================
class CompetenciasIn(BaseModel):
    user_id: int
    respuestas: Dict[str, Any]
    f1_promedio: float
    f2_promedio: float
    f3_promedio: float
    f4_promedio: float
    puntaje_total: float


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
        from_attributes = True


# =============================================================
#     SCHEMA PARA PLAN DE TRABAJO
# =============================================================
class ObjetivoPlanCreate(BaseModel):
    descripcion: str
    actividad: str
    recursos: Optional[str] = None
    seguimiento: Optional[str] = None
    cumplimiento: int = 0


class PlanTrabajoCreate(BaseModel):
    paciente_id: int
    profesional_id: int
    objetivo_principal: str
    plan_ejecucion: str
    recursos_necesarios: Optional[str] = None
    emociones_asociadas: Optional[str] = None
    objetivos: List[ObjetivoPlanCreate]


class PlanTrabajoOut(BaseModel):
    id: int
    paciente_id: int
    profesional_id: int
    fecha_creacion: datetime
    objetivo_principal: str
    plan_ejecucion: str
    recursos_necesarios: str
    emociones_asociadas: str
    estado: str

    class Config:
        from_attributes = True