# routes_evaluations.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db import get_db
from models import Evaluation, CompetenciasProfesionales, User, Profile
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
# RESUMEN GENERAL DEL PACIENTE
# Devuelve la última evaluación disponible por instrumento.
# ============================================================

TEST_RESUMEN_CONFIG = {
    "automanejo_paciente": {
        "key": "automanejo",
        "titulo": "Automanejo",
        "score_maximo": 96,
        "mayor_mejor": True,
    },
    "autoeficacia_enfermedad_cronica": {
        "key": "autoeficacia",
        "titulo": "Autoeficacia",
        "score_maximo": 60,
        "mayor_mejor": True,
    },
    "comunicacion_medico": {
        "key": "comunicacion_medico",
        "titulo": "Comunicación con el médico",
        "score_maximo": 15,
        "mayor_mejor": True,
        "usar_score_respuestas": "score_comunicacion",
    },
    "medicamentos_indicaciones": {
        "key": "medicamentos",
        "titulo": "Medicamentos / Indicaciones",
        "score_maximo": 4,
        "mayor_mejor": True,
    },
    "datos_familiares": {
        "key": "apoyo_familiar",
        "titulo": "Apoyo familiar",
        "score_maximo": 28,
        "mayor_mejor": True,
    },
    "afectos_emociones": {
        "key": "afectos_emociones",
        "titulo": "Afectos / Emociones",
        "score_maximo": 24,
        "mayor_mejor": False,
    },
    "actividad_fisica": {
        "key": "actividad_fisica",
        "titulo": "Actividad física",
        "score_maximo": 24,
        "mayor_mejor": True,
    },
}


def _nivel_resumen(score: int, score_maximo: int, mayor_mejor: bool):
    if score_maximo <= 0:
        return {"nivel": "Sin interpretación", "semaforo": "gris"}

    porcentaje = score / score_maximo

    if mayor_mejor:
        if porcentaje >= 0.70:
            return {"nivel": "Fortaleza", "semaforo": "verde"}
        if porcentaje >= 0.40:
            return {"nivel": "Seguimiento", "semaforo": "amarillo"}
        return {"nivel": "Necesidad de intervención", "semaforo": "rojo"}

    # Para afectos/emociones, menor puntaje es mejor.
    if porcentaje <= 0.33:
        return {"nivel": "Fortaleza", "semaforo": "verde"}
    if porcentaje <= 0.66:
        return {"nivel": "Seguimiento", "semaforo": "amarillo"}
    return {"nivel": "Necesidad de intervención", "semaforo": "rojo"}


def _item_resumen(e, config):
    data = _evaluation_to_dict(e)
    respuestas = data.get("respuestas") or {}

    score = data.get("score") or 0
    campo_score = config.get("usar_score_respuestas")

    if campo_score and isinstance(respuestas, dict) and respuestas.get(campo_score) is not None:
        try:
            score = int(respuestas.get(campo_score))
        except Exception:
            score = data.get("score") or 0

    score_maximo = int(config.get("score_maximo", 0))
    mayor_mejor = bool(config.get("mayor_mejor", True))
    nivel = _nivel_resumen(score, score_maximo, mayor_mejor)

    return {
        "key": config.get("key"),
        "titulo": config.get("titulo"),
        "test_type": data.get("test_type"),
        "score": score,
        "score_maximo": score_maximo,
        "mayor_mejor": mayor_mejor,
        "nivel": nivel["nivel"],
        "semaforo": nivel["semaforo"],
        "fecha": data.get("fecha"),
        "fecha_aplicacion": data.get("fecha_aplicacion"),
        "respuestas": respuestas,
        "evaluacion_id": data.get("id"),
        "score_original": data.get("score"),
    }


@router.get("/resumen-general/{user_id}")
def resumen_general_paciente(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    # El paciente puede ver su propio resumen.
    # El profesional puede ver el resumen de sus pacientes.
    if current_user["id"] != user_id and current_user.get("user_type") != "profesional":
        raise HTTPException(status_code=403, detail="Acceso restringido")


    user = db.query(User).filter(User.id == user_id).first()
    profile = db.query(Profile).filter(Profile.user_id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    nombre_perfil = ""
    if profile:
        nombre_perfil = f"{profile.nombre or ''} {profile.apellido or ''}".strip()

    paciente_info = {
        "id": user.id,
        "full_name": nombre_perfil or user.full_name or "Paciente",
        "nombre": profile.nombre if profile else None,
        "apellido": profile.apellido if profile else None,
        "nss": profile.nss if profile else None,
        "email": user.email,
    }

    items = []

    for test_type, config in TEST_RESUMEN_CONFIG.items():
        evaluacion = (
            db.query(Evaluation)
            .filter(
                Evaluation.user_id == user_id,
                Evaluation.test_type == test_type,
            )
            .order_by(Evaluation.fecha_aplicacion.desc())
            .first()
        )

        if evaluacion:
            items.append(_item_resumen(evaluacion, config))
        else:
            items.append({
                "key": config.get("key"),
                "titulo": config.get("titulo"),
                "test_type": test_type,
                "score": None,
                "score_maximo": config.get("score_maximo"),
                "mayor_mejor": config.get("mayor_mejor", True),
                "nivel": "Sin registro",
                "semaforo": "gris",
                "fecha": None,
                "fecha_aplicacion": None,
                "respuestas": None,
                "evaluacion_id": None,
            })

    # Última evaluación profesional de automanejo como referencia clínica.
    profesional = (
        db.query(Evaluation)
        .filter(
            Evaluation.user_id == user_id,
            Evaluation.test_type == "automanejo_prof",
        )
        .order_by(Evaluation.fecha_aplicacion.desc())
        .first()
    )

    automanejo_prof = None
    if profesional:
        automanejo_prof = _evaluation_to_dict(profesional)

    contestados = [i for i in items if i.get("score") is not None]
    fortalezas = len([i for i in contestados if i.get("semaforo") == "verde"])
    seguimiento = len([i for i in contestados if i.get("semaforo") == "amarillo"])
    intervencion = len([i for i in contestados if i.get("semaforo") == "rojo"])

    fechas = [i.get("fecha") for i in contestados if i.get("fecha")]
    ultima_fecha = max(fechas) if fechas else None

    return {
        "user_id": user_id,
        "paciente": paciente_info,
        "total_instrumentos": len(items),
        "instrumentos_contestados": len(contestados),
        "ultima_fecha": ultima_fecha,
        "fortalezas": fortalezas,
        "seguimiento": seguimiento,
        "intervencion": intervencion,
        "automanejo_profesional": automanejo_prof,
        "items": items,
    }



# ============================================================
# HISTORIAL DE EVALUACIONES POR INSTRUMENTO
# Devuelve todas las evaluaciones de un paciente para un test_type.
# IMPORTANTE: esta ruta debe ir antes de /{user_id} para evitar conflicto.
# ============================================================

@router.get("/history/{user_id}/{test_type}")
def historial_evaluaciones_por_instrumento(
    user_id: int,
    test_type: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    # El paciente puede ver su propio historial.
    # El profesional puede ver el historial de sus pacientes.
    if current_user["id"] != user_id and current_user.get("user_type") != "profesional":
        raise HTTPException(status_code=403, detail="Acceso restringido")

    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    config = TEST_RESUMEN_CONFIG.get(test_type)

    evaluaciones = (
        db.query(Evaluation)
        .filter(
            Evaluation.user_id == user_id,
            Evaluation.test_type == test_type,
        )
        .order_by(Evaluation.fecha_aplicacion.asc())
        .all()
    )

    items = []

    for e in evaluaciones:
        data = _evaluation_to_dict(e)
        respuestas = data.get("respuestas") or {}
        score = data.get("score") or 0

        # Caso especial: comunicación médico usa solo las preguntas 1 a 3.
        if config and config.get("usar_score_respuestas"):
            campo_score = config.get("usar_score_respuestas")
            if isinstance(respuestas, dict) and respuestas.get(campo_score) is not None:
                try:
                    score = int(respuestas.get(campo_score))
                except Exception:
                    score = data.get("score") or 0

        score_maximo = int(config.get("score_maximo", 0)) if config else None
        mayor_mejor = bool(config.get("mayor_mejor", True)) if config else True
        nivel = _nivel_resumen(score, score_maximo, mayor_mejor) if score_maximo else {
            "nivel": "Sin interpretación",
            "semaforo": "gris",
        }

        items.append({
            "id": data.get("id"),
            "user_id": data.get("user_id"),
            "evaluador_id": data.get("evaluador_id"),
            "test_type": data.get("test_type"),
            "titulo": config.get("titulo") if config else test_type,
            "score": score,
            "score_maximo": score_maximo,
            "mayor_mejor": mayor_mejor,
            "nivel": nivel["nivel"],
            "semaforo": nivel["semaforo"],
            "fecha": data.get("fecha"),
            "fecha_aplicacion": data.get("fecha_aplicacion"),
            "respuestas": respuestas,
            "observaciones": data.get("observaciones"),
        })

    return {
        "user_id": user_id,
        "test_type": test_type,
        "titulo": config.get("titulo") if config else test_type,
        "score_maximo": int(config.get("score_maximo", 0)) if config else None,
        "mayor_mejor": bool(config.get("mayor_mejor", True)) if config else True,
        "total": len(items),
        "items": items,
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
