# bot/validators.py
# Pure validation functions — no Telegram imports, no side effects.
# Easy to unit-test in isolation, and reusable across any conversation phase.


def parse_positive_float(text: str) -> float | None:
    """
    Try to parse text as a positive float.
    Returns the float if valid, None otherwise.
    """
    try:
        value = float(text.replace(",", "."))  # accept both 0.25 and 0,25
        if value <= 0:
            return None
        return value
    except ValueError:
        return None
