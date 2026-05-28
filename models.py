# models.py
from sqlalchemy import Column, Integer, String, Text, Float, DateTime, ForeignKey, inspect
from sqlalchemy.orm import relationship
from datetime import datetime
from db import Base

# ================================================================
# USUARIOS
# ================================================================
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    # Correo: se mantiene como identificador principal tradicional
    email = Column(String(120), unique=True, nullable=False)

    # Contraseña cifrada
    password_hash = Column(String(255), nullable=False)

    # Datos generales
    full_name = Column(String(120))
    user_type = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)

    # ============================================================
    # TELÉFONO PARA LOGIN
    # ============================================================
    # country_code:
    #   Guarda la lada del país. Ejemplo:
    #   México: +52
    #   Perú:   +51
    #
    # phone_national:
    #   Guarda solo los 10 dígitos que escribe el usuario.
    #   Ejemplo: 8331234567
    #
    # phone_number:
    #   Guarda el teléfono completo con lada.
    #   Ejemplo: +528331234567
    #
    # Este campo sí debe ser único porque se usará para iniciar sesión.
    # ============================================================
    country_code = Column(String(5), nullable=True)
    phone_national = Column(String(10), nullable=True)
    phone_number = Column(String(20), unique=True, index=True, nullable=True)

    # Relaciones
    profile = relationship("Profile", back_populates="user", uselist=False)
    evaluations = relationship("Evaluation", back_populates="user")
    competencias = relationship("CompetenciasProfesionales", back_populates="user")


# ================================================================
# CONSENTIMIENTOS
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
# CÓDIGOS PARA RECUPERACIÓN DE CONTRASEÑA
# ================================================================
class PasswordResetCode(Base):
    __tablename__ = "password_reset_codes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Guardamos hash del código, no el código en texto plano
    code_hash = Column(String(255), nullable=False)

    # Fecha y hora de expiración del código
    expires_at = Column(DateTime, nullable=False)

    # Para evitar reutilizar el mismo código
    used = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)

# ================================================================
# PERFILES (Pacientes y profesionales)
# ================================================================
class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    # Comunes
    nombre = Column(String(100), nullable=True)
    apellido = Column(String(100), nullable=True)
    edad = Column(Integer, nullable=True)
    genero = Column(String(20), nullable=True)
    telefono = Column(String(20), nullable=True)
    direccion = Column(String(255), nullable=True)

    # Profesionales
    especialidad = Column(String(100), nullable=True)
    cedula_profesional = Column(String(50), nullable=True)
    unidad_medica = Column(String(150), nullable=True)

    # Pacientes
    fecha_nacimiento = Column(String(50), nullable=True)
    nss = Column(String(50), nullable=True)

    user = relationship("User", back_populates="profile")


# ================================================================
# EVALUACIONES
# ================================================================
class Evaluation(Base):
    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    evaluador_id = Column(Integer, nullable=True)
    test_type = Column(String(100))
    score = Column(Integer)
    respuestas_json = Column(Text, nullable=True)
    observaciones = Column(Text, nullable=True)
    fecha_aplicacion = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="evaluations")


# ================================================================
# COMPETENCIAS PROFESIONALES
# ================================================================
class CompetenciasProfesionales(Base):
    __tablename__ = "competencias_profesionales"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))

    # JSON serializado
    respuestas = Column(Text)   # <--- Compatibilidad universal

    f1_promedio = Column(Float)
    f2_promedio = Column(Float)
    f3_promedio = Column(Float)
    f4_promedio = Column(Float)
    puntaje_total = Column(Float)

    fecha_aplicacion = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="competencias")


# ================================================================
# PLAN DE TRABAJO
# ================================================================
class PlanTrabajo(Base):
    __tablename__ = "plan_trabajo"

    id = Column(Integer, primary_key=True, index=True)

    paciente_id = Column(Integer, ForeignKey("users.id"))
    profesional_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    fecha_creacion = Column(DateTime, default=datetime.utcnow)

    objetivo_principal = Column(Text)
    plan_ejecucion = Column(Text)
    recursos_necesarios = Column(Text)
    emociones_asociadas = Column(Text)

    estado = Column(String(20), default="activo")  # activo / cerrado

    objetivos = relationship(
        "ObjetivoPlan",
        back_populates="plan",
        cascade="all, delete",
    )


# ================================================================
# OBJETIVOS DEL PLAN DE TRABAJO
# ================================================================
class ObjetivoPlan(Base):
    __tablename__ = "objetivos_plan"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("plan_trabajo.id"))

    descripcion = Column(String(255))
    actividad = Column(String(255))
    recursos = Column(String(255))
    seguimiento = Column(Text)
    fecha_revision = Column(String(20), nullable=True)

    cumplimiento = Column(Integer, default=0)

    plan = relationship("PlanTrabajo", back_populates="objetivos")
    __tablename__ = "objetivos_plan"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("plan_trabajo.id"))

    descripcion = Column(String(255))
    actividad = Column(String(255))
    recursos = Column(String(255))
    seguimiento = Column(Text)

    cumplimiento = Column(Integer, default=0)

    plan = relationship("PlanTrabajo", back_populates="objetivos")