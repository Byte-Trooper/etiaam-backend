# routes_evaluations.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db import get_db
from models import User, Evaluation
from auth import get_current_user
from datetime import datetime
from typing import Optional
import json

router = APIRouter(prefix="/api/evaluations", tags=["Evaluaciones"])

# 🧩 Crear o registrar una evaluación
@router.post("/")
def create_evaluation(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Registra una nueva evaluación.
    Ahora incluye almacenamiento del campo `respuestas_json` (lista de respuestas por pregunta).
    """
    try:
        user_id = payload.get("user_id")
        test_type = payload.get("test_type")
        score = payload.get("score")
        respuestas_json = payload.get("respuestas")  # 🆕 CAMBIO: antes 'respuestas_json'
        observaciones = payload.get("observaciones")

        if not user_id or not test_type:
            raise HTTPException(status_code=400, detail="Faltan campos requeridos")

        evaluacion = Evaluation(
            user_id=user_id,
            evaluador_id=current_user.get("id"),  # Si es paciente, es el mismo id
            test_type=test_type,
            score=score,
            respuestas_json=json.dumps(respuestas_json or {"preguntas": []}),  # 🆕 Guarda el JSON
            observaciones=observaciones,
            fecha_aplicacion=datetime.utcnow()
        )

        db.add(evaluacion)
        db.commit()
        db.refresh(evaluacion)

        return {
            "status": "ok",
            "evaluation_id": evaluacion.id,
            "message": "Evaluación registrada correctamente"
        }

    except Exception as e:
        print("❌ Error en create_evaluation:", e)
        raise HTTPException(status_code=500, detail=str(e))


# 🧩 Obtener todas las evaluaciones de un paciente
@router.get("/{user_id}")
def get_evaluations(user_id: int, db: Session = Depends(get_db)):
    """
    Devuelve todas las evaluaciones del paciente, incluyendo las respuestas JSON.
    """
    evaluaciones = (
        db.query(Evaluation)
        .filter(Evaluation.user_id == user_id)
        .order_by(Evaluation.fecha_aplicacion.desc())
        .all()
    )

    if not evaluaciones:
        raise HTTPException(status_code=404, detail="No se encontraron evaluaciones")

    return [
        {
            "id": e.id,
            "test_type": e.test_type,
            "score": e.score,
            "evaluador_id": e.evaluador_id,
            "fecha_aplicacion": e.fecha_aplicacion,
            "observaciones": e.observaciones,
            # 🆕 Devuelve el JSON parseado si existe
            "respuestas": json.loads(e.respuestas_json) if e.respuestas_json else None
        }
        for e in evaluaciones
    ]


# 🧩 Comparar evaluación paciente vs profesional
@router.get("/compare/{user_id}")
def compare_evaluations(user_id: int, db: Session = Depends(get_db)):
    """
    Devuelve la última evaluación del paciente y del profesional,
    incluyendo las respuestas individuales y la diferencia.
    """
    paciente_eval = (
        db.query(Evaluation)
        .filter(Evaluation.user_id == user_id, Evaluation.evaluador_id == None)
        .order_by(Evaluation.fecha_aplicacion.desc())
        .first()
    )
    profesional_eval = (
        db.query(Evaluation)
        .filter(Evaluation.user_id == user_id, Evaluation.evaluador_id != None)
        .order_by(Evaluation.fecha_aplicacion.desc())
        .first()
    )

    if not paciente_eval and not profesional_eval:
        raise HTTPException(status_code=404, detail="Sin evaluaciones registradas")

    def format_eval(e: Optional[Evaluation]):
        if not e:
            return None
        return {
            "id": e.id,
            "score": e.score,
            "fecha": e.fecha_aplicacion,
            "observaciones": e.observaciones,
            "respuestas": json.loads(e.respuestas_json) if e.respuestas_json else None,  # 🆕 Nuevo campo
        }

    return {
        "paciente": format_eval(paciente_eval),
        "profesional": format_eval(profesional_eval),
        "diferencia": (
            None
            if not paciente_eval or not profesional_eval
            else profesional_eval.score - paciente_eval.score
        ),
    }
