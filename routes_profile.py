# routes_profile.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db import get_db
from models import User, Profile, Evaluation
from schemas import ProfileIn, ProfileOut, EvaluationIn, EvaluationOut
from datetime import datetime
from auth import get_current_user

router = APIRouter(prefix="/api", tags=["Perfil y Evaluaciones"])

# ================================================================
# 🧩 PERFIL
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
        profile = Profile(user_id=user_id, **payload.dict(exclude_unset=True))
        db.add(profile)
    else:
        for key, value in payload.dict(exclude_unset=True).items():
            setattr(profile, key, value)

    db.commit()
    db.refresh(profile)
    return profile


@router.get("/profile/{user_id}", response_model=ProfileOut)
def get_profile(user_id: int, db: Session = Depends(get_db)):
    """Obtiene el perfil de un usuario por su ID (solo lectura)"""
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    if not profile:
        raise HTTPException(404, "Perfil no encontrado")
    return profile


# ================================================================
# 🧩 PERFIL del usuario autenticado
# ================================================================
@router.get("/me")
def get_my_profile(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Devuelve la información del usuario autenticado"""
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

# --- Lista de pacientes (solo visible para profesionales) ---
@router.get("/pacientes")
def listar_pacientes(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    """Devuelve la lista de todos los pacientes (solo accesible para profesionales)."""
    
    # 🔒 Verificar que sea profesional
    if not current_user or current_user.get("user_type") != "profesional":
        raise HTTPException(status_code=403, detail="Acceso restringido a profesionales de salud")
    
    pacientes = (
        db.query(User)
        .filter(User.user_type == "paciente")
        .all()
    )

    if not pacientes:
        return []

    # 🔹 Devolver información básica de los pacientes
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
# 🧩 EVALUACIONES
# ================================================================
from datetime import datetime

@router.post("/evaluations", response_model=EvaluationOut)
def create_evaluation(payload: EvaluationIn, db: Session = Depends(get_db)):
    # Si el usuario se obtiene del token, omite esta parte.
    # Aquí solo se valida si el ID existe.
    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(404, "Usuario no encontrado")

    evaluation = Evaluation(
        user_id=payload.user_id,
        test_type=payload.test_type,
        score=payload.score,
        fecha_aplicacion=datetime.utcnow(),
        observaciones=payload.observaciones
    )
    db.add(evaluation)
    db.commit()
    db.refresh(evaluation)

    # ✅ Convertimos el datetime a string para cumplir con el schema
    return {
        "id": evaluation.id,
        "user_id": evaluation.user_id,
        "test_type": evaluation.test_type,
        "score": evaluation.score,
        "fecha_aplicacion": evaluation.fecha_aplicacion.isoformat(),
        "observaciones": evaluation.observaciones,
    }



@router.get("/evaluations/{user_id}", response_model=list[EvaluationOut])
def get_user_evaluations(user_id: int, db: Session = Depends(get_db)):
    return db.query(Evaluation).filter(Evaluation.user_id == user_id).all()
