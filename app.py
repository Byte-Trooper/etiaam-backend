# app.py
import random
from datetime import datetime, timedelta
import traceback

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError

from db import Base, engine, get_db
from models import User, Consent, PasswordResetCode
from schemas import (
    RegisterIn,
    LoginIn,
    TokenOut,
    ForgotPasswordIn,
    ResetPasswordIn,
    MessageOut,
)
from auth import hash_password, verify_password, create_access_token, sha256_hex
from email_service import send_password_reset_email
from routes_profile import router as profile_router
from routes_evaluations import router as evaluations_router
from routes_plan_trabajo import router as plan_router


app = FastAPI(title="ETIAAM API", version="1.0.0")


@app.on_event("startup")
def startup():
    try:
        Base.metadata.create_all(bind=engine)
        print("Base de datos conectada correctamente")
    except OperationalError as e:
        print("Error conectando a la base de datos:", e)


# CORS abierto para desarrollo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Cargar routers
app.include_router(profile_router)
app.include_router(evaluations_router)
app.include_router(plan_router)

print("Routers cargados correctamente: /api/profile, /api/evaluations y /api/plan activos")


# ============================================================
# Endpoints principales
# ============================================================

@app.get("/health")
def health():
    return {"ok": True}


@app.get("/consent/latest")
def latest_consent():
    text = (
        "CONSENTIMIENTO INFORMADO\n"
        "Título del proyecto: ECOSISTEMA TECNOLÓGICO CON INTELIGENCIA ARTIFICIAL PARA EL AUTOMANEJO (ETIAAM)\n"
        "\nEstimado(a) Usuario:\n"
        "Los investigadores de la Facultad de Enfermería Tampico y de la Facultad de Ingeniería de la Universidad Autónoma de Tamaulipas, México, me han informado que están dirigiendo el proyecto de investigación ETIAAM, cuyo objetivo es desarrollar un ecosistema médico-tecnológico integral basado en técnicas de inteligencia artificial y ciencia de datos para el apoyo del automanejo en enfermedades crónicas no transmisibles y la optimización de la atención en salud.\n"

        "\nMi participación consistirá en responder un cuestionario electrónico a través de una aplicación (App) instalada en mi teléfono, mediante la cual podré contestar las preguntas y observar el seguimiento de mi condición crónica. Esta información será compartida con los profesionales de salud responsables de mi atención.\n"
        "Los datos obtenidos serán utilizados exclusivamente con fines científicos por el equipo de investigación del proyecto, no estarán disponibles para otros propósitos y se conservarán durante la vigencia del proyecto y un año posterior a su terminación. Seré identificado(a) mediante un número y no por mi nombre. Los resultados se publicarán con fines académicos sin revelar mi identidad.\n"

        "\nEsta investigación se considera de riesgo mínimo. \nSi durante el cuestionario alguna pregunta me causa molestia o incomodidad, puedo negarme a responder. \nMi participación es completamente voluntaria y puedo retirarme en cualquier momento sin que esto afecte mi atención médica. \nNo recibiré compensación económica por mi participación.\n"

        "\nContacto:"
        "\n• Dra. María Isabel de Córdova — decordova.maria.isabel@gmail.com"
        "\n• Dr. Pedro Córdoba — pcordoba@docentes.uat.edu.mx"
        "\nTeléfonos: +51 980973062 / +52 833 1551764\n"

        "\nSi tengo dudas sobre mis derechos como participante en la investigación, puedo contactar al Dr. Carlos Eduardo Pretel Vergel (Centro de Salud donde me atiendo) o al Dr. José Alfredo Álvarez (Jefatura de Enseñanza, Clínica ISSSTE).\n"
    )

    return {
        "version": "v2.0",
        "text": text,
    }


# ============================================================
# REGISTRO
# ============================================================
@app.post("/register", response_model=TokenOut)
def register(payload: RegisterIn, req: Request, db: Session = Depends(get_db)):
    if payload.user_type not in ("paciente", "profesional"):
        raise HTTPException(
            status_code=400,
            detail="user_type inválido",
        )

    # Validar correo duplicado
    existing_email = db.query(User).filter(User.email == payload.email).first()
    if existing_email:
        raise HTTPException(
            status_code=409,
            detail="Email ya registrado",
        )

    # Validar teléfono duplicado
    existing_phone = (
        db.query(User)
        .filter(User.phone_number == payload.phone_number)
        .first()
    )

    if existing_phone:
        raise HTTPException(
            status_code=409,
            detail="Número celular ya registrado",
        )

    # Validación de seguridad adicional:
    # el teléfono completo debe coincidir con lada + número nacional
    expected_phone_number = f"{payload.country_code}{payload.phone_national}"

    if payload.phone_number != expected_phone_number:
        raise HTTPException(
            status_code=400,
            detail="El número celular completo no coincide con la lada y el número nacional",
        )

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        user_type=payload.user_type,

        # Campos para login con celular
        country_code=payload.country_code,
        phone_national=payload.phone_national,
        phone_number=payload.phone_number,
    )

    db.add(user)
    db.flush()

    consent = Consent(
        user_id=user.id,
        version=payload.consent_version,
        text_hash=sha256_hex(payload.consent_text),
        ip_address=req.client.host if req.client else None,
        user_agent=req.headers.get("user-agent"),
    )

    db.add(consent)
    db.commit()
    db.refresh(user)

    token = create_access_token(
        {
            "sub": str(user.id),
            "user_type": user.user_type,
        }
    )

    return TokenOut(
        access_token=token,
        user_type=user.user_type,
        full_name=user.full_name,
        email=user.email,
        country_code=user.country_code,
        phone_national=user.phone_national,
        phone_number=user.phone_number,
    )


# ============================================================
# LOGIN
# Permite iniciar sesión con:
# - correo electrónico
# - celular nacional de 10 dígitos + lada seleccionada en Flutter
# ============================================================
@app.post("/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    identifier = payload.identifier.strip()

    user = None

    # Login con correo
    if "@" in identifier:
        user = db.query(User).filter(User.email == identifier).first()

    # Login con celular de 10 dígitos
    elif identifier.isdigit() and len(identifier) == 10:
        if not payload.country_code:
            raise HTTPException(
                status_code=400,
                detail="Debes seleccionar la lada del país",
            )

        full_phone_number = f"{payload.country_code}{identifier}"

        user = (
            db.query(User)
            .filter(User.phone_number == full_phone_number)
            .first()
        )

    else:
        raise HTTPException(
            status_code=400,
            detail="Ingresa un correo válido o un celular de 10 dígitos",
        )

    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=401,
            detail="Credenciales inválidas",
        )

    token = create_access_token(
        {
            "sub": str(user.id),
            "user_type": user.user_type,
        }
    )

    return TokenOut(
        access_token=token,
        user_type=user.user_type,
        full_name=user.full_name,
        email=user.email,
        country_code=user.country_code,
        phone_national=user.phone_national,
        phone_number=user.phone_number,
    )


# ============================================================
# RECUPERACIÓN DE CONTRASEÑA - SOLICITAR CÓDIGO
# ============================================================
@app.post("/password/forgot", response_model=MessageOut)
def forgot_password(payload: ForgotPasswordIn, db: Session = Depends(get_db)):
    """
    Envía un código de recuperación al correo del usuario.

    Por seguridad, aunque el correo no exista, regresamos el mismo mensaje.
    Así evitamos revelar qué correos están registrados.
    """

    generic_message = "Si el correo está registrado, enviaremos un código de recuperación."

    user = db.query(User).filter(User.email == payload.email).first()

    if not user:
        return MessageOut(message=generic_message)

    # Invalidar códigos anteriores no usados del usuario
    previous_codes = (
        db.query(PasswordResetCode)
        .filter(
            PasswordResetCode.user_id == user.id,
            PasswordResetCode.used == 0,
        )
        .all()
    )

    for item in previous_codes:
        item.used = 1

    # Código de 6 dígitos
    code = f"{random.randint(0, 999999):06d}"

    reset_code = PasswordResetCode(
        user_id=user.id,
        code_hash=sha256_hex(code),
        expires_at=datetime.utcnow() + timedelta(minutes=10),
        used=0,
    )

    db.add(reset_code)
    db.commit()

    try:
        send_password_reset_email(user.email, code)
    except Exception as e:
        print("Error enviando correo de recuperación:")
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail="No se pudo enviar el correo de recuperación. Intenta más tarde.",
        )

    return MessageOut(message=generic_message)


# ============================================================
# RECUPERACIÓN DE CONTRASEÑA - RESTABLECER CONTRASEÑA
# ============================================================
@app.post("/password/reset", response_model=MessageOut)
def reset_password(payload: ResetPasswordIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()

    if not user:
        raise HTTPException(
            status_code=400,
            detail="Código inválido o expirado",
        )

    code_hash = sha256_hex(payload.code)

    reset_code = (
        db.query(PasswordResetCode)
        .filter(
            PasswordResetCode.user_id == user.id,
            PasswordResetCode.code_hash == code_hash,
            PasswordResetCode.used == 0,
        )
        .order_by(PasswordResetCode.created_at.desc())
        .first()
    )

    if not reset_code:
        raise HTTPException(
            status_code=400,
            detail="Código inválido o expirado",
        )

    if reset_code.expires_at < datetime.utcnow():
        reset_code.used = 1
        db.commit()

        raise HTTPException(
            status_code=400,
            detail="Código inválido o expirado",
        )

    # Actualizar contraseña
    user.password_hash = hash_password(payload.new_password)

    # Marcar código como usado
    reset_code.used = 1

    db.commit()

    return MessageOut(
        message="Contraseña actualizada correctamente."
    )