"""
JARVIS — Cargador de Configuración
====================================
Carga, valida y proporciona acceso a la configuración del sistema
desde config.json con valores por defecto.
"""

import os
import json
from typing import Any, Optional
from utils.logger import get_logger

log = get_logger("utils.config")


# Valores por defecto completos (fallback si falta algo en config.json)
DEFAULT_CONFIG = {
    "jarvis": {
        "name": "JARVIS",
        "version": "1.0.0",
        "language": "es",
        "debug": False,
        "log_level": "INFO",
        "log_file": "logs/jarvis.log",
        "max_log_size_mb": 10,
        "log_backup_count": 5,
    },
    "interaction": {
        "mode": "text",
        "wake_word": "hey jarvis",
        "prompt_symbol": "❯",
        "greeting": True,
        "farewell": True,
        "confirm_dangerous_actions": True,
    },
    "voice": {
        "enabled": False,
        "tts_engine": "pyttsx3",
        "tts_rate": 180,
        "tts_volume": 0.9,
        "tts_voice_index": 0,
        "stt_engine": "google",
        "stt_language": "es-ES",
        "stt_timeout": 5,
        "stt_phrase_limit": 10,
        "wake_word_enabled": False,
        "wake_word_timeout": 2,
    },
    "nlp": {
        "spacy_model": "es_core_news_md",
        "fuzzy_threshold": 70,
        "confidence_threshold": 0.5,
        "use_spacy": True,
        "fallback_to_rules": True,
    },
    "memory": {
        "enabled": True,
        "data_dir": "data",
        "history_max_entries": 1000,
        "auto_save_interval_seconds": 60,
        "learn_from_corrections": True,
    },
    "task_engine": {
        "max_concurrent_tasks": 10,
        "task_timeout_seconds": 300,
        "enable_scheduler": True,
        "scheduler_check_interval": 1,
    },
    "skills": {
        "skills_dir": "skills",
        "auto_discover": True,
        "disabled_skills": [],
        "apps_registry": {},
        "default_browser": "chrome",
        "default_search_engine": "google",
        "screenshot_dir": "screenshots",
        "files_default_dir": ".",
    },
    "ui": {
        "theme": "hacker",
        "colors": {
            "primary": "cyan",
            "secondary": "green",
            "accent": "magenta",
            "error": "red",
            "warning": "yellow",
            "success": "green",
            "info": "blue",
        },
        "show_banner": True,
        "show_timestamps": True,
        "show_skill_name": False,
        "animation_speed": "normal",
    },
}


class ConfigLoader:
    """
    Cargador de configuración singleton.
    
    Lee config.json y combina con valores por defecto.
    Proporciona acceso tipo dot-notation a la configuración.
    """

    _instance: Optional["ConfigLoader"] = None
    _config: dict = {}
    _config_path: str = ""

    def __new__(cls) -> "ConfigLoader":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load(self, config_path: str = "config.json") -> dict:
        """
        Carga la configuración desde archivo JSON.
        
        Args:
            config_path: Ruta al archivo de configuración
            
        Returns:
            Diccionario de configuración completo
        """
        self._config_path = config_path
        self._config = self._deep_merge(DEFAULT_CONFIG, {})

        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    user_config = json.load(f)
                self._config = self._deep_merge(DEFAULT_CONFIG, user_config)
                log.info(f"Configuración cargada desde {config_path}")
            except json.JSONDecodeError as e:
                log.error(f"Error al parsear {config_path}: {e}. Usando valores por defecto.")
            except Exception as e:
                log.error(f"Error al cargar configuración: {e}. Usando valores por defecto.")
        else:
            log.warning(f"No se encontró {config_path}. Usando valores por defecto.")
            self._save_default(config_path)

        return self._config

    def _deep_merge(self, base: dict, override: dict) -> dict:
        """Merge profundo de diccionarios. Override tiene prioridad."""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def _save_default(self, path: str) -> None:
        """Guarda la configuración por defecto si no existe el archivo."""
        try:
            os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_CONFIG, f, indent=4, ensure_ascii=False)
            log.info(f"Configuración por defecto guardada en {path}")
        except Exception as e:
            log.error(f"No se pudo guardar configuración por defecto: {e}")

    def get(self, *keys: str, default: Any = None) -> Any:
        """
        Obtiene un valor de configuración usando claves encadenadas.
        
        Ejemplo:
            config.get("voice", "tts_rate")  -> 180
            config.get("jarvis", "name")     -> "JARVIS"
        """
        result = self._config
        for key in keys:
            if isinstance(result, dict) and key in result:
                result = result[key]
            else:
                return default
        return result

    def set(self, *keys_and_value: Any) -> None:
        """
        Establece un valor en la configuración.
        El último argumento es el valor, los anteriores son las claves.
        
        Ejemplo:
            config.set("voice", "enabled", True)
        """
        if len(keys_and_value) < 2:
            return

        *keys, value = keys_and_value
        target = self._config
        for key in keys[:-1]:
            if key not in target or not isinstance(target[key], dict):
                target[key] = {}
            target = target[key]
        target[keys[-1]] = value

    def save(self) -> None:
        """Guarda la configuración actual en disco."""
        try:
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=4, ensure_ascii=False)
            log.debug("Configuración guardada en disco")
        except Exception as e:
            log.error(f"Error al guardar configuración: {e}")

    @property
    def config(self) -> dict:
        """Acceso directo al diccionario de configuración."""
        return self._config

    def __repr__(self) -> str:
        return f"<ConfigLoader path='{self._config_path}' keys={list(self._config.keys())}>"


# Singleton global
config = ConfigLoader()
