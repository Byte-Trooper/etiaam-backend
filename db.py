# db.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# Lee la URL desde la variable de entorno (Render -> Environment)
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(
    DATABASE_URL,
    connect_args={"ssl": {}},   # Aiven SSL
    pool_pre_ping=True,
    pool_recycle=300
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 🔹 Nueva función: aquí sí definimos get_db()
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
