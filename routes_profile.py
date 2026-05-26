# routes_profile.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import re

from db import get_db
from models import User, Profile
from schemas import ProfileIn, ProfileOut
from auth import get_current_user


router = APIRouter(prefix="/api", tags=["Perfil"])


# ================================================================
# FUNCIONES AUXILIARES
# ================================================================

def _payload_to_dict(payload: ProfileIn) -> dict:
    """
    Compatible con Pydantic v1 y v2.
    """
    if hasattr(payload, "model_dump"):
        return payload.model_dump(exclude_unset=True)
    return payload.dict(exclude_unset=True)


def _normalizar_telefono(raw_phone: str | None, default_country_code: str | None = "+52"):
    """
    Recibe teléfono completo (+528331234567) o 10 dígitos (8331234567)
    y regresa:
      country_code, phone_national, phone_number

    Reglas:
    - México: +52 + 10 dígitos
    - Perú: +51 + 10 dígitos, según la validación actual del proyecto
    """
    if not raw_phone:
        return None

    raw = str(raw_phone).strip()
    digits = re.sub(r"\D", "", raw)

    country_code = default_country_code if default_country_code in ["+52", "+51"] else "+52"

    if raw.startswith("+52") or digits.startswith("52"):
        country_code = "+52"
        if digits.startswith("52"):
            phone_national = digits[2:]
        else:
            phone_national = digits
    elif raw.startswith("+51") or digits.startswith("51"):
        country_code = "+51"
        if digits.startswith("51"):
            phone_national = digits[2:]
        else:
            phone_national = digits
    else:
        phone_national = digits

    # Nos quedamos con los últimos 10 dígitos por seguridad si llegó con lada.
    if len(phone_national) > 10:
        phone_national = phone_national[-10:]

    if not re.fullmatch(r"\d{10}", phone_national):
        raise HTTPException(
            status_code=400,
            detail="El teléfono debe contener exactamente 10 dígitos nacionales.",
        )

    phone_number = f"{country_code}{phone_national}"

    return {
        "country_code": country_code,
        "phone_national": phone_national,
        "phone_number": phone_number,
    }


def _sync_user_phone(
    user: User,
    telefono: str | None,
    db: Session,
):
    """
    Sincroniza el teléfono oficial de la cuenta en users.
    También permite conservar profiles.telefono como copia de compatibilidad.
    """
    parsed = _normalizar_telefono(
        telefono,
        default_country_code=user.country_code or "+52",
    )

    if parsed is None:
        return None

    # Validar duplicado si el número pertenece a otro usuario.
    existing = (
        db.query(User)
        .filter(
            User.phone_number == parsed["phone_number"],
            User.id != user.id,
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Número celular ya registrado por otro usuario.",
        )

    user.country_code = parsed["country_code"]
    user.phone_national = parsed["phone_national"]
    user.phone_number = parsed["phone_number"]

    return parsed


def _profile_response(user: User, profile: Profile | None):
    """
    Respuesta unificada:
    - Datos clínicos/personales desde profiles
    - Teléfono oficial desde users
    """
    return {
        "id": profile.id if profile else None,
        "user_id": user.id,

        "nombre": profile.nombre if profile else None,
        "apellido": profile.apellido if profile else None,
        "edad": profile.edad if profile else None,
        "genero": profile.genero if profile else None,

        # Campo conservado por compatibilidad, pero apunta al teléfono oficial.
        "telefono": user.phone_number or (profile.telefono if profile else None),

        "direccion": profile.direccion if profile else None,
        "especialidad": profile.especialidad if profile else None,
        "fecha_nacimiento": profile.fecha_nacimiento if profile else None,
        "nss": profile.nss if profile else None,
        "alergias": getattr(profile, "alergias", None) if profile else None,
        "cedula_profesional": profile.cedula_profesional if profile else None,
        "unidad_medica": profile.unidad_medica if profile else None,

        # Teléfono oficial de la cuenta
        "country_code": user.country_code,
        "phone_national": user.phone_national,
        "phone_number": user.phone_number,

        # Datos generales de la cuenta
        "email": user.email,
        "full_name": user.full_name,
        "user_type": user.user_type,
    }


# ================================================================
# CREAR / ACTUALIZAR PERFIL
# ================================================================
@router.post("/profile", response_model=ProfileOut)
def create_or_update_profile(
    payload: ProfileIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["id"]
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(404, "Usuario no encontrado")

    payload_data = _payload_to_dict(payload)

    # Si viene teléfono desde la pantalla de perfil, actualizar users.
    parsed_phone = None
    if "telefono" in payload_data and payload_data.get("telefono"):
        parsed_phone = _sync_user_phone(user, payload_data.get("telefono"), db)

        # Mantener profiles.telefono como copia de compatibilidad.
        payload_data["telefono"] = parsed_phone["phone_number"]

    # Buscar perfil
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()

    if not profile:
        profile = Profile(user_id=user_id, **payload_data)
        db.add(profile)
    else:
        for key, value in payload_data.items():
            setattr(profile, key, value)

    db.commit()
    db.refresh(user)
    db.refresh(profile)

    return _profile_response(user, profile)


# ================================================================
# OBTENER PERFIL
# ================================================================
@router.get("/profile/{user_id}", response_model=ProfileOut)
def get_profile(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    # El usuario puede consultar su propio perfil.
    # El profesional puede consultar perfiles de pacientes.
    if current_user["id"] != user_id and current_user.get("user_type") != "profesional":
        raise HTTPException(403, "Acceso restringido")

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(404, "Usuario no encontrado")

    profile = db.query(Profile).filter(Profile.user_id == user_id).first()

    return _profile_response(user, profile)


# ================================================================
# PERFIL DEL USUARIO LOGEADO
# ================================================================
@router.get("/me")
def get_my_profile(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.id == current_user["id"]).first()

    if not user:
        raise HTTPException(404, "Usuario no encontrado")

    profile = db.query(Profile).filter(Profile.user_id == user.id).first()

    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "user_type": user.user_type,

        # Teléfono oficial de la cuenta
        "country_code": user.country_code,
        "phone_national": user.phone_national,
        "phone_number": user.phone_number,

        "profile": _profile_response(user, profile) if profile else None,
    }


# ================================================================
# LISTA SIMPLE DE PACIENTES
# ================================================================
@router.get("/pacientes")
def listar_pacientes(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.get("user_type") != "profesional":
        raise HTTPException(403, "Acceso restringido a profesionales")

    pacientes = db.query(User).filter(User.user_type == "paciente").all()

    return [
        {
            "id": p.id,
            "full_name": p.full_name,
            "email": p.email,
            "user_type": p.user_type,

            # Teléfono oficial de la cuenta
            "telefono": p.phone_number,
            "country_code": p.country_code,
            "phone_national": p.phone_national,
            "phone_number": p.phone_number,
        }
        for p in pacientes
    ]


# ================================================================
# ENDPOINT COMPLETO DE PACIENTES
# ================================================================
@router.get("/pacientes/detalle")
def listar_pacientes_detalle(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.get("user_type") != "profesional":
        raise HTTPException(403, "Acceso restringido")

    pacientes = (
        db.query(User, Profile)
        .join(Profile, Profile.user_id == User.id)
        .filter(User.user_type == "paciente")
        .all()
    )

    resultado = []

    for user, profile in pacientes:
        resultado.append({
            "id": user.id,
            "nombre": profile.nombre,
            "apellido": profile.apellido,
            "full_name": f"{profile.nombre or ''} {profile.apellido or ''}".strip(),
            "nss": profile.nss or "00000",

            # Teléfono oficial de la cuenta
            "telefono": user.phone_number or profile.telefono,
            "country_code": user.country_code,
            "phone_national": user.phone_national,
            "phone_number": user.phone_number,

            "unidad_medica": profile.unidad_medica,
        })

    return resultado


# ================================================================
# INFORMACIÓN DE UN PACIENTE
# ================================================================
@router.get("/pacientes/info/{user_id}")
def obtener_info_paciente(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    # Solo profesionales pueden acceder
    if current_user["user_type"] != "profesional":
        raise HTTPException(403, "Acceso restringido")

    # Buscar usuario paciente
    user = (
        db.query(User)
        .filter(User.id == user_id, User.user_type == "paciente")
        .first()
    )

    if not user:
        raise HTTPException(404, "Paciente no encontrado")

    # Perfil asociado
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()

    if not profile:
        raise HTTPException(404, "Perfil no encontrado")

    # Construir nombre completo
    full_name = f"{profile.nombre or ''} {profile.apellido or ''}".strip()

    return {
        "id": user.id,
        "full_name": full_name,
        "nombre": profile.nombre,
        "apellido": profile.apellido,
        "genero": profile.genero,
        "edad": profile.edad,

        # Teléfono oficial de la cuenta
        "telefono": user.phone_number or profile.telefono,
        "country_code": user.country_code,
        "phone_national": user.phone_national,
        "phone_number": user.phone_number,

        "direccion": profile.direccion,
        "unidad_medica": profile.unidad_medica,
        "fecha_nacimiento": profile.fecha_nacimiento,
        "nss": profile.nss,
    }
