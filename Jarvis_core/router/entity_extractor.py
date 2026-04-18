"""
JARVIS — Entity Extractor (Extractor de Entidades)
=====================================================
Extrae entidades relevantes del texto del usuario:
aplicaciones, rutas, URLs, números, tiempos, etc.
"""

import re
from typing import Any, Dict, List, Optional
from utils.logger import get_logger
from utils.helpers import normalize_text, remove_accents, extract_numbers, extract_urls, is_url

log = get_logger("router.entity_extractor")


# Preposiciones y artículos a ignorar al extraer el target
STOP_WORDS = {
    "el", "la", "los", "las", "un", "una", "unos", "unas",
    "de", "del", "al", "en", "a", "por", "para", "con", "sin",
    "que", "es", "fue", "ser", "como", "mas", "pero", "y", "o",
    "me", "mi", "te", "tu", "se", "si", "no", "ya",
    "muy", "algo", "esto", "eso", "esta", "ese",
    "por favor", "porfavor", "porfa", "please",
}

# Verbos de acción a ignorar cuando extraemos el target
ACTION_VERBS = {
    "abre", "abrir", "abreme", "cierra", "cerrar", "mata", "matar",
    "ejecuta", "ejecutar", "inicia", "iniciar", "lanza", "lanzar",
    "busca", "buscar", "googlea", "googlear", "encuentra", "encontrar",
    "crea", "crear", "genera", "generar", "haz", "hacer",
    "toma", "tomar", "saca", "sacar", "captura", "capturar",
    "sube", "subir", "baja", "bajar", "pon", "poner",
    "muestra", "mostrar", "dime", "decir", "dame", "dar",
    "aumenta", "aumentar", "reduce", "reducir", "establece", "establecer",
    "silencia", "silenciar", "mutea", "mutear",
    "apaga", "apagar", "reinicia", "reiniciar",
    "bloquea", "bloquear", "suspende", "suspender",
    "corre", "correr", "run", "arranca", "arrancar",
    "lista", "listar", "enseña", "ensenar",
}


class EntityExtractor:
    """
    Extrae entidades del texto del comando.
    
    Entidades soportadas:
    - app_name: Nombre de aplicación
    - file_name: Nombre de archivo
    - file_path: Ruta de archivo
    - url: URL
    - search_query: Consulta de búsqueda
    - number: Valor numérico
    - percentage: Porcentaje
    - command_text: Texto de comando CMD/PowerShell
    - time_value: Valor de tiempo
    - direction: Dirección (arriba/abajo)
    """

    def __init__(self):
        self._nlp = None
        try:
            import spacy
            self._nlp = spacy.load("es_core_news_md")
        except Exception:
            pass  # spaCy es opcional para extracción de entidades

    def extract(self, text: str, intent: str = "") -> Dict[str, Any]:
        """
        Extrae todas las entidades relevantes del texto.
        
        Args:
            text: Texto original del usuario
            intent: Intención clasificada (ayuda a decidir qué extraer)
            
        Returns:
            Diccionario de entidades extraídas
        """
        entities: Dict[str, Any] = {}

        # URLs
        urls = extract_urls(text)
        if urls:
            entities["url"] = urls[0]
            entities["urls"] = urls

        # Números
        numbers = extract_numbers(text)
        if numbers:
            entities["number"] = numbers[0]
            entities["numbers"] = numbers
            # ¿Es un porcentaje?
            if "%" in text or "por ciento" in text or "porciento" in text:
                entities["percentage"] = min(100, max(0, int(numbers[0])))

        # Extraer basado en intent
        if intent:
            intent_extractors = {
                "open_app": self._extract_app_name,
                "close_app": self._extract_app_name,
                "search_web": self._extract_search_query,
                "open_url": self._extract_url,
                "create_file": self._extract_file_info,
                "find_file": self._extract_file_info,
                "list_files": self._extract_path,
                "execute_cmd": self._extract_command_text,
                "volume_up": self._extract_amount,
                "volume_down": self._extract_amount,
                "volume_set": self._extract_amount,
                "brightness_up": self._extract_amount,
                "brightness_down": self._extract_amount,
                "brightness_set": self._extract_amount,
            }
            extractor = intent_extractors.get(intent)
            if extractor:
                specific = extractor(text)
                entities.update(specific)

        # Target genérico (lo que queda después de quitar verbos y stop words)
        if "target" not in entities:
            target = self._extract_generic_target(text)
            if target:
                entities["target"] = target

        return entities

    def _extract_app_name(self, text: str) -> Dict[str, str]:
        """Extrae el nombre de la aplicación."""
        # Quitar verbos de acción y stop words
        target = self._extract_generic_target(text)
        if target:
            return {"app_name": target, "target": target}
        return {}

    def _extract_search_query(self, text: str) -> Dict[str, str]:
        """Extrae la consulta de búsqueda."""
        text_lower = text.lower()

        # Patrones comunes
        patterns = [
            r"busca(?:r)?(?:\s+en\s+(?:google|internet|la web))?\s+(.+)",
            r"googlea(?:r)?\s+(.+)",
            r"investiga(?:r)?\s+(.+)",
            r"busca(?:r)?\s+(?:que|como|por que|donde|cuando|quien)\s+(.+)",
            r"busca(?:r)?\s+(?:sobre|acerca de|informacion de|info de)\s+(.+)",
            r"busca(?:r)?\s+(.+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                query = match.group(1).strip()
                # Limpiar stop words del final
                query = re.sub(r"\s+(por favor|porfa|porfavor|please)$", "", query)
                return {"search_query": query, "target": query}

        return {}

    def _extract_url(self, text: str) -> Dict[str, str]:
        """Extrae URL del texto."""
        urls = extract_urls(text)
        if urls:
            return {"url": urls[0], "target": urls[0]}

        # Intentar detectar dominios sin protocolo
        domain_pattern = re.search(r"(\S+\.\S{2,})", text)
        if domain_pattern:
            url = domain_pattern.group(1)
            if not url.startswith("http"):
                url = "https://" + url
            return {"url": url, "target": url}

        return {}

    def _extract_file_info(self, text: str) -> Dict[str, str]:
        """Extrae información de archivo."""
        entities = {}

        # Buscar nombre de archivo con extensión
        file_pattern = re.search(r"(\S+\.\w{1,5})", text)
        if file_pattern:
            entities["file_name"] = file_pattern.group(1)
            entities["target"] = file_pattern.group(1)

        # Buscar nombre después de "llamado", "con nombre"
        name_patterns = [
            r"(?:llamado|con nombre|nombre)\s+[\"']?(\S+)[\"']?",
            r"(?:archivo|fichero|documento)\s+[\"']?(\S+)[\"']?",
        ]
        for pattern in name_patterns:
            match = re.search(pattern, text.lower())
            if match:
                name = match.group(1).strip("\"'")
                entities["file_name"] = name
                entities["target"] = name
                break

        # Buscar contenido después de "con contenido", "que diga"
        content_patterns = [
            r"(?:con contenido|que diga|que contenga|con texto)\s+[\"']?(.+?)[\"']?$",
            r"(?:contenido|texto)\s*[:=]\s*[\"']?(.+?)[\"']?$",
        ]
        for pattern in content_patterns:
            match = re.search(pattern, text.lower())
            if match:
                entities["content"] = match.group(1).strip("\"'")
                break

        return entities

    def _extract_path(self, text: str) -> Dict[str, str]:
        """Extrae ruta de directorio o archivo."""
        # Buscar rutas de Windows
        path_pattern = re.search(r"([A-Za-z]:\\[^\s]+|\\\\[^\s]+)", text)
        if path_pattern:
            return {"path": path_pattern.group(1), "target": path_pattern.group(1)}

        # Buscar rutas relativas
        rel_pattern = re.search(r"(\.[\\/][^\s]+)", text)
        if rel_pattern:
            return {"path": rel_pattern.group(1), "target": rel_pattern.group(1)}

        return {}

    def _extract_command_text(self, text: str) -> Dict[str, str]:
        """Extrae el comando a ejecutar en CMD/PowerShell."""
        text_lower = text.lower()

        patterns = [
            r"(?:ejecuta|ejecutar|corre|correr|run)\s+(?:el\s+)?(?:comando\s+)?[\"'](.+?)[\"']",
            r"(?:en|por)\s+(?:cmd|powershell|terminal|consola)\s*[:=]?\s*(.+)",
            r"(?:ejecuta|ejecutar|corre|correr|run)\s+(?:el\s+)?(?:comando\s+)?(.+?)(?:\s+en\s+(?:cmd|powershell|terminal))?$",
        ]

        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                cmd = match.group(1).strip("\"' ")
                shell = "powershell" if "powershell" in text_lower else "cmd"
                return {"command_text": cmd, "shell": shell, "target": cmd}

        return {}

    def _extract_amount(self, text: str) -> Dict[str, Any]:
        """Extrae cantidad/porcentaje para volume/brightness."""
        entities = {}

        numbers = extract_numbers(text)
        if numbers:
            entities["amount"] = int(numbers[0])

        # Detectar palabras de cantidad
        from utils.helpers import parse_percentage
        pct = parse_percentage(text)
        if pct is not None:
            entities["amount"] = pct

        return entities

    def _extract_generic_target(self, text: str) -> str:
        """
        Extrae el target genérico quitando verbos de acción y stop words.
        Ejemplo: "abre el navegador chrome" → "navegador chrome" → "chrome"
        """
        words = text.lower().split()
        filtered = []
        for word in words:
            clean = remove_accents(word.strip("¿?¡!.,;:"))
            if clean and clean not in ACTION_VERBS and clean not in STOP_WORDS:
                filtered.append(word.strip("¿?¡!.,;:"))

        return " ".join(filtered).strip()

    def __repr__(self) -> str:
        spacy = "✓" if self._nlp else "✗"
        return f"<EntityExtractor spaCy={spacy}>"
