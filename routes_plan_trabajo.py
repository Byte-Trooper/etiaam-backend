# routes_plan_trabajo.py

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from db import get_db
from models import PlanTrabajo, ObjetivoPlan
from schemas import PlanTrabajoCreate
from datetime import datetime

router = APIRouter(prefix="/api/plan", tags=["Plan Trabajo"])

@router.post("/")
def crear_plan(data: PlanTrabajoCreate, db: Session = Depends(get_db)):
    # Cerrar planes activos anteriores
    planes_activos = db.query(PlanTrabajo).filter(
        PlanTrabajo.paciente_id == data.paciente_id,
        PlanTrabajo.estado == "activo"
    ).all()

    for p in planes_activos:
        p.estado = "cerrado"

    db.commit()

    nuevo_plan = PlanTrabajo(
        paciente_id=data.paciente_id,
        profesional_id=data.profesional_id,
        fecha_creacion=datetime.utcnow(),
        objetivo_principal=data.objetivo_principal,
        plan_ejecucion=data.plan_ejecucion,
        recursos_necesarios=data.recursos_necesarios,
        emociones_asociadas=data.emociones_asociadas,
        estado="activo"
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
            cronograma=obj.cronograma,
            fecha_seguimiento=obj.fecha_seguimiento,
            importante=obj.importante,
            posible=obj.posible,
            claro=obj.claro,
            capacidad=obj.capacidad,
            merece=obj.merece,
            seguimiento=obj.seguimiento,
            cumplimiento=obj.cumplimiento
        )
        db.add(nuevo_obj)

    db.commit()

    return {"message": "Plan creado correctamente"}


# ================================================================
# OBTENER ULTIMO PLAN
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

    return plan


# ================================================================
# OBTENER HISTORIAL
# ================================================================
@router.get("/historial/{paciente_id}")
def historial_planes(paciente_id: int, db: Session = Depends(get_db)):
    planes = (
        db.query(PlanTrabajo)
        .filter(PlanTrabajo.paciente_id == paciente_id)
        .order_by(PlanTrabajo.fecha_creacion.desc())
        .all()
    )

    return planes


# ================================================================
# OBTENER OBJETIVOS
# ================================================================
@router.get("/{plan_id}")
def obtener_plan_detalle(plan_id: int, db: Session = Depends(get_db)):
    plan = (
        db.query(PlanTrabajo)
        .filter(PlanTrabajo.id == plan_id)
        .first()
    )

    if not plan:
        return {"message": "Plan no encontrado"}

    return plan

# ================================================================
# CERRAR PLAN DE TRABAJO
# ================================================================
@router.put("/cerrar/{plan_id}")
def cerrar_plan(plan_id: int, db: Session = Depends(get_db)):

    plan = db.query(PlanTrabajo).filter(
        PlanTrabajo.id == plan_id
    ).first()

    if not plan:
        return {"message": "Plan no encontrado"}

    plan.estado = "cerrado"
    db.commit()

    return {"message": "Plan cerrado correctamente"}
