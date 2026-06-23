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
        raise HTTPException(status_code=400, detail="Formato de fecha inválido. Usa YYYY-MM-DD")


def _parse_medication_date(value: str | None):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except Exception:
        return None


def _parse_time(value: str):
    try:
        h, m = value.split(":")[:2]
        return time(int(h), int(m))
    except Exception:
        return None


def _medication_events_for_day(med: PatientMedication, selected_date: date):
    """
    Genera las tomas reales de un medicamento para un día seleccionado.

    Reglas:
    - Respeta fecha_inicio y fecha_fin.
    - Si fecha_fin existe, no muestra el medicamento después de esa fecha.
    - Calcula la secuencia real desde fecha_inicio + hora_inicio.
      Ejemplo: 21 junio 20:00 cada 8 horas -> 22 junio 04:00, 12:00, 20:00.
    - Si fecha_fin es NULL, se considera uso continuo desde fecha_inicio.
    """
    if not med.frecuencia_horas or med.frecuencia_horas <= 0:
        return []

    start_time = _parse_time(med.hora_inicio)
    if start_time is None:
        return []

    start_date = _parse_medication_date(med.fecha_inicio)

    # Compatibilidad con registros antiguos: si no tienen fecha_inicio,
    # se usa created_at como inicio aproximado. Si tampoco existe, no se muestra.
    if start_date is None:
        if getattr(med, "created_at", None):
            start_date = med.created_at.date()
        else:
            return []

    end_date = _parse_medication_date(med.fecha_fin)

    # Fuera del periodo de tratamiento.
    if selected_date < start_date:
        return []

    if end_date is not None and selected_date > end_date:
        return []

    start_dt = datetime.combine(start_date, start_time)
    day_start = datetime.combine(selected_date, time(0, 0))
    day_end = datetime.combine(selected_date, time(23, 59, 59))

    if end_date is not None:
        treatment_end = datetime.combine(end_date, time(23, 59, 59))
    else:
        treatment_end = day_end

    window_start = max(day_start, start_dt)
    window_end = min(day_end, treatment_end)

    if window_start > window_end:
        return []

    interval = timedelta(hours=med.frecuencia_horas)

    # Avanza desde el inicio real del tratamiento hasta la primera toma
    # que cae dentro del día seleccionado.
    current = start_dt
    if current < window_start:
        elapsed_seconds = (window_start - current).total_seconds()
        interval_seconds = interval.total_seconds()
        steps = int(elapsed_seconds // interval_seconds)
        current = current + timedelta(seconds=steps * interval_seconds)
        if current < window_start:
            current += interval

    events = []
    while current <= window_end:
        events.append({
            "tipo": "medicamento",
            "origen": "medicamento",
            "id": med.id,
            "hora": current.strftime("%H:%M"),
            "titulo": med.nombre,
            "descripcion": f"{med.cantidad} {med.unidad} · {med.frecuencia_texto}",
        })
        current += interval

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


@router.get("/profesional")
def calendario_profesional(
    date_value: str | None = Query(None, alias="date"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    profesional = db.query(User).filter(User.id == current_user["id"]).first()

    if not profesional:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if profesional.user_type != "profesional":
        raise HTTPException(status_code=403, detail="Este módulo es para profesionales")

    selected_date = _parse_date(date_value)
    selected_date_str = selected_date.isoformat()

    citas = (
        db.query(PatientAppointment)
        .filter(
            PatientAppointment.profesional_id == profesional.id,
            PatientAppointment.fecha_cita == selected_date_str,
            PatientAppointment.estado == "programada",
        )
        .order_by(PatientAppointment.hora_cita.asc())
        .all()
    )

    eventos = []

    for cita in citas:
        paciente = db.query(Profile).filter(Profile.user_id == cita.paciente_id).first()

        if paciente:
            nombre_paciente = f"{paciente.nombre or ''} {paciente.apellido or ''}".strip()
        else:
            nombre_paciente = "Paciente"

        eventos.append({
            "tipo": "cita",
            "id": cita.id,
            "hora": cita.hora_cita,
            "titulo": nombre_paciente,
            "descripcion": f"{cita.motivo} · {cita.unidad_medica or ''}",
        })

    return {
        "date": selected_date_str,
        "items": eventos,
    }
