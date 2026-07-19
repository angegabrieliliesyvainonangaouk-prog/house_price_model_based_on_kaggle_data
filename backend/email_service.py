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


async def send_verification_email(to_email: str, verification_token: str, base_url: str = "") -> bool:
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.warning("SMTP not configured, skipping email send")
        return False

    verify_url = f"{base_url}/api/v1/auth/verify-email?token={verification_token}" if base_url else f"/api/v1/auth/verify-email?token={verification_token}"

    msg = MIMEMultipart("alternative")
    msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
    msg["To"] = to_email
    msg["Subject"] = "ML Predictor Pro - Confirmez votre adresse e-mail"

    html = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 500px; margin: 0 auto; padding: 20px;">
        <div style="background: #f8f9fa; border-radius: 12px; padding: 32px; text-align: center;">
            <h1 style="color: #1a1a2e; font-size: 24px; margin-bottom: 8px;">ML Predictor Pro</h1>
            <p style="color: #666; margin-bottom: 24px;">Estimation Immobiliere par Intelligence Artificielle</p>
        </div>
        <div style="padding: 32px;">
            <h2 style="color: #1a1a2e; font-size: 20px;">Confirmez votre e-mail</h2>
            <p style="color: #444; line-height: 1.6;">
                Merci pour votre inscription ! Cliquez sur le bouton ci-dessous pour activer votre compte.
            </p>
            <div style="text-align: center; margin: 24px 0;">
                <a href="{verify_url}" style="display: inline-block; background: #2563eb; color: white; padding: 14px 32px; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 16px;">
                    Confirmer mon e-mail
                </a>
            </div>
            <p style="color: #666; font-size: 14px; line-height: 1.5;">
                Ce lien est valable pendant <strong>24 heures</strong>.
            </p>
            <p style="color: #999; font-size: 13px;">
                Si vous n'avez pas cree ce compte, ignorez cet e-mail.
            </p>
        </div>
    </body>
    </html>
    """

    text_content = f"""
Confirmez votre e-mail

Cliquez sur ce lien pour activer votre compte : {verify_url}

Ce lien est valable pendant 24 heures.
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
        logger.info(f"Verification email sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send verification email to {to_email}: {e}")
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
            <p style="color: #999; font-size: 12px;">Si vous n'avez pas effectue ce changement, contactez-nous immediatement.</p>
        </div>
    </body>
    """

    msg.attach(MIMEText("Votre mot de passe a ete modifie avec succes.", "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        await aiosmtplib.send(msg, hostname=SMTP_HOST, port=SMTP_PORT, start_tls=True, username=SMTP_USER, password=SMTP_PASSWORD)
        return True
    except Exception as e:
        logger.error(f"Failed to send password change email: {e}")
        return False
