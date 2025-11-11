# models.py
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from db import Base

# ================================================================
# 🧩 USUARIOS
# ================================================================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(120))
    user_type = Column(String(50))  # 'paciente' | 'profesional'
    created_at = Column(DateTime, default=datetime.utcnow)

    profile = relationship("Profile", back_populates="user", uselist=False)
    evaluations = relationship("Evaluation", back_populates="user")


# ================================================================
# 🧩 CONSENTIMIENTOS
# ================================================================
class Consent(Base):
    __tablename__ = "consents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    version = Column(String(50))
    text_hash = Column(String(255))
    ip_address = Column(String(64))
    user_agent = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


# ================================================================
# 🧩 PERFILES (unificada para paciente y profesional)
# ================================================================
class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    # Campos comunes
    nombre = Column(String(100))
    apellido = Column(String(100))
    edad = Column(Integer)
    genero = Column(String(20))
    telefono = Column(String(20))
    direccion = Column(String(255))

    # Campos adicionales (según tipo de usuario)
    especialidad = Column(String(100))        # Profesionales
    fecha_nacimiento = Column(String(50))     # Pacientes
    nss = Column(String(50))                  # Pacientes
    alergias = Column(Text)                   # Pacientes
    respuestas = Column(JSON)
    user = relationship("User", back_populates="profile")


# ================================================================
# 🧩 EVALUACIONES
# ================================================================
class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    test_type = Column(String(100))  # Ejemplo: "Automanejo"
    score = Column(Float)
    observaciones = Column(Text)
    fecha_aplicacion = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="evaluations")
