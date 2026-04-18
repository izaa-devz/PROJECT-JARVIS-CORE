"""
JARVIS — Background Task Runner
==================================
Ejecuta tareas pesadas en hilos/procesos separados sin bloquear el main loop.
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from typing import Any, Callable, Optional
from utils.logger import get_logger

log = get_logger("task_engine.background")


class BackgroundRunner:
    """
    Ejecuta funciones bloqueantes en background sin afectar el event loop.
    
    Usa ThreadPoolExecutor para I/O bound y ProcessPoolExecutor para CPU bound.
    """

    def __init__(self, max_threads: int = 5, max_processes: int = 2):
        self._thread_pool = ThreadPoolExecutor(max_workers=max_threads, thread_name_prefix="jarvis-bg")
        self._process_pool: Optional[ProcessPoolExecutor] = None
        self._max_processes = max_processes

    async def run_in_thread(self, func: Callable, *args: Any) -> Any:
        """
        Ejecuta una función bloqueante en un hilo separado.
        Ideal para: I/O, llamadas al sistema, pyttsx3, etc.
        """
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._thread_pool, func, *args)

    async def run_in_process(self, func: Callable, *args: Any) -> Any:
        """
        Ejecuta una función en un proceso separado.
        Ideal para: cálculos pesados, procesamiento de imagen, etc.
        """
        if self._process_pool is None:
            self._process_pool = ProcessPoolExecutor(max_workers=self._max_processes)
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._process_pool, func, *args)

    def shutdown(self) -> None:
        """Cierra los pools de ejecución."""
        self._thread_pool.shutdown(wait=False)
        if self._process_pool:
            self._process_pool.shutdown(wait=False)
        log.debug("Background Runner cerrado")

    def __repr__(self) -> str:
        return f"<BackgroundRunner threads={self._thread_pool._max_workers}>"
