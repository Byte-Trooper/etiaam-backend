from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import json

from db import get_db
from models import User, Profile, PatientAppointment
from schemas import (
    PatientAppointmentCreate,
    PatientAppointmentUpdate,
    PatientAppointmentOut,
    ProfesionalUnidadOut,
)
from auth import get_current_user

router = APIRouter(prefix="/api/appointments", tags=["Citas del paciente"])


DEFAULT_RECORDATORIOS = {
    "3_dias": True,
    "1_dia": True,
    "4_horas": True,
    "1_hora": True,
}


def _get_user_and_profile(db: Session, user_id: int):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    profile = db.query(Profile).filter(Profile.user_id == user_id).first()
    return user, profile


def _validar_paciente_actual(db: Session, current_user: dict):
    user, profile = _get_user_and_profile(db, current_user["id"])

    if user.user_type != "paciente":
        raise HTTPException(status_code=403, detail="Este módulo es para pacientes")

    if not profile or not profile.unidad_medica:
        raise HTTPException(
            status_code=400,
            detail="Completa tu unidad médica en Mis datos personales antes de registrar citas.",
        )

    return user, profile


def _nombre_profesional(user: User, profile: Profile | None):
    if profile:
        nombre = f"{profile.nombre or ''} {profile.apellido or ''}".strip()
        if nombre:
            return nombre
    return user.full_name or "Profesional de salud"


def _validar_profesional_misma_unidad(db: Session, profesional_id: int, unidad_medica: str):
    profesional = (
        db.query(User)
        .filter(User.id == profesional_id, User.user_type == "profesional")
        .first()
    )

    if not profesional:
        raise HTTPException(status_code=404, detail="Profesional no encontrado")

    profile = db.query(Profile).filter(Profile.user_id == profesional_id).first()

    if not profile or profile.unidad_medica != unidad_medica:
        raise HTTPException(
            status_code=403,
            detail="El profesional seleccionado no pertenece a tu unidad médica.",
        )

    return profesional, profile


def _recordatorios_to_json(recordatorios):
    data = recordatorios if recordatorios is not None else DEFAULT_RECORDATORIOS
    return json.dumps(data)


def _appointment_to_out(cita: PatientAppointment, db: Session):
    profesional_nombre = None
    profesional_especialidad = None

    if cita.profesional_id:
        profesional = db.query(User).filter(User.id == cita.profesional_id).first()
        profile = db.query(Profile).filter(Profile.user_id == cita.profesional_id).first()
        if profesional:
            profesional_nombre = _nombre_profesional(profesional, profile)
        if profile:
            profesional_especialidad = profile.especialidad

    recordatorios = DEFAULT_RECORDATORIOS
    if cita.recordatorios_json:
        try:
            recordatorios = json.loads(cita.recordatorios_json)
        except Exception:
            recordatorios = DEFAULT_RECORDATORIOS

    return PatientAppointmentOut(
        id=cita.id,
        paciente_id=cita.paciente_id,
        profesional_id=cita.profesional_id,
        profesional_nombre=profesional_nombre,
        profesional_especialidad=profesional_especialidad,
        unidad_medica=cita.unidad_medica,
        fecha_cita=cita.fecha_cita,
        hora_cita=cita.hora_cita,
        motivo=cita.motivo,
        notas=cita.notas,
        recordatorios=recordatorios,
        estado=cita.estado,
        created_at=cita.created_at,
        updated_at=cita.updated_at,
    )


@router.get("/profesionales-mi-unidad", response_model=list[ProfesionalUnidadOut])
def profesionales_mi_unidad(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    _, paciente_profile = _validar_paciente_actual(db, current_user)

    resultados = (
        db.query(User, Profile)
        .join(Profile, Profile.user_id == User.id)
        .filter(
            User.user_type == "profesional",
            Profile.unidad_medica == paciente_profile.unidad_medica,
        )
        .order_by(Profile.nombre.asc(), Profile.apellido.asc())
        .all()
    )

    return [
        ProfesionalUnidadOut(
            id=user.id,
            nombre=_nombre_profesional(user, profile),
            especialidad=profile.especialidad,
            unidad_medica=profile.unidad_medica,
        )
        for user, profile in resultados
    ]


@router.get("", response_model=list[PatientAppointmentOut])
def listar_citas(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    paciente, _ = _validar_paciente_actual(db, current_user)

    citas = (
        db.query(PatientAppointment)
        .filter(PatientAppointment.paciente_id == paciente.id)
        .order_by(PatientAppointment.fecha_cita.asc(), PatientAppointment.hora_cita.asc())
        .all()
    )

    return [_appointment_to_out(cita, db) for cita in citas]


@router.post("", response_model=PatientAppointmentOut)
def crear_cita(
    payload: PatientAppointmentCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    paciente, paciente_profile = _validar_paciente_actual(db, current_user)
    _validar_profesional_misma_unidad(db, payload.profesional_id, paciente_profile.unidad_medica)

    cita = PatientAppointment(
        paciente_id=paciente.id,
        profesional_id=payload.profesional_id,
        unidad_medica=paciente_profile.unidad_medica,
        fecha_cita=payload.fecha_cita,
        hora_cita=payload.hora_cita,
        motivo=payload.motivo,
        notas=payload.notas or "",
        recordatorios_json=_recordatorios_to_json(payload.recordatorios),
        estado="programada",
    )

    db.add(cita)
    db.commit()
    db.refresh(cita)

    return _appointment_to_out(cita, db)


@router.put("/{appointment_id}", response_model=PatientAppointmentOut)
def actualizar_cita(
    appointment_id: int,
    payload: PatientAppointmentUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    paciente, paciente_profile = _validar_paciente_actual(db, current_user)

    cita = (
        db.query(PatientAppointment)
        .filter(
            PatientAppointment.id == appointment_id,
            PatientAppointment.paciente_id == paciente.id,
        )
        .first()
    )

    if not cita:
        raise HTTPException(status_code=404, detail="Cita no encontrada")

    data = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else payload.dict(exclude_unset=True)

    if "profesional_id" in data and data["profesional_id"] is not None:
        _validar_profesional_misma_unidad(db, data["profesional_id"], paciente_profile.unidad_medica)

    if "recordatorios" in data:
        cita.recordatorios_json = _recordatorios_to_json(data.pop("recordatorios"))

    for key, value in data.items():
        setattr(cita, key, value)

    db.commit()
    db.refresh(cita)

    return _appointment_to_out(cita, db)


@router.delete("/{appointment_id}")
def cancelar_cita(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    paciente, _ = _validar_paciente_actual(db, current_user)

    cita = (
        db.query(PatientAppointment)
        .filter(
            PatientAppointment.id == appointment_id,
            PatientAppointment.paciente_id == paciente.id,
        )
        .first()
    )

    if not cita:
        raise HTTPException(status_code=404, detail="Cita no encontrada")

    cita.estado = "cancelada"
    db.commit()

    return {"ok": True, "message": "Cita cancelada"}
