# routes_evaluations.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db import get_db
from models import Evaluation, CompetenciasProfesionales
from auth import get_current_user
from datetime import datetime
import json
from schemas import CompetenciasIn, CompetenciasOut

router = APIRouter(prefix="/api/evaluations", tags=["Evaluaciones"])

# ============================================================
# GUARDAR EVALUACIÓN GENERAL (AUTOMANEJO PACIENTE / PROFESIONAL)
# ============================================================
@router.post("")
def create_evaluation(payload: dict, db: Session = Depends(get_db)):

    if "user_id" not in payload or "test_type" not in payload:
        raise HTTPException(status_code=400, detail="Faltan campos obligatorios")

    new_eval = Evaluation(
        user_id = payload.get("user_id"),
        evaluador_id = payload.get("evaluador_id"),
        test_type = payload.get("test_type"),
        score = payload.get("score"),
        observaciones = payload.get("observaciones", ""),
        respuestas_json = json.dumps(payload.get("respuestas_json")),
        fecha_aplicacion = datetime.utcnow()
    )

    db.add(new_eval)
    db.commit()
    db.refresh(new_eval)

    parsed = None
    if new_eval.respuestas_json:
        try:
            parsed = json.loads(new_eval.respuestas_json)
        except:
            parsed = None

    return {
        "id": new_eval.id,
        "user_id": new_eval.user_id,
        "evaluador_id": new_eval.evaluador_id,
        "test_type": new_eval.test_type,
        "score": new_eval.score,
        "observaciones": new_eval.observaciones,
        "fecha_aplicacion": new_eval.fecha_aplicacion.isoformat(),
        "respuestas": parsed,
    }


# ============================================================
# OBTENER HISTORIAL DE EVALUACIONES
# ============================================================
@router.get("/{user_id}")
def get_evaluations(user_id: int, db: Session = Depends(get_db)):
    evaluations = (
        db.query(Evaluation)
        .filter(Evaluation.user_id == user_id)
        .order_by(Evaluation.fecha_aplicacion.desc())
        .all()
    )

    result = []
    for e in evaluations:
        parsed = None
        if e.respuestas_json:
            try:
                parsed = json.loads(e.respuestas_json)
            except:
                parsed = None

        result.append({
            "id": e.id,
            "user_id": e.user_id,
            "evaluador_id": e.evaluador_id,
            "test_type": e.test_type,
            "score": e.score,
            "observaciones": e.observaciones,
            "fecha_aplicacion": e.fecha_aplicacion.isoformat() if e.fecha_aplicacion else None,
            "respuestas": parsed
        })
    return result


# ============================================================
# COMPARACIÓN PACIENTE vs PROFESIONAL
# ============================================================
@router.get("/compare/{user_id}")
def compare_last_evaluations(user_id: int, db: Session = Depends(get_db)):

    paciente = (
        db.query(Evaluation)
        .filter(Evaluation.user_id == user_id, Evaluation.test_type == "automanejo_paciente")
        .order_by(Evaluation.fecha_aplicacion.desc())
        .first()
    )

    profesional = (
        db.query(Evaluation)
        .filter(Evaluation.user_id == user_id, Evaluation.test_type == "automanejo_prof")
        .order_by(Evaluation.fecha_aplicacion.desc())
        .first()
    )

    def _to_dict(e):
        if not e:
            return None
        parsed = None
        if e.respuestas_json:
            try:
                parsed = json.loads(e.respuestas_json)
            except:
                parsed = None
        return {
            "id": e.id,
            "user_id": e.user_id,
            "test_type": e.test_type,
            "score": e.score,
            "observaciones": e.observaciones,
            "fecha": e.fecha_aplicacion.isoformat(),
            "respuestas": parsed
        }

    return {
        "paciente": _to_dict(paciente),
        "profesional": _to_dict(profesional),
    }


# ============================================================
# GUARDAR TEST DE COMPETENCIAS
# ============================================================
@router.post("/competencias", response_model=CompetenciasOut)
def guardar_competencias(
    data: CompetenciasIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):

    registro = CompetenciasProfesionales(
        user_id=data.user_id,
        respuestas=data.respuestas,
        f1_promedio=data.f1_promedio,
        f2_promedio=data.f2_promedio,
        f3_promedio=data.f3_promedio,
        f4_promedio=data.f4_promedio,
        puntaje_total=data.puntaje_total,
        fecha_aplicacion=datetime.utcnow()
    )

    db.add(registro)
    db.commit()
    db.refresh(registro)
    return registro
