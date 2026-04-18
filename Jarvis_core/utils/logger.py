"""
JARVIS — Sistema de Logging Profesional
========================================
Logging con rotación de archivos, formato rico, y soporte para modo debug.
Utiliza rich para output colorizado en terminal.
"""

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Optional

# Intentar importar rich para logging bonito en terminal
try:
    from rich.logging import RichHandler
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class JarvisLogger:
    """
    Sistema de logging centralizado para JARVIS.
    
    Características:
    - Rotación automática de archivos de log
    - Formato rico en terminal (con rich)
    - Modos: DEBUG, INFO, WARNING, ERROR, CRITICAL
    - Separación de logs por módulo
    - Timestamps ISO 8601
    """

    _instances: dict = {}
    _initialized: bool = False
    _log_dir: str = "logs"
    _log_file: str = "jarvis.log"
    _max_size_mb: int = 10
    _backup_count: int = 5
    _level: int = logging.INFO
    _debug_mode: bool = False

    @classmethod
    def initialize(
        cls,
        log_dir: str = "logs",
        log_file: str = "jarvis.log",
        max_size_mb: int = 10,
        backup_count: int = 5,
        level: str = "INFO",
        debug: bool = False,
    ) -> None:
        """
        Inicializa el sistema de logging globalmente.
        Debe llamarse una vez al inicio de la aplicación.
        """
        cls._log_dir = log_dir
        cls._log_file = log_file
        cls._max_size_mb = max_size_mb
        cls._backup_count = backup_count
        cls._debug_mode = debug
        cls._level = logging.DEBUG if debug else getattr(logging, level.upper(), logging.INFO)

        # Crear directorio de logs
        os.makedirs(log_dir, exist_ok=True)

        cls._initialized = True

    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """
        Obtiene o crea un logger para el módulo especificado.
        
        Args:
            name: Nombre del módulo (ej: 'core.engine', 'skills.open_app')
            
        Returns:
            Logger configurado
        """
        if name in cls._instances:
            return cls._instances[name]

        if not cls._initialized:
            cls.initialize()

        logger = logging.getLogger(f"jarvis.{name}")
        logger.setLevel(cls._level)
        logger.propagate = False

        # Evitar duplicar handlers
        if not logger.handlers:
            # Handler de archivo con rotación (captura TODO)
            log_path = os.path.join(cls._log_dir, cls._log_file)
            file_handler = RotatingFileHandler(
                log_path,
                maxBytes=cls._max_size_mb * 1024 * 1024,
                backupCount=cls._backup_count,
                encoding="utf-8",
            )
            file_handler.setLevel(cls._level)
            file_format = logging.Formatter(
                "%(asctime)s | %(name)-30s | %(levelname)-8s | %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
            file_handler.setFormatter(file_format)
            logger.addHandler(file_handler)

            # Handler de consola — solo WARNING+ en modo normal
            # para mantener la UI limpia. Debug mode muestra todo.
            console_level = cls._level if cls._debug_mode else logging.WARNING

            if RICH_AVAILABLE:
                console_handler = RichHandler(
                    level=console_level,
                    rich_tracebacks=True,
                    show_time=True,
                    show_path=cls._debug_mode,
                    markup=True,
                )
            else:
                console_handler = logging.StreamHandler(sys.stdout)
                console_format = logging.Formatter(
                    "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                    datefmt="%H:%M:%S",
                )
                console_handler.setFormatter(console_format)

            console_handler.setLevel(console_level)
            logger.addHandler(console_handler)

        cls._instances[name] = logger
        return logger

    @classmethod
    def set_level(cls, level: str) -> None:
        """Cambia el nivel de logging globalmente."""
        new_level = getattr(logging, level.upper(), logging.INFO)
        cls._level = new_level
        for logger in cls._instances.values():
            logger.setLevel(new_level)
            for handler in logger.handlers:
                handler.setLevel(new_level)

    @classmethod
    def shutdown(cls) -> None:
        """Cierra todos los loggers y libera recursos."""
        for logger in cls._instances.values():
            for handler in logger.handlers[:]:
                handler.close()
                logger.removeHandler(handler)
        cls._instances.clear()
        cls._initialized = False


# Atajo para obtener logger rápidamente
def get_logger(name: str) -> logging.Logger:
    """Atajo global para obtener un logger de JARVIS."""
    return JarvisLogger.get_logger(name)
