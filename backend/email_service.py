import os
import logging
import httpx

logger = logging.getLogger("email")

BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "ML Predictor Pro")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "")


async def send_verification_email(to_email: str, verification_token: str, base_url: str = "") -> bool:
    if not BREVO_API_KEY:
        logger.warning("BREVO_API_KEY not configured, skipping email send")
        return False

    verify_url = f"{base_url}/api/v1/auth/verify-email?token={verification_token}" if base_url else f"/api/v1/auth/verify-email?token={verification_token}"

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

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.brevo.com/v3/smtp/email",
                headers={
                    "api-key": BREVO_API_KEY,
                    "Content-Type": "application/json",
                },
                json={
                    "sender": {"name": SMTP_FROM_NAME, "email": SMTP_FROM_EMAIL},
                    "to": [{"email": to_email}],
                    "subject": "ML Predictor Pro - Confirmez votre adresse e-mail",
                    "textContent": text_content,
                    "htmlContent": html,
                },
                timeout=10.0,
            )
            if resp.status_code == 201:
                logger.info(f"Verification email sent to {to_email}")
                return True
            else:
                logger.error(f"Failed to send verification email to {to_email}: {resp.status_code} {resp.text}")
                return False
    except Exception as e:
        logger.error(f"Failed to send verification email to {to_email}: {e}")
        return False


async def send_password_change_confirmation(to_email: str) -> bool:
    if not BREVO_API_KEY:
        return False

    html = """
    <body style="font-family: -apple-system, sans-serif; max-width: 500px; margin: 0 auto; padding: 20px;">
        <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 8px; padding: 24px; text-align: center;">
            <h2 style="color: #166534;">Mot de passe modifie</h2>
            <p style="color: #444;">Votre mot de passe a ete modifie avec succes.</p>
            <p style="color: #999; font-size: 12px;">Si vous n'avez pas effectue ce changement, contactez-nous immediatement.</p>
        </div>
    </body>
    """

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.brevo.com/v3/smtp/email",
                headers={
                    "api-key": BREVO_API_KEY,
                    "Content-Type": "application/json",
                },
                json={
                    "sender": {"name": SMTP_FROM_NAME, "email": SMTP_FROM_EMAIL},
                    "to": [{"email": to_email}],
                    "subject": "ML Predictor Pro - Mot de passe modifie",
                    "textContent": "Votre mot de passe a ete modifie avec succes.",
                    "htmlContent": html,
                },
                timeout=10.0,
            )
            return resp.status_code == 201
    except Exception as e:
        logger.error(f"Failed to send password change email: {e}")
        return False
