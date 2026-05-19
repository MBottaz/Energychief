import re
from typing import Optional

def validate_pod(pod: str) -> bool:
    """
    Validates the POD format (IT001E12345678).
    Expected 14 characters: IT + 3 digits + E + 8 digits.
    """
    return bool(re.match(r"^IT\d{3}E\d{8}$", pod))

def extract_pod_prefix(pod: str) -> str:
    """
    Extracts the first 8 characters of the POD (identifies the primary substation).
    """
    return pod[:8]
