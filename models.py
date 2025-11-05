from sqlalchemy import (
    Column, Integer, String, ForeignKey, DateTime, Float, Text, Table
)
from sqlalchemy.orm import relationship
from datetime import datetime
from db import Base

# --- Tabla intermedia para relación muchos-a-muchos (profesional ↔ paciente) ---
patients_professionals = Table(
    "patients_professionals",
    Base.metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("professional_id", Integer, ForeignKey("users.id")),
    Column("patient_id", Integer, ForeignKey("users.id"))
)

# --- Usuario principal (paciente o profesional) ---
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(120), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    user_type = Column(String(20), nullable=False)  # 'paciente' o 'profesional'
    full_name = Column(String(120))
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relaciones
    profile = relationship("Profile", back_populates="user", uselist=False)
    evaluations = relationship("Evaluation", back_populates="user")
    consents = relationship("Consent", back_populates="user")

    # Profesionales pueden tener muchos pacientes y viceversa
    patients = relationship(
        "User",
        secondary=patients_professionals,
        primaryjoin=id == patients_professionals.c.professional_id,
        secondaryjoin=id == patients_professionals.c.patient_id,
        backref="professionals"
    )

# --- Información adicional de cada usuario ---
class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    nombre = Column(String(120))
    apellido = Column(String(120))
    edad = Column(Integer)
    genero = Column(String(50))
    especialidad = Column(String(120))
    telefono = Column(String(50))
    direccion = Column(String(255))

    user = relationship("User", back_populates="profile")

# --- Consentimientos informados ---
class Consent(Base):
    __tablename__ = "consents"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    version = Column(String(10))
    text_hash = Column(String(64))
    ip_address = Column(String(100))
    user_agent = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="consents")

# --- Evaluaciones de los instrumentos ---
class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))  # paciente o profesional
    test_type = Column(String(50))  # 'Automanejo', 'Apoyo familiar', etc.
    score = Column(Float)
    fecha_aplicacion = Column(DateTime, default=datetime.utcnow)
    observaciones = Column(Text)

    user = relationship("User", back_populates="evaluations")
