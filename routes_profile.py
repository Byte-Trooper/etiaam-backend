# routes_profile.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db import get_db
from models import User, Profile
from schemas import ProfileIn, ProfileOut
from auth import get_current_user

router = APIRouter(prefix="/api", tags=["Perfil"])


# ================================================================
# 🧩 CREAR / ACTUALIZAR PERFIL
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

    # buscar perfil
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()

    if not profile:
        profile = Profile(user_id=user_id, **payload.dict(exclude_unset=True))
        db.add(profile)
    else:
        for key, value in payload.dict(exclude_unset=True).items():
            setattr(profile, key, value)

    db.commit()
    db.refresh(profile)
    return profile


# ================================================================
# 🧩 OBTENER PERFIL
# ================================================================
@router.get("/profile/{user_id}", response_model=ProfileOut)
def get_profile(user_id: int, db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    if not profile:
        raise HTTPException(404, "Perfil no encontrado")
    return profile


# ================================================================
# 🧩 PERFIL DEL USUARIO LOGEADO
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
        "profile": profile.__dict__ if profile else None,
    }


# ================================================================
# 🧩 LISTA SIMPLE DE PACIENTES (ACTUAL)
# ================================================================
@router.get("/pacientes")
def listar_pacientes(current_user: dict = Depends(get_current_user),
                     db: Session = Depends(get_db)):

    if current_user.get("user_type") != "profesional":
        raise HTTPException(403, "Acceso restringido a profesionales")

    pacientes = db.query(User).filter(User.user_type == "paciente").all()

    return [
        {
            "id": p.id,
            "full_name": p.full_name,
            "email": p.email,
            "user_type": p.user_type
        }
        for p in pacientes
    ]


# ================================================================
# 🆕 NUEVO ENDPOINT COMPLETO (RECOMENDADO)
# ================================================================
@router.get("/pacientes/detalle")
def listar_pacientes_detalle(current_user: dict = Depends(get_current_user),
                             db: Session = Depends(get_db)):

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
            "full_name": f"{profile.nombre} {profile.apellido}",
            "nss": profile.nss or "00000",
            "telefono": profile.telefono,
            "unidad_medica": profile.unidad_medica,
        })

    return resultado

# ================================================================
# 🆕 DETALLE COMPLETO DEL PACIENTE (User + Profile)
# ================================================================
@router.get("/pacientes/detalle/{user_id}")
def detalle_paciente(user_id: int, 
                     db: Session = Depends(get_db), 
                     current_user: dict = Depends(get_current_user)):

    # Solo profesionales pueden consultar
    if current_user.get("user_type") != "profesional":
        raise HTTPException(403, "Acceso restringido a profesionales")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "Usuario no encontrado")

    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    if not profile:
        # Aún no tiene perfil → devolvemos datos básicos
        return {
            "user_id": user.id,
            "full_name": user.full_name,
            "email": user.email,
            "genero": "",
            "edad": "",
            "telefono": "",
            "direccion": "",
            "unidad_medica": "",
            "fecha_nacimiento": "",
            "nss": "00000"
        }

    # Construimos full_name seguro
    nombre = profile.nombre or ""
    apellido = profile.apellido or ""
    full_name = f"{nombre} {apellido}".strip() or user.full_name

    return {
        "user_id": user.id,
        "full_name": full_name,
        "email": user.email,
        "genero": profile.genero or "",
        "edad": profile.edad or "",
        "telefono": profile.telefono or "",
        "direccion": profile.direccion or "",
        "unidad_medica": profile.unidad_medica or "",
        "fecha_nacimiento": profile.fecha_nacimiento or "",
        "nss": profile.nss or "00000"
    }
