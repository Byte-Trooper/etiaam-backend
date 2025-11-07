from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db import get_db
from models import User, Profile, Evaluation
from schemas import ProfileIn, ProfileOut, EvaluationIn, EvaluationOut
from datetime import datetime
from auth import get_current_user

router = APIRouter(prefix="/api", tags=["Perfil"])


# --- Perfil del usuario ---
@router.post("/profile", response_model=ProfileOut)
def create_or_update_profile(payload: ProfileIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        raise HTTPException(404, "Usuario no encontrado")
    
    profile = db.query(Profile).filter(Profile.user_id == payload.user_id).first()
    if not profile:
        profile = Profile(**payload.dict())
        db.add(profile)
    else:
        for key, value in payload.dict().items():
            setattr(profile, key, value)
    db.commit()
    db.refresh(profile)
    return profile

@router.get("/profile/{user_id}", response_model=ProfileOut)
def get_profile(user_id: int, db: Session = Depends(get_db)):
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    if not profile:
        raise HTTPException(404, "Perfil no encontrado")
    return profile

# --- Evaluaciones ---
@router.post("/evaluations", response_model=EvaluationOut)
def create_evaluation(payload: EvaluationIn, db: Session = Depends(get_db)):
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
    return evaluation

@router.get("/evaluations/{user_id}", response_model=list[EvaluationOut])
def get_user_evaluations(user_id: int, db: Session = Depends(get_db)):
    return db.query(Evaluation).filter(Evaluation.user_id == user_id).all()

@router.get("/me")
def get_my_profile(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Devuelve la información del usuario autenticado."""
    if not current_user or "id" not in current_user:
        raise HTTPException(status_code=401, detail="Token inválido o usuario no autenticado")

    # ✅ Aquí db ya es una sesión válida
    user = db.query(User).filter(User.id == current_user["id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "user_type": user.user_type,
    }
