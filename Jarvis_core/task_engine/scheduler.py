"""
JARVIS — Scheduler (Programador de Tareas)
=============================================
Programa tareas para ejecutarse en el futuro.
Soporta: ejecutar en X segundos, a una hora específica, repetitivas.
"""

import asyncio
import time
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from utils.logger import get_logger

log = get_logger("task_engine.scheduler")


@dataclass
class ScheduledTask:
    """Tarea programada."""
    id: str
    name: str
    callback: Callable
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)
    execute_at: float = 0  # timestamp
    repeat_interval: Optional[float] = None  # segundos entre repeticiones
    max_repeats: int = 0  # 0 = infinito
    executions: int = 0
    active: bool = True
    last_executed: Optional[float] = None


class Scheduler:
    """
    Programador de tareas basado en asyncio.
    
    Permite programar:
    - Ejecución diferida (en X segundos)
    - Ejecución a hora específica
    - Tareas repetitivas
    """

    def __init__(self, check_interval: float = 1.0):
        self._tasks: Dict[str, ScheduledTask] = {}
        self._check_interval = check_interval
        self._task_counter = 0
        self._runner: Optional[asyncio.Task] = None
        self._running = False

    async def start(self) -> None:
        """Inicia el loop de verificación del scheduler."""
        if self._running:
            return
        self._running = True
        self._runner = asyncio.create_task(self._scheduler_loop())
        log.info("Scheduler iniciado")

    async def stop(self) -> None:
        """Detiene el scheduler."""
        self._running = False
        if self._runner:
            self._runner.cancel()
            try:
                await self._runner
            except asyncio.CancelledError:
                pass
        log.info("Scheduler detenido")

    def schedule_delay(
        self,
        callback: Callable,
        delay_seconds: float,
        name: str = "",
        *args,
        **kwargs,
    ) -> str:
        """
        Programa una tarea para ejecutarse después de N segundos.
        
        Returns:
            ID de la tarea programada
        """
        task_id = self._generate_id()
        task = ScheduledTask(
            id=task_id,
            name=name or f"delayed_{task_id}",
            callback=callback,
            args=args,
            kwargs=kwargs,
            execute_at=time.time() + delay_seconds,
        )
        self._tasks[task_id] = task
        log.info(f"Tarea programada [{task_id}] '{task.name}' en {delay_seconds}s")
        return task_id

    def schedule_at(
        self,
        callback: Callable,
        execute_time: datetime,
        name: str = "",
        *args,
        **kwargs,
    ) -> str:
        """
        Programa una tarea para una hora específica.
        
        Returns:
            ID de la tarea programada
        """
        task_id = self._generate_id()
        task = ScheduledTask(
            id=task_id,
            name=name or f"scheduled_{task_id}",
            callback=callback,
            args=args,
            kwargs=kwargs,
            execute_at=execute_time.timestamp(),
        )
        self._tasks[task_id] = task
        log.info(f"Tarea programada [{task_id}] '{task.name}' para {execute_time.isoformat()}")
        return task_id

    def schedule_repeat(
        self,
        callback: Callable,
        interval_seconds: float,
        name: str = "",
        max_repeats: int = 0,
        *args,
        **kwargs,
    ) -> str:
        """
        Programa una tarea repetitiva.
        
        Args:
            interval_seconds: Intervalo entre ejecuciones
            max_repeats: Máximo de repeticiones (0 = infinito)
        """
        task_id = self._generate_id()
        task = ScheduledTask(
            id=task_id,
            name=name or f"repeat_{task_id}",
            callback=callback,
            args=args,
            kwargs=kwargs,
            execute_at=time.time() + interval_seconds,
            repeat_interval=interval_seconds,
            max_repeats=max_repeats,
        )
        self._tasks[task_id] = task
        log.info(f"Tarea repetitiva [{task_id}] '{task.name}' cada {interval_seconds}s")
        return task_id

    def cancel(self, task_id: str) -> bool:
        """Cancela una tarea programada."""
        if task_id in self._tasks:
            self._tasks[task_id].active = False
            del self._tasks[task_id]
            log.info(f"Tarea [{task_id}] cancelada")
            return True
        return False

    def get_pending(self) -> List[ScheduledTask]:
        """Obtiene todas las tareas pendientes."""
        return [t for t in self._tasks.values() if t.active]

    async def _scheduler_loop(self) -> None:
        """Loop principal del scheduler."""
        while self._running:
            now = time.time()
            to_execute = []
            to_remove = []

            for task_id, task in self._tasks.items():
                if not task.active:
                    to_remove.append(task_id)
                    continue
                if now >= task.execute_at:
                    to_execute.append(task)

            # Ejecutar tareas listas
            for task in to_execute:
                try:
                    if asyncio.iscoroutinefunction(task.callback):
                        await task.callback(*task.args, **task.kwargs)
                    else:
                        task.callback(*task.args, **task.kwargs)
                    task.executions += 1
                    task.last_executed = time.time()
                    log.debug(f"Tarea [{task.id}] '{task.name}' ejecutada (#{task.executions})")
                except Exception as e:
                    log.error(f"Error en tarea [{task.id}] '{task.name}': {e}")

                # ¿Repetir?
                if task.repeat_interval and (task.max_repeats == 0 or task.executions < task.max_repeats):
                    task.execute_at = time.time() + task.repeat_interval
                else:
                    to_remove.append(task.id)

            # Limpiar tareas completadas
            for task_id in to_remove:
                self._tasks.pop(task_id, None)

            await asyncio.sleep(self._check_interval)

    def _generate_id(self) -> str:
        self._task_counter += 1
        return f"sched_{self._task_counter:04d}"

    def __repr__(self) -> str:
        return f"<Scheduler tasks={len(self._tasks)} running={self._running}>"
