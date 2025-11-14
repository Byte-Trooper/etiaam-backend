# routes_profile.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from db import get_db
from models import User, Profile
from schemas import ProfileIn, ProfileOut
from auth import get_current_user

router = APIRouter(prefix="/api", tags=["Perfil"])

# ================================================================
# 🧩 PERFIL — crear o actualizar
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
# 🧩 Obtener perfil por ID
# ================================================================
@router.get("/profile/{user_id}", response_model=ProfileOut)
def get_profile(user_id: int, db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    if not profile:
        raise HTTPException(404, "Perfil no encontrado")
    return profile

# ================================================================
# 🧩 Perfil del usuario autenticado
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
# 🧩 Lista de pacientes
# ================================================================
@router.get("/pacientes")
def listar_pacientes(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
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
