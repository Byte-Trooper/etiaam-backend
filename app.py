from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from db import Base, engine, SessionLocal
from models import User, Consent
from schemas import RegisterIn, LoginIn, TokenOut
from auth import hash_password, verify_password, create_access_token, sha256_hex

# 👇 De momento, mantenla activa hasta confirmar todas las tablas
Base.metadata.create_all(bind=engine)

# 👇 Nueva importación de tus rutas extendidas
from routes_profile import router as profile_router

app = FastAPI(title="ETIAAM API", version="1.0.0")

# CORS abierto para desarrollo
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/health")
def health(): return {"ok": True}

@app.get("/consent/latest")
def latest_consent():
    text = (
        "Autorización informada para el tratamiento de datos de salud (v1.0)\n"
        "• Finalidad: mejorar la atención y automanejo de ECNT.\n"
        "• Datos: identificación y registros de salud proporcionados.\n"
        "• Transferencias: solo equipo autorizado conforme a la ley.\n"
        "• Seguridad: medidas técnicas/administrativas, acceso restringido.\n"
        "• Derechos ARCO: acceso, rectificación, cancelación u oposición.\n"
        "Al aceptar, confirmas que leíste y autorizas el tratamiento."
    )
    return {"version": "v1.0", "text": text}

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

# 👇 Incluye tus nuevas rutas API (perfil y evaluaciones)
app.include_router(profile_router)
