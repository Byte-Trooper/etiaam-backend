from pydantic import BaseModel
from datetime import datetime
from typing import Optional

# --- Perfil ---
class ProfileIn(BaseModel):
    user_id: int
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    edad: Optional[int] = None
    genero: Optional[str] = None
    especialidad: Optional[str] = None
    telefono: Optional[str] = None
    direccion: Optional[str] = None

class ProfileOut(ProfileIn):
    id: int
    class Config:
        orm_mode = True

# --- Evaluación ---
class EvaluationIn(BaseModel):
    user_id: int
    test_type: str
    score: float
    observaciones: Optional[str] = None

class EvaluationOut(EvaluationIn):
    id: int
    fecha_aplicacion: datetime
    class Config:
        orm_mode = True
