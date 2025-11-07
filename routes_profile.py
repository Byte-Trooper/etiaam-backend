# routes_profile.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
from db import get_db
from models import User, Profile, Evaluation
from schemas import ProfileIn, ProfileOut, EvaluationIn, EvaluationOut
from auth import get_current_user

router = APIRouter(prefix="/api", tags=["Perfil"])

# ================================================================
# 🧩 PERFIL DEL USUARIO (Crear / Actualizar / Consultar)
# ================================================================

@router.post("/profile", response_model=ProfileOut)
def create_or_update_profile(
    payload: ProfileIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Crea o actualiza el perfil del usuario autenticado"""
    user_id = current_user["id"]

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "Usuario no encontrado")

    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    if not profile:
        # Crear nuevo perfil
        profile = Profile(**payload.dict(), user_id=user_id)
        db.add(profile)
    else:
        # Actualizar campos existentes
        for key, value in payload.dict().items():
            setattr(profile, key, value)

    db.commit()
    db.refresh(profile)
    return profile


@router.get("/profile/me", response_model=ProfileOut)
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Obtiene el perfil del usuario autenticado"""
    user_id = current_user["id"]
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    if not profile:
        raise HTTPException(404, "Perfil no encontrado")
    return profile


@router.get("/profile/{user_id}", response_model=ProfileOut)
def get_profile_by_id(user_id: int, db: Session = Depends(get_db)):
    """Obtiene el perfil por ID (solo para pruebas o administradores)"""
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    if not profile:
        raise HTTPException(404, "Perfil no encontrado")
    return profile


# ================================================================
# 🧩 EVALUACIONES
# ================================================================

@router.post("/evaluations", response_model=EvaluationOut)
def create_evaluation(
    payload: EvaluationIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Guarda una evaluación asociada al usuario autenticado"""
    user_id = current_user["id"]

    evaluation = Evaluation(
        user_id=user_id,
        test_type=payload.test_type,
        score=payload.score,
        fecha_aplicacion=datetime.utcnow(),
        observaciones=payload.observaciones
    )
    db.add(evaluation)
    db.commit()
    db.refresh(evaluation)
    return evaluation


@router.get("/evaluations/me", response_model=list[EvaluationOut])
def get_my_evaluations(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Devuelve todas las evaluaciones del usuario autenticado"""
    user_id = current_user["id"]
    return db.query(Evaluation).filter(Evaluation.user_id == user_id).all()


@router.get("/evaluations/{user_id}", response_model=list[EvaluationOut])
def get_user_evaluations(user_id: int, db: Session = Depends(get_db)):
    """Consulta evaluaciones por ID (uso administrativo)"""
    return db.query(Evaluation).filter(Evaluation.user_id == user_id).all()


# ================================================================
# 🧩 DATOS BÁSICOS DEL USUARIO (para Flutter / autenticación)
# ================================================================

@router.get("/me")
def get_user_info(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Devuelve la información básica del usuario autenticado"""
    user = db.query(User).filter(User.id == current_user["id"]).first()
    if not user:
        raise HTTPException(404, "Usuario no encontrado")

    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "user_type": user.user_type,
    }
