from pydantic import BaseModel, EmailStr

class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    user_type: str  # 'paciente' | 'profesional'
    consent_text: str
    consent_version: str

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_type: str
    full_name: str
    email: EmailStr
