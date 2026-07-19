import os
import logging
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger("email")

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "ML Predictor Pro")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "")


async def send_welcome_email(to_email: str, default_password: str) -> bool:
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.warning("SMTP not configured, skipping email send")
        return False

    msg = MIMEMultipart("alternative")
    msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
    msg["To"] = to_email
    msg["Subject"] = "Bienvenue sur ML Predictor Pro - Vos identifiants"

    html = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 500px; margin: 0 auto; padding: 20px;">
        <div style="background: #f8f9fa; border-radius: 12px; padding: 32px; text-align: center;">
            <h1 style="color: #1a1a2e; font-size: 24px; margin-bottom: 8px;">ML Predictor Pro</h1>
            <p style="color: #666; margin-bottom: 24px;">Estimation Immobiliere par Intelligence Artificielle</p>
        </div>
        <div style="padding: 32px;">
            <h2 style="color: #1a1a2e; font-size: 20px;">Bienvenue !</h2>
            <p style="color: #444; line-height: 1.6;">
                Votre compte a ete cree avec succes. Voici vos identifiants de connexion :
            </p>
            <div style="background: #f0f4ff; border: 1px solid #d0d9f0; border-radius: 8px; padding: 16px; margin: 20px 0;">
                <p style="margin: 0; color: #666; font-size: 13px;">Adresse e-mail</p>
                <p style="margin: 4px 0 12px; color: #1a1a2e; font-weight: 600;">{to_email}</p>
                <p style="margin: 0; color: #666; font-size: 13px;">Mot de passe temporaire</p>
                <p style="margin: 4px 0 0; color: #1a1a2e; font-weight: 600; font-family: monospace; font-size: 16px; letter-spacing: 1px;">{default_password}</p>
            </div>
            <p style="color: #dc2626; font-weight: 600; font-size: 14px;">
                IMPORTANT : Connectez-vous puis modifiez immediatement votre mot de passe depuis les parametres de votre compte.
            </p>
            <hr style="border: none; border-top: 1px solid #eee; margin: 24px 0;">
            <p style="color: #999; font-size: 12px;">
                Si vous n'avez pas cree ce compte, ignorez cet e-mail.
            </p>
        </div>
    </body>
    </html>
    """

    text_content = f"""
Bienvenue sur ML Predictor Pro !

Vos identifiants :
E-mail : {to_email}
Mot de passe temporaire : {default_password}

Connectez-vous puis modifiez votre mot de passe.
"""

    msg.attach(MIMEText(text_content, "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        await aiosmtplib.send(
            msg,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            start_tls=True,
            username=SMTP_USER,
            password=SMTP_PASSWORD,
        )
        logger.info(f"Welcome email sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False


async def send_password_change_confirmation(to_email: str) -> bool:
    if not SMTP_USER or not SMTP_PASSWORD:
        return False

    msg = MIMEMultipart("alternative")
    msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
    msg["To"] = to_email
    msg["Subject"] = "ML Predictor Pro - Mot de passe modifie"

    html = f"""
    <body style="font-family: -apple-system, sans-serif; max-width: 500px; margin: 0 auto; padding: 20px;">
        <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 24px; text-align: center;">
            <h2 style="color: #166534;">Mot de passe modifie</h2>
            <p style="color: #444;">Votre mot de passe a ete modifie avec succes.</p>
            <p style="color: #999; font-size: 12px;">Si vous n'avez pas effectue cette change, contactez-nous immediatement.</p>
        </div>
    </body>
    """

    msg.attach(MIMEText(f"Votre mot de passe a ete modifie avec succes.", "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        await aiosmtplib.send(msg, hostname=SMTP_HOST, port=SMTP_PORT, start_tls=True, username=SMTP_USER, password=SMTP_PASSWORD)
        return True
    except Exception as e:
        logger.error(f"Failed to send password change email: {e}")
        return False
