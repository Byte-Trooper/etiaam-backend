# email_service.py
import os
import requests


RESEND_API_KEY = os.getenv("RESEND_API_KEY")
RESEND_FROM = os.getenv("RESEND_FROM", "ETIAAM <onboarding@resend.dev>")
RESEND_API_URL = "https://api.resend.com/emails"


def send_password_reset_email(to_email: str, code: str) -> None:
    """
    Envía un código de recuperación de contraseña por correo electrónico
    usando Resend API por HTTPS.

    Ya no se usa SMTP, porque Render puede bloquear puertos SMTP como 587.
    """

    if not RESEND_API_KEY:
        raise RuntimeError(
            "Falta la variable de entorno RESEND_API_KEY."
        )

    subject = "Código de recuperación ETIAAM"

    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #222;">
        <div style="max-width: 560px; margin: 0 auto; padding: 24px; border: 1px solid #ddd; border-radius: 12px;">
          <h2 style="color: #1A237E;">Recuperación de contraseña ETIAAM</h2>

          <p>Hola,</p>

          <p>Recibimos una solicitud para restablecer tu contraseña en ETIAAM.</p>

          <p>Tu código de recuperación es:</p>

          <div style="font-size: 28px; font-weight: bold; letter-spacing: 4px; color: #00796B; margin: 24px 0;">
            {code}
          </div>

          <p>Este código expirará en <strong>10 minutos</strong>.</p>

          <p>Si no solicitaste este cambio, puedes ignorar este mensaje.</p>

          <br>

          <p style="color: #555;">Atentamente,<br>Equipo ETIAAM</p>
        </div>
      </body>
    </html>
    """

    text_body = f"""
Hola,

Recibimos una solicitud para restablecer tu contraseña en ETIAAM.

Tu código de recuperación es:

{code}

Este código expirará en 10 minutos.

Si no solicitaste este cambio, puedes ignorar este mensaje.

Atentamente,
Equipo ETIAAM
"""

    payload = {
        "from": RESEND_FROM,
        "to": [to_email],
        "subject": subject,
        "html": html_body,
        "text": text_body,
    }

    headers = {
        "Authorization": f"Bearer {RESEND_API_KEY}",
        "Content-Type": "application/json",
    }

    response = requests.post(
        RESEND_API_URL,
        json=payload,
        headers=headers,
        timeout=20,
    )

    if response.status_code not in (200, 201, 202):
        raise RuntimeError(
            f"Error Resend {response.status_code}: {response.text}"
        )