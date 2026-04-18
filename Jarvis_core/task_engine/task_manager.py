"""
JARVIS — Task Manager
=======================
Gestor de tareas con cola de prioridad, ejecución inmediata,
diferida y en background con tracking de estado.
"""

import asyncio
import uuid
import time
from typing import Any, Callable, Coroutine, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum, auto
from utils.logger import get_logger

log = get_logger("task_engine.manager")


class TaskStatus(Enum):
    """Estados posibles de una tarea."""
    PENDING = auto()
    RUNNING = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()
    TIMEOUT = auto()


class TaskPriority(Enum):
    """Niveles de prioridad."""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


@dataclass
class Task:
    """Representa una tarea a ejecutar."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    coroutine: Optional[Callable] = None
    args: tuple = ()
    kwargs: dict = field(default_factory=dict)
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    timeout: Optional[float] = None

    @property
    def duration(self) -> Optional[float]:
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None

    @property
    def duration_ms(self) -> float:
        d = self.duration
        return d * 1000 if d else 0


class TaskManager:
    """
    Gestor de tareas asíncronas.
    
    Soporta:
    - Cola de tareas con prioridad
    - Ejecución inmediata
    - Tareas en background
    - Timeout por tarea
    - Tracking de estado
    - Límite de concurrencia
    """

    def __init__(self, max_concurrent: int = 10, default_timeout: float = 300):
        self._max_concurrent = max_concurrent
        self._default_timeout = default_timeout
        self._tasks: Dict[str, Task] = {}
        self._running: Dict[str, asyncio.Task] = {}
        self._semaphore = asyncio.Semaphore(max_concurrent)

    async def submit(
        self,
        coro_func: Callable,
        *args,
        name: str = "",
        priority: TaskPriority = TaskPriority.NORMAL,
        timeout: Optional[float] = None,
        **kwargs,
    ) -> Task:
        """
        Envía una tarea para ejecución inmediata.
        
        Args:
            coro_func: Función async a ejecutar
            name: Nombre descriptivo de la tarea
            priority: Prioridad
            timeout: Timeout en segundos (None = default)
            
        Returns:
            Task con el resultado
        """
        task = Task(
            name=name or coro_func.__name__,
            coroutine=coro_func,
            args=args,
            kwargs=kwargs,
            priority=priority,
            timeout=timeout or self._default_timeout,
        )

        self._tasks[task.id] = task
        await self._execute(task)
        return task

    async def submit_background(
        self,
        coro_func: Callable,
        *args,
        name: str = "",
        timeout: Optional[float] = None,
        **kwargs,
    ) -> str:
        """
        Envía una tarea para ejecución en background.
        Retorna inmediatamente con el task_id.
        """
        task = Task(
            name=name or coro_func.__name__,
            coroutine=coro_func,
            args=args,
            kwargs=kwargs,
            priority=TaskPriority.BACKGROUND,
            timeout=timeout or self._default_timeout,
        )

        self._tasks[task.id] = task

        async_task = asyncio.create_task(self._execute(task))
        self._running[task.id] = async_task

        log.info(f"Tarea background iniciada: [{task.id}] {task.name}")
        return task.id

    async def _execute(self, task: Task) -> None:
        """Ejecuta una tarea con semáforo de concurrencia."""
        async with self._semaphore:
            task.status = TaskStatus.RUNNING
            task.started_at = time.time()

            try:
                if task.timeout:
                    task.result = await asyncio.wait_for(
                        task.coroutine(*task.args, **task.kwargs),
                        timeout=task.timeout,
                    )
                else:
                    task.result = await task.coroutine(*task.args, **task.kwargs)

                task.status = TaskStatus.COMPLETED
                log.debug(f"Tarea completada: [{task.id}] {task.name} ({task.duration_ms:.0f}ms)")

            except asyncio.TimeoutError:
                task.status = TaskStatus.TIMEOUT
                task.error = f"Timeout después de {task.timeout}s"
                log.warning(f"Tarea timeout: [{task.id}] {task.name}")

            except asyncio.CancelledError:
                task.status = TaskStatus.CANCELLED
                log.info(f"Tarea cancelada: [{task.id}] {task.name}")

            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error = str(e)
                log.error(f"Tarea fallida: [{task.id}] {task.name}: {e}")

            finally:
                task.completed_at = time.time()
                self._running.pop(task.id, None)

    async def cancel(self, task_id: str) -> bool:
        """Cancela una tarea en ejecución."""
        if task_id in self._running:
            self._running[task_id].cancel()
            return True
        return False

    def get_task(self, task_id: str) -> Optional[Task]:
        """Obtiene una tarea por su ID."""
        return self._tasks.get(task_id)

    def get_running(self) -> List[Task]:
        """Obtiene las tareas actualmente en ejecución."""
        return [t for t in self._tasks.values() if t.status == TaskStatus.RUNNING]

    def get_stats(self) -> dict:
        """Estadísticas de tareas."""
        statuses = {}
        for task in self._tasks.values():
            name = task.status.name
            statuses[name] = statuses.get(name, 0) + 1
        return {
            "total": len(self._tasks),
            "running": len(self._running),
            "statuses": statuses,
        }

    async def shutdown(self) -> None:
        """Cancela todas las tareas en ejecución."""
        for task_id in list(self._running.keys()):
            await self.cancel(task_id)
        log.info("Task Manager cerrado")

    def __repr__(self) -> str:
        return f"<TaskManager total={len(self._tasks)} running={len(self._running)}>"
