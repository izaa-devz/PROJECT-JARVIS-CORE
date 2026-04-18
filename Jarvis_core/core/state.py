"""
JARVIS — Gestor de Estado Global
==================================
Singleton thread-safe para almacenar y gestionar el estado del sistema.
"""

import asyncio
from typing import Any, Dict, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from utils.logger import get_logger

log = get_logger("core.state")


class SystemStatus(Enum):
    """Estados posibles del sistema."""
    INITIALIZING = auto()
    READY = auto()
    PROCESSING = auto()
    LISTENING = auto()
    SPEAKING = auto()
    ERROR = auto()
    SHUTTING_DOWN = auto()


class InteractionMode(Enum):
    """Modos de interacción."""
    TEXT = "text"
    VOICE = "voice"
    HYBRID = "hybrid"


@dataclass
class SessionInfo:
    """Información de la sesión actual."""
    session_id: str = ""
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    commands_processed: int = 0
    errors_count: int = 0
    skills_used: Dict[str, int] = field(default_factory=dict)
    last_command: str = ""
    last_response: str = ""
    last_activity: str = field(default_factory=lambda: datetime.now().isoformat())


class StateManager:
    """
    Gestor de estado global del sistema JARVIS.
    
    Mantiene:
    - Estado actual del sistema (ready, processing, etc.)
    - Modo de interacción (text, voice, hybrid)
    - Info de sesión
    - Datos arbitrarios de estado compartido entre módulos
    - Locks para acceso thread-safe
    """

    _instance: Optional["StateManager"] = None

    def __new__(cls) -> "StateManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        self._status: SystemStatus = SystemStatus.INITIALIZING
        self._mode: InteractionMode = InteractionMode.TEXT
        self._session: SessionInfo = SessionInfo()
        self._data: Dict[str, Any] = {}
        self._lock = asyncio.Lock()
        self._active_skills: Set[str] = set()
        self._loaded_skills: Set[str] = set()

        log.debug("State Manager inicializado")

    # ─── Status ────────────────────────────────────────────────

    @property
    def status(self) -> SystemStatus:
        """Estado actual del sistema."""
        return self._status

    async def set_status(self, status: SystemStatus) -> None:
        """Cambia el estado del sistema de forma thread-safe."""
        async with self._lock:
            old = self._status
            self._status = status
            if old != status:
                log.debug(f"Estado: {old.name} → {status.name}")

    @property
    def is_ready(self) -> bool:
        return self._status == SystemStatus.READY

    @property
    def is_processing(self) -> bool:
        return self._status == SystemStatus.PROCESSING

    # ─── Interaction Mode ──────────────────────────────────────

    @property
    def mode(self) -> InteractionMode:
        """Modo de interacción actual."""
        return self._mode

    async def set_mode(self, mode: InteractionMode) -> None:
        """Cambia el modo de interacción."""
        async with self._lock:
            old = self._mode
            self._mode = mode
            if old != mode:
                log.info(f"Modo: {old.value} → {mode.value}")

    # ─── Session ───────────────────────────────────────────────

    @property
    def session(self) -> SessionInfo:
        """Información de la sesión actual."""
        return self._session

    async def record_command(self, command: str) -> None:
        """Registra un comando procesado en la sesión."""
        async with self._lock:
            self._session.commands_processed += 1
            self._session.last_command = command
            self._session.last_activity = datetime.now().isoformat()

    async def record_response(self, response: str) -> None:
        """Registra una respuesta."""
        async with self._lock:
            self._session.last_response = response

    async def record_error(self) -> None:
        """Registra un error en la sesión."""
        async with self._lock:
            self._session.errors_count += 1

    async def record_skill_usage(self, skill_name: str) -> None:
        """Registra el uso de un skill."""
        async with self._lock:
            self._session.skills_used[skill_name] = self._session.skills_used.get(skill_name, 0) + 1

    # ─── Skills Tracking ───────────────────────────────────────

    @property
    def loaded_skills(self) -> Set[str]:
        """Skills cargados en el sistema."""
        return self._loaded_skills.copy()

    def register_skill(self, skill_name: str) -> None:
        """Registra un skill como cargado."""
        self._loaded_skills.add(skill_name)

    @property
    def active_skills(self) -> Set[str]:
        """Skills actualmente en ejecución."""
        return self._active_skills.copy()

    async def skill_started(self, skill_name: str) -> None:
        """Marca un skill como en ejecución."""
        async with self._lock:
            self._active_skills.add(skill_name)

    async def skill_finished(self, skill_name: str) -> None:
        """Marca un skill como finalizado."""
        async with self._lock:
            self._active_skills.discard(skill_name)

    # ─── Shared Data ──────────────────────────────────────────

    async def get(self, key: str, default: Any = None) -> Any:
        """Obtiene un dato del estado compartido."""
        async with self._lock:
            return self._data.get(key, default)

    async def set(self, key: str, value: Any) -> None:
        """Establece un dato en el estado compartido."""
        async with self._lock:
            self._data[key] = value

    async def delete(self, key: str) -> bool:
        """Elimina un dato del estado compartido."""
        async with self._lock:
            if key in self._data:
                del self._data[key]
                return True
            return False

    # ─── Reset ─────────────────────────────────────────────────

    async def reset_session(self) -> None:
        """Reinicia la sesión actual."""
        async with self._lock:
            self._session = SessionInfo()
            log.info("Sesión reiniciada")

    def get_summary(self) -> dict:
        """Retorna resumen del estado actual."""
        return {
            "status": self._status.name,
            "mode": self._mode.value,
            "session": {
                "commands_processed": self._session.commands_processed,
                "errors": self._session.errors_count,
                "started_at": self._session.started_at,
                "last_activity": self._session.last_activity,
                "skills_used": dict(self._session.skills_used),
            },
            "loaded_skills": len(self._loaded_skills),
            "active_skills": list(self._active_skills),
        }

    def __repr__(self) -> str:
        return (
            f"<StateManager status={self._status.name} mode={self._mode.value} "
            f"commands={self._session.commands_processed}>"
        )
