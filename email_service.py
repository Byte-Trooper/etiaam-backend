# email_service.py
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)


def send_password_reset_email(to_email: str, code: str) -> None:
    """
    Envía un código de recuperación de contraseña por correo electrónico.

    Importante:
    - No se debe enviar la contraseña actual.
    - El código debe expirar en backend.
    - La contraseña SMTP debe venir desde variables de entorno.
    """

    if not SMTP_USER or not SMTP_PASSWORD:
        raise RuntimeError(
            "Faltan variables SMTP_USER o SMTP_PASSWORD en el entorno."
        )

    subject = "Código de recuperación ETIAAM"

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

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = SMTP_FROM
    message["To"] = to_email

    message.attach(MIMEText(text_body, "plain", "utf-8"))
    message.attach(MIMEText(html_body, "html", "utf-8"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_FROM, to_email, message.as_string())