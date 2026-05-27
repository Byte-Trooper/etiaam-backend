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
# CONFIGURACIÓN
# ============================================================

AUTOMANEJO_TEST_TYPES = {
    "automanejo_paciente",
    "automanejo_prof",
}


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def _parse_json(value):
    """
    Convierte respuestas_json a diccionario.
    Puede venir como dict, string JSON o None.
    """
    if value is None:
        return None

    if isinstance(value, dict):
        return value

    if isinstance(value, str):
        try:
            return json.loads(value)
        except Exception:
            return None

    return None


def _extraer_preguntas(respuestas):
    """
    Extrae la lista de respuestas del instrumento:
    {"preguntas": [3, 7, 4, ...]}
    """
    if not isinstance(respuestas, dict):
        return []

    preguntas = respuestas.get("preguntas")

    if not isinstance(preguntas, list):
        return []

    valores = []

    for item in preguntas:
        try:
            valores.append(int(float(item)))
        except Exception:
            pass

    return valores


def _calcular_score_automanejo(test_type, respuestas, score_fallback=None):
    """
    Calcula el score real del instrumento de automanejo.
    Antes se usaba promedio; ahora se usa suma total de respuestas.
    """
    preguntas = _extraer_preguntas(respuestas)

    if test_type in AUTOMANEJO_TEST_TYPES and preguntas:
        return int(sum(preguntas))

    if score_fallback is not None:
        try:
            return int(score_fallback)
        except Exception:
            return 0

    return 0


def _obtener_respuestas_desde_payload(payload: dict):
    """
    Acepta diferentes nombres por compatibilidad con Flutter:
    - respuestas_json
    - respuestas
    """
    respuestas = payload.get("respuestas_json")

    if respuestas is None:
        respuestas = payload.get("respuestas")

    parsed = _parse_json(respuestas)

    if parsed is None and isinstance(respuestas, dict):
        parsed = respuestas

    return parsed


def _evaluation_to_dict(e):
    """
    Convierte una evaluación a JSON de respuesta.
    Importante: recalcula score desde respuestas_json para que también
    evaluaciones antiguas se muestren con score total.
    """
    if not e:
        return None

    parsed = _parse_json(e.respuestas_json)

    score_calculado = _calcular_score_automanejo(
        e.test_type,
        parsed,
        score_fallback=e.score,
    )

    return {
        "id": e.id,
        "user_id": e.user_id,
        "evaluador_id": e.evaluador_id,
        "test_type": e.test_type,
        "score": score_calculado,
        "observaciones": e.observaciones,
        "fecha": e.fecha_aplicacion.isoformat() if e.fecha_aplicacion else None,
        "fecha_aplicacion": e.fecha_aplicacion.isoformat() if e.fecha_aplicacion else None,
        "respuestas": parsed,
    }


# ============================================================
# GUARDAR EVALUACIÓN GENERAL
# AUTOMANEJO PACIENTE / PROFESIONAL
# ============================================================

@router.post("")
def create_evaluation(payload: dict, db: Session = Depends(get_db)):

    if "user_id" not in payload or "test_type" not in payload:
        raise HTTPException(
            status_code=400,
            detail="Faltan campos obligatorios"
        )

    test_type = payload.get("test_type")
    respuestas = _obtener_respuestas_desde_payload(payload)

    # Nuevo cálculo correcto:
    # score = suma total de las respuestas del instrumento.
    score_calculado = _calcular_score_automanejo(
        test_type,
        respuestas,
        score_fallback=payload.get("score"),
    )

    new_eval = Evaluation(
        user_id=payload.get("user_id"),
        evaluador_id=payload.get("evaluador_id"),
        test_type=test_type,
        score=score_calculado,
        observaciones=payload.get("observaciones", ""),
        respuestas_json=json.dumps(respuestas),
        fecha_aplicacion=datetime.utcnow(),
    )

    db.add(new_eval)
    db.commit()
    db.refresh(new_eval)

    return _evaluation_to_dict(new_eval)


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

    return [_evaluation_to_dict(e) for e in evaluations]


# ============================================================
# COMPARACIÓN PACIENTE vs PROFESIONAL
# ============================================================

@router.get("/compare/{user_id}")
def compare_last_evaluations(user_id: int, db: Session = Depends(get_db)):

    paciente = (
        db.query(Evaluation)
        .filter(
            Evaluation.user_id == user_id,
            Evaluation.test_type == "automanejo_paciente"
        )
        .order_by(Evaluation.fecha_aplicacion.desc())
        .first()
    )

    profesional = (
        db.query(Evaluation)
        .filter(
            Evaluation.user_id == user_id,
            Evaluation.test_type == "automanejo_prof"
        )
        .order_by(Evaluation.fecha_aplicacion.desc())
        .first()
    )

    return {
        "paciente": _evaluation_to_dict(paciente),
        "profesional": _evaluation_to_dict(profesional),
    }


# ============================================================
# GUARDAR TEST DE COMPETENCIAS PROFESIONALES
# ============================================================

@router.post("/competencias", response_model=CompetenciasOut)
def guardar_competencias(
    data: CompetenciasIn,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    registro = CompetenciasProfesionales(
        user_id=data.user_id,
        respuestas=json.dumps(data.respuestas),
        f1_promedio=data.f1_promedio,
        f2_promedio=data.f2_promedio,
        f3_promedio=data.f3_promedio,
        f4_promedio=data.f4_promedio,
        puntaje_total=data.puntaje_total,
    )

    db.add(registro)
    db.commit()
    db.refresh(registro)

    return CompetenciasOut(
        id=registro.id,
        user_id=registro.user_id,
        respuestas=json.loads(registro.respuestas),
        f1_promedio=registro.f1_promedio,
        f2_promedio=registro.f2_promedio,
        f3_promedio=registro.f3_promedio,
        f4_promedio=registro.f4_promedio,
        puntaje_total=registro.puntaje_total,
        fecha_aplicacion=registro.fecha_aplicacion.isoformat()
        if registro.fecha_aplicacion
        else None,
    )


# ============================================================
# ÚLTIMA EVALUACIÓN DE AUTOMANEJO DEL PACIENTE
# ============================================================

@router.get("/paciente/ultimo/{user_id}")
def ultimo_automanejo_paciente(user_id: int, db: Session = Depends(get_db)):

    eval = (
        db.query(Evaluation)
        .filter(
            Evaluation.user_id == user_id,
            Evaluation.test_type == "automanejo_paciente",
        )
        .order_by(Evaluation.fecha_aplicacion.desc())
        .first()
    )

    if not eval:
        return {"ultimo": None}

    data = _evaluation_to_dict(eval)

    return {
        "ultimo": True,
        "score": data["score"],
        "fecha": data["fecha"],
        "respuestas": data["respuestas"],
    }

# ============================================================
# OBTENER ÚLTIMO TEST DE COMPETENCIAS DEL PROFESIONAL
# ============================================================
@router.get("/competencias/ultimo")
def obtener_ultimo_test_competencias(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    registro = (
        db.query(CompetenciasProfesionales)
        .filter(CompetenciasProfesionales.user_id == current_user["id"])
        .order_by(CompetenciasProfesionales.fecha_aplicacion.desc())
        .first()
    )

    if not registro:
        return {"ultimo": None}

    respuestas = None

    if registro.respuestas:
        try:
            respuestas = json.loads(registro.respuestas)
        except Exception:
            respuestas = None

    return {
        "ultimo": True,
        "id": registro.id,
        "user_id": registro.user_id,
        "respuestas": respuestas,
        "f1_promedio": registro.f1_promedio,
        "f2_promedio": registro.f2_promedio,
        "f3_promedio": registro.f3_promedio,
        "f4_promedio": registro.f4_promedio,
        "puntaje_total": registro.puntaje_total,
        "fecha_aplicacion": registro.fecha_aplicacion.isoformat()
        if registro.fecha_aplicacion
        else None,
    }
