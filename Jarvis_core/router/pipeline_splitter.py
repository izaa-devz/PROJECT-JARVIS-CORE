"""
JARVIS — Pipeline Splitter
=============================
Divide comandos complejos multi-paso en acciones individuales.
Ejemplo: "abre chrome y busca tutorial de python" → 2 acciones
"""

import re
from typing import List
from dataclasses import dataclass
from utils.logger import get_logger

log = get_logger("router.pipeline_splitter")


@dataclass
class SubCommand:
    """Un sub-comando individual dentro de un comando complejo."""
    text: str
    order: int = 0
    depends_on_previous: bool = False


# Conjunciones y conectores que separan acciones
CONJUNCTIONS = [
    r"\s+y\s+(?:luego\s+|después\s+|despues\s+)?",
    r"\s+,\s+(?:luego\s+|después\s+|despues\s+)?",
    r"\s+después\s+",
    r"\s+despues\s+",
    r"\s+luego\s+",
    r"\s+y\s+después\s+",
    r"\s+y\s+despues\s+",
    r"\s+entonces\s+",
    r"\s+;\s+",
]

# Patrones que indican que una "y" es parte del mismo comando (no separador)
FALSE_SPLIT_PATTERNS = [
    r"busca.*y.*",  # "busca python y javascript" — no dividir
    r"cpu\s+y\s+ram",
    r"disco\s+y\s+memoria",
    r"archivos\s+y\s+carpetas",
]


class PipelineSplitter:
    """
    Divide un comando complejo en sub-comandos secuenciales.
    
    Reglas:
    - "abre chrome y busca python" → ["abre chrome", "busca python"]
    - "sube el volumen y abre spotify" → ["sube el volumen", "abre spotify"]
    - "busca python y javascript" → NO dividir (mismo contexto)
    """

    def split(self, text: str) -> List[SubCommand]:
        """
        Divide un texto en sub-comandos.
        
        Args:
            text: Texto completo del usuario
            
        Returns:
            Lista de SubCommand en orden de ejecución
        """
        text = text.strip()

        # Verificar si contiene conjunciones
        if not self._has_conjunction(text):
            return [SubCommand(text=text, order=0)]

        # Verificar falsos positivos
        if self._is_false_split(text):
            return [SubCommand(text=text, order=0)]

        # Dividir
        parts = self._split_text(text)

        # Filtrar partes vacías y crear SubCommands
        commands = []
        for i, part in enumerate(parts):
            part = part.strip()
            if part and len(part) > 2:
                # Determinar si depende del anterior
                depends = i > 0 and self._depends_on_previous(part, parts[i - 1] if i > 0 else "")
                commands.append(SubCommand(text=part, order=i, depends_on_previous=depends))

        if not commands:
            return [SubCommand(text=text, order=0)]

        if len(commands) > 1:
            log.info(f"Comando dividido en {len(commands)} pasos: {[c.text for c in commands]}")

        return commands

    def _has_conjunction(self, text: str) -> bool:
        """Verifica si el texto contiene alguna conjunción separadora."""
        for pattern in CONJUNCTIONS:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    def _is_false_split(self, text: str) -> bool:
        """Verifica si la conjunción es parte del mismo comando."""
        text_lower = text.lower()

        # Si solo hay un verbo de acción, probablemente no debemos dividir
        action_verbs = [
            "abre", "cierra", "busca", "crea", "ejecuta", "muestra",
            "sube", "baja", "toma", "dime", "pon",
        ]
        verb_count = sum(1 for verb in action_verbs if verb in text_lower)
        if verb_count <= 1:
            return True

        return False

    def _split_text(self, text: str) -> List[str]:
        """Divide el texto usando las conjunciones como separadores."""
        # Combinar patrones
        combined = "|".join(CONJUNCTIONS)
        parts = re.split(combined, text, flags=re.IGNORECASE)
        return [p.strip() for p in parts if p and p.strip()]

    def _depends_on_previous(self, current: str, previous: str) -> bool:
        """
        Determina si un sub-comando depende del resultado del anterior.
        Ej: "abre chrome" → "busca python en chrome" (depende de que chrome esté abierto)
        """
        dependency_indicators = [
            "en eso", "ahi", "ahí", "en ello", "en la misma",
        ]
        current_lower = current.lower()
        return any(ind in current_lower for ind in dependency_indicators)

    def __repr__(self) -> str:
        return "<PipelineSplitter>"
