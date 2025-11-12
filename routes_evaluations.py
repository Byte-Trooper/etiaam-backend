# routes_evaluations.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db import get_db
from models import Evaluation
from auth import get_current_user
from datetime import datetime
from typing import Optional
import json

router = APIRouter(prefix="/api/evaluations", tags=["Evaluaciones"])

# ============================================================
# 🧩 Crear o registrar una evaluación (con autenticación)
# ============================================================
@router.post("/")
def create_evaluation(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)  # ✅ ahora vuelve la autenticación
):
    try:
        print("📩 Solicitud recibida en create_evaluation()")
        print("📤 Payload recibido:", payload)

        # --- Extraer campos ---
        user_id = payload.get("user_id")
        test_type = payload.get("test_type")
        score = payload.get("score")
        observaciones = payload.get("observaciones")
        respuestas = payload.get("respuestas")

        if not user_id or not test_type:
            raise HTTPException(status_code=400, detail="Faltan campos requeridos")

        # --- Serializar respuestas ---
        if respuestas:
            try:
                respuestas_serializadas = json.dumps(respuestas, ensure_ascii=False)
            except Exception:
                respuestas_serializadas = str(respuestas)
        else:
            respuestas_serializadas = json.dumps({"preguntas": []})

        # ✅ Determinar si la evaluación es del paciente o del profesional
        evaluador_id = (
            None if current_user.get("user_type") == "paciente" else current_user.get("id")
        )

        print("💾 Insertando en BD con los siguientes datos:")
        print({
            "user_id": user_id,
            "test_type": test_type,
            "score": score,
            "respuestas_json": respuestas_serializadas,
            "observaciones": observaciones,
            "evaluador_id": evaluador_id
        })

        # --- Crear registro ---
        evaluacion = Evaluation(
            user_id=user_id,
            evaluador_id=evaluador_id,
            test_type=test_type,
            score=score,
            respuestas_json=respuestas_serializadas,
            observaciones=observaciones,
            fecha_aplicacion=datetime.utcnow()
        )

        db.add(evaluacion)
        db.commit()
        db.refresh(evaluacion)

        print(f"✅ Evaluación guardada con ID {evaluacion.id}")
        print(f"🧾 Respuestas almacenadas: {respuestas_serializadas}")

        return {"status": "ok", "evaluation_id": evaluacion.id}

    except Exception as e:
        print("❌ Error en create_evaluation:", e)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================
# 🧩 Obtener todas las evaluaciones de un paciente
# ============================================================
@router.get("/{user_id}")
def get_evaluations(user_id: int, db: Session = Depends(get_db)):
    evaluations = db.query(Evaluation).filter(Evaluation.user_id == user_id).all()
    result = []
    for e in evaluations:
        result.append({
            "id": e.id,
            "user_id": e.user_id,
            "evaluador_id": e.evaluador_id,
            "test_type": e.test_type,
            "score": e.score,
            "observaciones": e.observaciones,
            "fecha_aplicacion": e.fecha_aplicacion.isoformat(),
            # 👇 Parte esencial
            "respuestas_json": json.loads(e.respuestas_json) if e.respuestas_json else None,
        })
    return result



# ============================================================
# 🧩 Comparar evaluación paciente vs profesional
# ============================================================
@router.get("/compare/{user_id}")
def compare_evaluations(user_id: int, db: Session = Depends(get_db)):
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
            "respuestas": json.loads(e.respuestas_json) if e.respuestas_json else None,
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
