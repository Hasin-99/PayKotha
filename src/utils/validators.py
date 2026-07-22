from __future__ import annotations

import re


BD_PHONE_RE = re.compile(r"^(?:\+8801|8801|01)[3-9]\d{8}$")


def normalize_phone(phone: str) -> str:
    """Normalize BD mobile numbers to 01XXXXXXXXX."""
    digits = re.sub(r"[\s\-]", "", phone.strip())
    if digits.startswith("+880"):
        digits = "0" + digits[4:]
    elif digits.startswith("880"):
        digits = "0" + digits[3:]
    return digits


def validate_phone(phone: str) -> str:
    normalized = normalize_phone(phone)
    if not BD_PHONE_RE.match(normalized):
        raise ValueError(
            "Invalid Bangladeshi mobile number. Example: 01712345678"
        )
    return normalized


def validate_pin(pin: str) -> str:
    if not re.fullmatch(r"\d{4,6}", pin):
        raise ValueError("PIN must be 4–6 digits")
    return pin


def validate_name(name: str) -> str:
    name = name.strip()
    if len(name) < 2:
        raise ValueError("Name must be at least 2 characters")
    return name


def format_money(amount: float) -> str:
    return f"৳{amount:,.2f}"
