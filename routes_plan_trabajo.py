# routes_plan_trabajo.py

from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db import get_db
from models import PlanTrabajo, ObjetivoPlan
from schemas import PlanTrabajoCreate

router = APIRouter(prefix="/api/plan", tags=["Plan Trabajo"])


def _serializar_objetivo(obj: ObjetivoPlan):
    return {
        "id": obj.id,
        "descripcion": obj.descripcion,
        "actividad": obj.actividad,
        "recursos": obj.recursos,
        "seguimiento": obj.seguimiento,
        "fecha_revision": obj.fecha_revision,
        "cumplimiento": obj.cumplimiento or 0,
    }


def _serializar_plan(plan: PlanTrabajo):
    return {
        "id": plan.id,
        "paciente_id": plan.paciente_id,
        "profesional_id": plan.profesional_id,
        "fecha_creacion": plan.fecha_creacion,
        "objetivo_principal": plan.objetivo_principal,
        "plan_ejecucion": plan.plan_ejecucion,
        "recursos_necesarios": plan.recursos_necesarios,
        "emociones_asociadas": plan.emociones_asociadas,
        "estado": plan.estado,
        "objetivos": [_serializar_objetivo(obj) for obj in plan.objetivos],
    }


# ================================================================
# CREAR PLAN DE TRABAJO
# ================================================================
@router.post("/")
def crear_plan(data: PlanTrabajoCreate, db: Session = Depends(get_db)):
    """
    Crea un nuevo plan de trabajo.
    Al crear uno nuevo, se cierran automáticamente los planes activos anteriores
    del mismo paciente. Los objetivos se usan como acuerdos de consulta:
    meta, acción, fecha de revisión y cumplimiento.
    """

    planes_activos = (
        db.query(PlanTrabajo)
        .filter(
            PlanTrabajo.paciente_id == data.paciente_id,
            PlanTrabajo.estado == "activo",
        )
        .all()
    )

    for plan in planes_activos:
        plan.estado = "cerrado"

    nuevo_plan = PlanTrabajo(
        paciente_id=data.paciente_id,
        profesional_id=data.profesional_id,
        fecha_creacion=datetime.utcnow(),
        objetivo_principal=data.objetivo_principal,
        plan_ejecucion=data.plan_ejecucion,
        recursos_necesarios=data.recursos_necesarios,
        emociones_asociadas=data.emociones_asociadas,
        estado="activo",
    )

    db.add(nuevo_plan)
    db.commit()
    db.refresh(nuevo_plan)

    for obj in data.objetivos:
        nuevo_obj = ObjetivoPlan(
            plan_id=nuevo_plan.id,
            descripcion=obj.descripcion,
            actividad=obj.actividad,
            recursos=obj.recursos,
            seguimiento=obj.seguimiento,
            fecha_revision=obj.fecha_revision,
            cumplimiento=obj.cumplimiento,
        )
        db.add(nuevo_obj)

    db.commit()
    db.refresh(nuevo_plan)

    return {
        "message": "Plan creado correctamente",
        "plan_id": nuevo_plan.id,
    }


# ================================================================
# OBTENER ÚLTIMO PLAN
# ================================================================
@router.get("/ultimo/{paciente_id}")
def obtener_ultimo_plan(paciente_id: int, db: Session = Depends(get_db)):
    plan = (
        db.query(PlanTrabajo)
        .filter(PlanTrabajo.paciente_id == paciente_id)
        .order_by(PlanTrabajo.fecha_creacion.desc())
        .first()
    )

    if not plan:
        return {"message": "No hay plan disponible"}

    return _serializar_plan(plan)


# ================================================================
# OBTENER HISTORIAL DE PLANES
# ================================================================
@router.get("/historial/{paciente_id}")
def historial_planes(paciente_id: int, db: Session = Depends(get_db)):
    planes = (
        db.query(PlanTrabajo)
        .filter(PlanTrabajo.paciente_id == paciente_id)
        .order_by(PlanTrabajo.fecha_creacion.desc())
        .all()
    )

    return [_serializar_plan(plan) for plan in planes]


# ================================================================
# OBTENER DETALLE DE PLAN
# ================================================================
@router.get("/{plan_id}")
def obtener_plan_detalle(plan_id: int, db: Session = Depends(get_db)):
    plan = db.query(PlanTrabajo).filter(PlanTrabajo.id == plan_id).first()

    if not plan:
        return {"message": "Plan no encontrado"}

    return _serializar_plan(plan)


# ================================================================
# CERRAR PLAN DE TRABAJO
# ================================================================
@router.put("/cerrar/{plan_id}")
def cerrar_plan(plan_id: int, db: Session = Depends(get_db)):
    plan = db.query(PlanTrabajo).filter(PlanTrabajo.id == plan_id).first()

    if not plan:
        return {"message": "Plan no encontrado"}

    plan.estado = "cerrado"
    db.commit()

    return {"message": "Plan cerrado correctamente"}


# ================================================================
# ACTUALIZAR CUMPLIMIENTO DE UN ACUERDO
# ================================================================
@router.put("/objetivo/{objetivo_id}")
def actualizar_cumplimiento(
    objetivo_id: int,
    data: dict,
    db: Session = Depends(get_db),
):
    objetivo = db.query(ObjetivoPlan).filter(ObjetivoPlan.id == objetivo_id).first()

    if not objetivo:
        return {"message": "Objetivo no encontrado"}

    cumplimiento = int(data.get("cumplimiento", 0))
    objetivo.cumplimiento = max(0, min(100, cumplimiento))

    if "seguimiento" in data:
        objetivo.seguimiento = data.get("seguimiento")

    if "fecha_revision" in data:
        objetivo.fecha_revision = data.get("fecha_revision")

    db.commit()

    return {"message": "Cumplimiento actualizado"}


# ================================================================
# EVALUAR PLAN COMPLETO
# ================================================================
@router.put("/evaluar/{plan_id}")
def evaluar_plan(
    plan_id: int,
    data: dict,
    db: Session = Depends(get_db),
):
    plan = db.query(PlanTrabajo).filter(PlanTrabajo.id == plan_id).first()

    if not plan:
        return {"message": "Plan no encontrado"}

    objetivos_data = data.get("objetivos", [])

    for obj_data in objetivos_data:
        objetivo = (
            db.query(ObjetivoPlan)
            .filter(
                ObjetivoPlan.id == obj_data.get("id"),
                ObjetivoPlan.plan_id == plan_id,
            )
            .first()
        )

        if objetivo:
            cumplimiento = int(obj_data.get("cumplimiento", 0))
            objetivo.cumplimiento = max(0, min(100, cumplimiento))

            if "seguimiento" in obj_data:
                objetivo.seguimiento = obj_data.get("seguimiento")

            if "fecha_revision" in obj_data:
                objetivo.fecha_revision = obj_data.get("fecha_revision")

    db.commit()

    return {"message": "Evaluación guardada correctamente"}
