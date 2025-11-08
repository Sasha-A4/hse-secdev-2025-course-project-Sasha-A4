"""Утилиты для безопасного кодирования: маскирование PII, валидация и т.д."""

import logging
import re

# Настройка логирования без PII
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def mask_pii(data: str) -> str:
    """Маскирует PII (email, телефон, кредитные карты) в строках"""
    if not isinstance(data, str):
        return str(data)

    # Кредитная карта: 1234 5678 9012 3456 -> **** **** **** 3456
    # (сначала, чтобы не конфликтовать с телефоном)
    data = re.sub(
        r"\b(\d{4}[\s-]?)(\d{4}[\s-]?)(\d{4}[\s-]?)(\d{4})\b",
        r"**** **** **** \4",
        data,
    )

    # Email: user@domain.com -> u***@domain.com (минимум 1 символ перед @)
    data = re.sub(
        r"\b([a-zA-Z0-9._%+-])([a-zA-Z0-9._%+-]*?)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\b",
        r"\1***@\3",
        data,
    )

    # Телефон: +7 999 123-45-67 -> +7 *** ***-**-67
    data = re.sub(
        r"\b(\+?\d{1,3}[\s-]?)(\d{1,3}[\s-]?)(\d{1,3}[\s-]?)(\d{1,2}[\s-]?)(\d{2})\b",
        r"\1*** ***-**-\5",
        data,
    )

    return data


def sanitize_error_detail(detail: str) -> str:
    """Очищает детали ошибки от потенциально чувствительной информации"""
    if not isinstance(detail, str):
        return str(detail)
    # Маскируем PII
    masked = mask_pii(detail)
    # Удаляем потенциально опасные символы для логирования
    sanitized = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f]", "", masked)
    return sanitized


def safe_log_error(message: str, correlation_id: str, error_detail: str = ""):
    """Безопасное логирование ошибок без PII"""
    masked_detail = sanitize_error_detail(error_detail) if error_detail else ""
    logger.error(
        f"[{correlation_id}] {message}",
        extra={
            "correlation_id": correlation_id,
            "error_detail": masked_detail[:200],  # Ограничение длины
        },
    )
