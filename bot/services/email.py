"""Отправка email-уведомлений."""
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from bot.config.settings import HELP_EMAIL, SMTP_HOST, SMTP_PASSWORD, SMTP_PORT, SMTP_USER

logger = logging.getLogger(__name__)


def send_help_request_email(
    *,
    username: str,
    full_name: str,
    user_id: int,
    help_text: str,
) -> bool:
    """
    Отправляет запрос помощи на email.
    Возвращает True при успехе, False при ошибке или отсутствии SMTP-настроек.
    """
    if not all([SMTP_HOST, SMTP_USER, SMTP_PASSWORD, HELP_EMAIL]):
        logger.info(
            "Письмо не отправлено: SMTP не настроен. Добавьте в .env: SMTP_HOST, SMTP_USER, SMTP_PASSWORD"
        )
        return False

    subject = "🆘 Запрос помощи из бота"
    body = (
        f"Пользователю нужна помощь\n\n"
        f"Имя: {full_name}\n"
        f"Username: @{username or '—'}\n"
        f"User ID: {user_id}\n\n"
        f"Текст запроса:\n{help_text}"
    )

    try:
        import smtplib

        msg = MIMEMultipart()
        msg["From"] = SMTP_USER
        msg["To"] = HELP_EMAIL
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, HELP_EMAIL, msg.as_string())

        logger.info("Запрос помощи отправлен на %s", HELP_EMAIL)
        return True
    except Exception as e:
        logger.warning("Не удалось отправить email: %s", e)
        return False
