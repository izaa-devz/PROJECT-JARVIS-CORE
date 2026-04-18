"""
JARVIS — Sistema de Preferencias del Usuario
===============================================
Almacena y gestiona preferencias del usuario persistentes.
Incluye aprendizaje de correcciones de intención.
"""

import json
import os
from typing import Any, Dict, List, Optional
from utils.logger import get_logger

log = get_logger("memory.preferences")


class Preferences:
    """
    Gestor de preferencias del usuario.
    
    Almacena:
    - Aplicaciones favoritas
    - Configuraciones personalizadas
    - Correcciones de intenciones (aprendizaje)
    - Alias personalizados
    """

    def __init__(self, data_dir: str = "data"):
        self._data_dir = data_dir
        self._file_path = os.path.join(data_dir, "preferences.json")
        self._prefs: Dict[str, Any] = {
            "favorites": {},
            "aliases": {},
            "corrections": [],
            "custom": {},
        }

    def load(self) -> None:
        """Carga preferencias desde disco."""
        if os.path.exists(self._file_path):
            try:
                with open(self._file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._prefs.update(data)
                log.debug("Preferencias cargadas")
            except Exception as e:
                log.error(f"Error cargando preferencias: {e}")

    def save(self) -> None:
        """Guarda preferencias en disco."""
        try:
            os.makedirs(self._data_dir, exist_ok=True)
            with open(self._file_path, "w", encoding="utf-8") as f:
                json.dump(self._prefs, f, indent=2, ensure_ascii=False)
            log.debug("Preferencias guardadas")
        except Exception as e:
            log.error(f"Error guardando preferencias: {e}")

    # ─── Favorites ─────────────────────────────────────────────

    def set_favorite(self, category: str, name: str, value: Any) -> None:
        """Establece un favorito. Ej: set_favorite('app', 'editor', 'vscode')"""
        if category not in self._prefs["favorites"]:
            self._prefs["favorites"][category] = {}
        self._prefs["favorites"][category][name] = value

    def get_favorite(self, category: str, name: str, default: Any = None) -> Any:
        """Obtiene un favorito."""
        return self._prefs["favorites"].get(category, {}).get(name, default)

    # ─── Aliases ───────────────────────────────────────────────

    def set_alias(self, alias: str, command: str) -> None:
        """Registra un alias para un comando."""
        self._prefs["aliases"][alias.lower()] = command
        log.debug(f"Alias registrado: '{alias}' → '{command}'")

    def get_alias(self, alias: str) -> Optional[str]:
        """Obtiene el comando asociado a un alias."""
        return self._prefs["aliases"].get(alias.lower())

    def get_all_aliases(self) -> Dict[str, str]:
        """Obtiene todos los alias."""
        return dict(self._prefs["aliases"])

    # ─── Intent Corrections (Learning) ─────────────────────────

    def add_correction(self, command: str, wrong_intent: str, correct_intent: str) -> None:
        """
        Registra una corrección de intención para aprendizaje.
        Si el usuario dice "no, eso no es lo que pedí", registramos la corrección.
        """
        correction = {
            "command": command,
            "wrong_intent": wrong_intent,
            "correct_intent": correct_intent,
        }
        self._prefs["corrections"].append(correction)
        log.info(f"Corrección aprendida: '{command}' → {correct_intent} (era {wrong_intent})")

    def get_corrections(self) -> List[dict]:
        """Obtiene todas las correcciones registradas."""
        return list(self._prefs["corrections"])

    def find_correction(self, command: str) -> Optional[str]:
        """
        Busca si hay una corrección previa para un comando similar.
        Retorna el intent correcto si existe.
        """
        command_lower = command.lower()
        for correction in reversed(self._prefs["corrections"]):
            if correction["command"].lower() == command_lower:
                return correction["correct_intent"]
        return None

    # ─── Custom Preferences ────────────────────────────────────

    def set(self, key: str, value: Any) -> None:
        """Establece una preferencia personalizada."""
        self._prefs["custom"][key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Obtiene una preferencia personalizada."""
        return self._prefs["custom"].get(key, default)

    def delete(self, key: str) -> bool:
        """Elimina una preferencia personalizada."""
        if key in self._prefs["custom"]:
            del self._prefs["custom"][key]
            return True
        return False

    def get_summary(self) -> dict:
        """Resumen de preferencias."""
        return {
            "favorites": len(self._prefs.get("favorites", {})),
            "aliases": len(self._prefs.get("aliases", {})),
            "corrections": len(self._prefs.get("corrections", [])),
            "custom": len(self._prefs.get("custom", {})),
        }

    def __repr__(self) -> str:
        return f"<Preferences {self.get_summary()}>"
