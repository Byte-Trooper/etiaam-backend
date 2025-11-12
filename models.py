# models.py
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, inspect
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

    # 🔹 Relaciones
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

    user = relationship("User", back_populates="profile")


# ================================================================
# 🧩 EVALUACIONES
# ================================================================
class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    evaluador_id = Column(Integer, nullable=True)
    test_type = Column(String(100))
    score = Column(Float)
    respuestas_json = Column(Text, nullable=True)  # ✅ JSON serializado (TEXT para MySQL)
    observaciones = Column(Text)
    fecha_aplicacion = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="evaluations")


# ================================================================
# 🧩 Validación automática del esquema en ejecución
# ================================================================
def ensure_evaluation_columns(engine):
    inspector = inspect(engine)
    columns = [col["name"] for col in inspector.get_columns("evaluations")]
    if "respuestas_json" not in columns:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("ALTER TABLE evaluations ADD COLUMN respuestas_json TEXT NULL;"))
            conn.commit()
