import unicodedata


def normalize_password(value: str) -> str:
    return unicodedata.normalize("NFC", value)
