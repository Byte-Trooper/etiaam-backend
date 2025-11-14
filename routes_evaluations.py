# routes_evaluations.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db import get_db
from models import Evaluation
from auth import get_current_user
from datetime import datetime
import json

router = APIRouter(prefix="/api/evaluations", tags=["Evaluaciones"])

@router.post("/")
def create_evaluation(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Crear una evaluación de automanejo.
    El frontend envía:
    {
      "user_id": 31,
      "evaluador_id": 15,
      "test_type": "automanejo_prof",
      "score": 5.75,
      "respuestas_json": {"preguntas": [...]},
      "observaciones": ""
    }
    """

    required = ["user_id", "test_type", "score", "respuestas_json"]
    for field in required:
        if field not in payload:
            raise HTTPException(400, f"Falta el campo obligatorio: {field}")

    try:
        new_eval = Evaluation(
            user_id=payload["user_id"],
            evaluador_id=payload.get("evaluador_id"),
            test_type=payload["test_type"],
            score=payload["score"],
            respuestas_json=json.dumps(payload["respuestas_json"]),
            observaciones=payload.get("observaciones", ""),
            fecha_aplicacion=datetime.utcnow()
        )

        db.add(new_eval)
        db.commit()
        db.refresh(new_eval)

        return {
            "status": "success",
            "id": new_eval.id,
            "message": "Evaluación guardada correctamente"
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"Error al guardar la evaluación: {str(e)}")


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
        # Parsear respuestas_json (string) -> dict con 'preguntas'
        parsed = None
        if e.respuestas_json:
            try:
                parsed = json.loads(e.respuestas_json)
            except Exception:
                parsed = None

        result.append({
            "id": e.id,
            "user_id": e.user_id,
            "evaluador_id": e.evaluador_id,
            "test_type": e.test_type,
            "score": e.score,
            "observaciones": e.observaciones or "",
            "fecha_aplicacion": e.fecha_aplicacion.isoformat() if e.fecha_aplicacion else None,
            # clave que tu app ya espera:
            "respuestas": parsed  # <- importante
        })
    return result


@router.get("/compare/{user_id}")
def compare_last_evaluations(user_id: int, db: Session = Depends(get_db)):
    # última del paciente
    paciente = (
        db.query(Evaluation)
        .filter(Evaluation.user_id == user_id, Evaluation.test_type == "automanejo_paciente")
        .order_by(Evaluation.fecha_aplicacion.desc())
        .first()
    )
    # última del profesional
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
            except Exception:
                parsed = None
        return {
            "id": e.id,
            "user_id": e.user_id,
            "test_type": e.test_type,
            "score": e.score,
            "observaciones": e.observaciones or "",
            "fecha": e.fecha_aplicacion.isoformat() if e.fecha_aplicacion else None,
            # clave que usa tu ComparacionAutomanejoScreen:
            "respuestas": parsed
        }

    return {
        "paciente": _to_dict(paciente),
        "profesional": _to_dict(profesional)
    }
