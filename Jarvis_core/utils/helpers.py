"""
JARVIS — Utilidades Generales
==============================
Funciones helper reutilizables por todo el sistema.
"""

import re
import os
import unicodedata
from datetime import datetime
from typing import Optional


def normalize_text(text: str) -> str:
    """
    Normaliza texto para procesamiento NLP.
    - Minúsculas
    - Elimina acentos
    - Elimina caracteres especiales extra
    - Normaliza espacios
    """
    text = text.strip().lower()
    # Remover acentos
    text = remove_accents(text)
    # Normalizar espacios múltiples
    text = re.sub(r"\s+", " ", text)
    return text


def remove_accents(text: str) -> str:
    """Elimina acentos y diacríticos de un texto."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def format_bytes(size_bytes: int) -> str:
    """Formatea bytes a formato legible (KB, MB, GB, TB)."""
    if size_bytes == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = float(size_bytes)
    while size >= 1024.0 and i < len(units) - 1:
        size /= 1024.0
        i += 1
    return f"{size:.2f} {units[i]}"


def format_duration(seconds: float) -> str:
    """Formatea duración en segundos a formato legible."""
    if seconds < 1:
        return f"{seconds * 1000:.0f}ms"
    elif seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}m {secs}s"
    else:
        hours = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        return f"{hours}h {mins}m"


def get_timestamp() -> str:
    """Retorna timestamp ISO 8601 actual."""
    return datetime.now().isoformat()


def get_time_greeting() -> str:
    """Retorna saludo basado en la hora del día."""
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return "Buenos días"
    elif 12 <= hour < 19:
        return "Buenas tardes"
    else:
        return "Buenas noches"


def sanitize_filename(name: str) -> str:
    """Sanitiza un nombre de archivo eliminando caracteres no válidos."""
    invalid_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(invalid_chars, "_", name)
    sanitized = sanitized.strip(". ")
    return sanitized[:255] if sanitized else "unnamed"


def extract_numbers(text: str) -> list:
    """Extrae todos los números de un texto."""
    return [int(n) if n.isdigit() else float(n) for n in re.findall(r"\d+\.?\d*", text)]


def is_url(text: str) -> bool:
    """Verifica si un texto parece ser una URL."""
    url_pattern = re.compile(
        r"^(https?://|www\.)[^\s/$.?#].[^\s]*$", re.IGNORECASE
    )
    return bool(url_pattern.match(text.strip()))


def extract_urls(text: str) -> list:
    """Extrae todas las URLs de un texto."""
    url_pattern = re.compile(
        r"(https?://[^\s]+|www\.[^\s]+)", re.IGNORECASE
    )
    return url_pattern.findall(text)


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Trunca texto a longitud máxima con sufijo."""
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def pluralize(count: int, singular: str, plural: Optional[str] = None) -> str:
    """Pluraliza una palabra según el conteo."""
    if plural is None:
        plural = singular + "s"
    return f"{count} {singular if count == 1 else plural}"


def ensure_dir(path: str) -> str:
    """Asegura que un directorio exista. Retorna la ruta."""
    os.makedirs(path, exist_ok=True)
    return path


def safe_json_loads(text: str, default=None):
    """Carga JSON de forma segura, retornando default si falla."""
    import json
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return default


# Mapa de palabras numéricas en español a valores
WORD_TO_NUMBER = {
    "cero": 0, "uno": 1, "una": 1, "dos": 2, "tres": 3, "cuatro": 4,
    "cinco": 5, "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10,
    "once": 11, "doce": 12, "trece": 13, "catorce": 14, "quince": 15,
    "veinte": 20, "veinticinco": 25, "treinta": 30, "cuarenta": 40,
    "cincuenta": 50, "sesenta": 60, "setenta": 70, "ochenta": 80,
    "noventa": 90, "cien": 100, "maximo": 100, "minimo": 0,
    "medio": 50, "mitad": 50, "todo": 100, "nada": 0, "completo": 100,
}


def word_to_number(word: str) -> Optional[int]:
    """Convierte una palabra numérica en español a su valor."""
    word = normalize_text(word)
    return WORD_TO_NUMBER.get(word)


def parse_percentage(text: str) -> Optional[int]:
    """
    Extrae un valor de porcentaje de un texto.
    Soporta: "50%", "50 por ciento", "cincuenta", "al máximo"
    """
    # Buscar número directo
    numbers = extract_numbers(text)
    if numbers:
        val = int(numbers[0])
        return max(0, min(100, val))

    # Buscar palabras numéricas
    text_normalized = normalize_text(text)
    for word, value in WORD_TO_NUMBER.items():
        if word in text_normalized:
            return value

    return None
