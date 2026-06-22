
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from db import get_db
from models import PatientMedication, User
from schemas import (
    PatientMedicationCreate,
    PatientMedicationUpdate,
    PatientMedicationOut,
)
from auth import get_current_user

router = APIRouter(prefix="/api/medications", tags=["Medicamentos del paciente"])


FRECUENCIAS_PERMITIDAS = {
    "Cada 4 horas": 4,
    "Cada 6 horas": 6,
    "Cada 8 horas": 8,
    "Cada 12 horas": 12,
    "Cada 24 horas": 24,
    "Una vez al día": 24,
    "Dos veces al día": 12,
    "Tres veces al día": 8,
    "Solo cuando lo indique el médico": None,
}


def _validar_usuario_paciente(db: Session, user_id: int):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if user.user_type != "paciente":
        raise HTTPException(status_code=403, detail="Este módulo es para pacientes")
    return user


def _normalizar_frecuencia(frecuencia_texto: str, frecuencia_horas: int | None):
    if frecuencia_texto in FRECUENCIAS_PERMITIDAS:
        return FRECUENCIAS_PERMITIDAS[frecuencia_texto]
    return frecuencia_horas


@router.get("", response_model=list[PatientMedicationOut])
def listar_medicamentos(
    incluir_inactivos: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["id"]
    _validar_usuario_paciente(db, user_id)

    query = db.query(PatientMedication).filter(PatientMedication.user_id == user_id)

    if not incluir_inactivos:
        query = query.filter(PatientMedication.activo == 1)

    return query.order_by(PatientMedication.created_at.desc()).all()


@router.post("", response_model=PatientMedicationOut)
def crear_medicamento(
    payload: PatientMedicationCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["id"]
    _validar_usuario_paciente(db, user_id)

    frecuencia_horas = _normalizar_frecuencia(
        payload.frecuencia_texto,
        payload.frecuencia_horas,
    )

    medicamento = PatientMedication(
        user_id=user_id,
        nombre=payload.nombre.strip(),
        presentacion=payload.presentacion,
        cantidad=payload.cantidad,
        unidad=payload.unidad,
        frecuencia_texto=payload.frecuencia_texto,
        frecuencia_horas=frecuencia_horas,
        hora_inicio=payload.hora_inicio,
        fecha_inicio=payload.fecha_inicio,
        fecha_fin=payload.fecha_fin,
        duracion_texto=payload.duracion_texto,
        indicaciones=payload.indicaciones or "",
        activo=1,
    )

    db.add(medicamento)
    db.commit()
    db.refresh(medicamento)

    return medicamento


@router.put("/{medication_id}", response_model=PatientMedicationOut)
def actualizar_medicamento(
    medication_id: int,
    payload: PatientMedicationUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["id"]
    _validar_usuario_paciente(db, user_id)

    medicamento = (
        db.query(PatientMedication)
        .filter(
            PatientMedication.id == medication_id,
            PatientMedication.user_id == user_id,
        )
        .first()
    )

    if not medicamento:
        raise HTTPException(status_code=404, detail="Medicamento no encontrado")

    data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else payload.dict(exclude_unset=True)

    if "frecuencia_texto" in data:
        data["frecuencia_horas"] = _normalizar_frecuencia(
            data.get("frecuencia_texto"),
            data.get("frecuencia_horas"),
        )

    for key, value in data.items():
        setattr(medicamento, key, value)

    db.commit()
    db.refresh(medicamento)

    return medicamento


@router.delete("/{medication_id}")
def desactivar_medicamento(
    medication_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["id"]
    _validar_usuario_paciente(db, user_id)

    medicamento = (
        db.query(PatientMedication)
        .filter(
            PatientMedication.id == medication_id,
            PatientMedication.user_id == user_id,
        )
        .first()
    )

    if not medicamento:
        raise HTTPException(status_code=404, detail="Medicamento no encontrado")

    medicamento.activo = 0
    db.commit()

    return {"ok": True, "message": "Medicamento desactivado"}
