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
            merece=obj.merece
        )
        db.add(nuevo_obj)

    db.commit()

    return {"message": "Plan creado correctamente"}
