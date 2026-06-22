from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime, date, time, timedelta

from db import get_db
from models import User, Profile, PatientMedication, PatientAppointment
from auth import get_current_user

router = APIRouter(prefix="/api/calendar", tags=["Calendario del paciente"])


def _validar_paciente(db: Session, current_user: dict):
    user = db.query(User).filter(User.id == current_user["id"]).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if user.user_type != "paciente":
        raise HTTPException(status_code=403, detail="Este módulo es para pacientes")
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    return user, profile


def _parse_date(value: str | None):
    if not value:
        return date.today()
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Formato de fecha inválido. Usa YYYY-MM-DD",
        )


def _parse_time(value: str):
    try:
        h, m = value.split(":")[:2]
        return time(int(h), int(m))
    except Exception:
        return None


def _medication_events_for_day(med: PatientMedication, selected_date: date):
    if not med.frecuencia_horas or med.frecuencia_horas <= 0:
        return []

    start_time = _parse_time(med.hora_inicio)
    if start_time is None:
        return []

    try:
        fecha_inicio = (
            datetime.strptime(med.fecha_inicio, "%Y-%m-%d").date()
            if med.fecha_inicio
            else selected_date
        )
    except Exception:
        fecha_inicio = selected_date

    try:
        fecha_fin = (
            datetime.strptime(med.fecha_fin, "%Y-%m-%d").date()
            if med.fecha_fin
            else selected_date
        )
    except Exception:
        fecha_fin = selected_date

    if selected_date < fecha_inicio or selected_date > fecha_fin:
        return []

    inicio_tratamiento = datetime.combine(fecha_inicio, start_time)
    fin_tratamiento = datetime.combine(fecha_fin, time(23, 59))

    inicio_dia = datetime.combine(selected_date, time(0, 0))
    fin_dia = datetime.combine(selected_date, time(23, 59))

    events = []
    current = inicio_tratamiento

    while current <= fin_tratamiento:
        if inicio_dia <= current <= fin_dia:
            events.append({
                "tipo": "medicamento",
                "origen": "medicamento",
                "id": med.id,
                "hora": current.strftime("%H:%M"),
                "titulo": med.nombre,
                "descripcion": f"{med.cantidad} {med.unidad} · {med.frecuencia_texto}",
            })

        current += timedelta(hours=med.frecuencia_horas)

    return events


def _nombre_profesional(db: Session, profesional_id: int | None):
    if not profesional_id:
        return "Profesional de salud"

    user = db.query(User).filter(User.id == profesional_id).first()
    profile = db.query(Profile).filter(Profile.user_id == profesional_id).first()

    if profile:
        nombre = f"{profile.nombre or ''} {profile.apellido or ''}".strip()
        if nombre:
            return nombre

    return user.full_name if user and user.full_name else "Profesional de salud"


@router.get("")
def calendario_dia(
    date_value: str | None = Query(None, alias="date"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user, profile = _validar_paciente(db, current_user)
    selected_date = _parse_date(date_value)
    selected_date_str = selected_date.isoformat()

    eventos = []

    medicamentos = (
        db.query(PatientMedication)
        .filter(
            PatientMedication.user_id == user.id,
            PatientMedication.activo == 1,
        )
        .all()
    )

    for med in medicamentos:
        eventos.extend(_medication_events_for_day(med, selected_date))

    citas = (
        db.query(PatientAppointment)
        .filter(
            PatientAppointment.paciente_id == user.id,
            PatientAppointment.fecha_cita == selected_date_str,
            PatientAppointment.estado == "programada",
        )
        .order_by(PatientAppointment.hora_cita.asc())
        .all()
    )

    for cita in citas:
        profesional_nombre = _nombre_profesional(db, cita.profesional_id)
        eventos.append({
            "tipo": "cita",
            "origen": "cita",
            "id": cita.id,
            "hora": cita.hora_cita,
            "titulo": f"Cita con {profesional_nombre}",
            "descripcion": f"{cita.motivo} · {cita.unidad_medica or (profile.unidad_medica if profile else '')}",
        })

    eventos.sort(key=lambda item: item.get("hora", "99:99"))

    return {
        "date": selected_date_str,
        "unidad_medica": profile.unidad_medica if profile else None,
        "items": eventos,
    }