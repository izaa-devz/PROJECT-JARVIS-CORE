"""
JARVIS — Memory Manager
=========================
Gestor central de memoria que coordina historial y preferencias.
Implementa auto-guardado periódico.
"""

import asyncio
from typing import Optional
from memory.history import History, CommandRecord
from memory.preferences import Preferences
from utils.logger import get_logger

log = get_logger("memory.manager")


class MemoryManager:
    """
    Gestor central de memoria persistente.
    
    Coordina:
    - Historial de comandos
    - Preferencias del usuario
    - Auto-guardado periódico
    """

    def __init__(self, data_dir: str = "data", max_history: int = 1000, auto_save_interval: int = 60):
        self._data_dir = data_dir
        self._auto_save_interval = auto_save_interval
        self._auto_save_task: Optional[asyncio.Task] = None

        # Subsistemas
        self.history = History(data_dir=data_dir, max_entries=max_history)
        self.preferences = Preferences(data_dir=data_dir)

    async def initialize(self) -> None:
        """Inicializa la memoria: carga datos desde disco."""
        self.history.load()
        self.preferences.load()
        log.info(
            f"Memoria inicializada — Historial: {self.history.count} registros, "
            f"Preferencias: {self.preferences.get_summary()}"
        )

    async def start_auto_save(self) -> None:
        """Inicia el ciclo de auto-guardado periódico."""
        if self._auto_save_task is not None:
            return

        async def _auto_save_loop():
            while True:
                await asyncio.sleep(self._auto_save_interval)
                try:
                    self.save_all()
                    log.debug("Auto-guardado completado")
                except Exception as e:
                    log.error(f"Error en auto-guardado: {e}")

        self._auto_save_task = asyncio.create_task(_auto_save_loop())
        log.debug(f"Auto-guardado configurado cada {self._auto_save_interval}s")

    async def stop_auto_save(self) -> None:
        """Detiene el auto-guardado."""
        if self._auto_save_task:
            self._auto_save_task.cancel()
            try:
                await self._auto_save_task
            except asyncio.CancelledError:
                pass
            self._auto_save_task = None

    def record_command(
        self,
        command: str,
        intent: str = "",
        skill: str = "",
        result: str = "",
        success: bool = True,
        duration_ms: float = 0,
        entities: dict = None,
    ) -> None:
        """Registra un comando en el historial."""
        record = CommandRecord(
            command=command,
            intent=intent,
            skill=skill,
            result=result,
            success=success,
            duration_ms=duration_ms,
            entities=entities,
        )
        self.history.add(record)

    def save_all(self) -> None:
        """Guarda todo en disco."""
        self.history.save()
        self.preferences.save()

    async def shutdown(self) -> None:
        """Cierra la memoria de forma limpia."""
        await self.stop_auto_save()
        self.save_all()
        log.info("Memoria guardada y cerrada")

    def get_summary(self) -> dict:
        """Resumen completo de la memoria."""
        return {
            "history": self.history.get_stats(),
            "preferences": self.preferences.get_summary(),
        }

    def __repr__(self) -> str:
        return f"<MemoryManager history={self.history.count} prefs={self.preferences.get_summary()}>"
