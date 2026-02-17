import re

EMAIL_REGEX = re.compile(r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
PHONE_REGEX = re.compile(r'^\+?[1-9]\d{7,14}$')


def normalize_company_name(value: str) -> str:
    return value.strip().lower()


def is_valid_email(email: str | None) -> bool:
    if not email:
        return False
    return bool(EMAIL_REGEX.match(email.strip()))


def is_valid_phone(phone: str | None) -> bool:
    if not phone:
        return False
    compact = re.sub(r'[\s\-()]', '', phone)
    return bool(PHONE_REGEX.match(compact))
