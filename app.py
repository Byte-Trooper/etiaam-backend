# app.py
from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
from db import Base, engine, get_db
from models import User, Consent
from schemas import RegisterIn, LoginIn, TokenOut
from auth import hash_password, verify_password, create_access_token, sha256_hex
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

print("✅ Routers cargados correctamente: /api/profile y /api/evaluations activos")

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
    return {"version": "v2.0", "text": text}


@app.post("/register", response_model=TokenOut)
def register(payload: RegisterIn, req: Request, db: Session = Depends(get_db)):
    if payload.user_type not in ("paciente", "profesional"):
        raise HTTPException(400, "user_type inválido")
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(409, "Email ya registrado")

    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
        user_type=payload.user_type
    )
    db.add(user)
    db.flush()

    consent = Consent(
        user_id=user.id,
        version=payload.consent_version,
        text_hash=sha256_hex(payload.consent_text),
        ip_address=req.client.host if req.client else None,
        user_agent=req.headers.get("user-agent")
    )
    db.add(consent)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": str(user.id), "user_type": user.user_type})
    return TokenOut(
        access_token=token,
        user_type=user.user_type,
        full_name=user.full_name,
        email=user.email
    )


@app.post("/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(401, "Credenciales inválidas")
    token = create_access_token({"sub": str(user.id), "user_type": user.user_type})
    return TokenOut(
        access_token=token,
        user_type=user.user_type,
        full_name=user.full_name,
        email=user.email
    )

