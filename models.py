from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from db import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(255))
    user_type = Column(String(50), nullable=False)  # 'paciente' | 'profesional'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    consents = relationship("Consent", back_populates="user")

class Consent(Base):
    __tablename__ = "consents"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    version = Column(String(20), nullable=False)
    text_hash = Column(String(64), nullable=False)
    accepted_at = Column(DateTime(timezone=True), server_default=func.now())
    ip_address = Column(String(45))
    user_agent = Column(String(255))
    user = relationship("User", back_populates="consents")
