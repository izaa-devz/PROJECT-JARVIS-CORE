"""
JARVIS — Sistema de Eventos (Event Bus)
=========================================
Patrón pub/sub asíncrono para comunicación desacoplada entre módulos.
Soporta eventos tipados, prioridad de listeners, y wildcard matching.
"""

import asyncio
from typing import Any, Callable, Coroutine, Dict, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum
from utils.logger import get_logger

log = get_logger("core.event_bus")


class Priority(IntEnum):
    """Prioridades de listeners. Números más bajos se ejecutan primero."""
    CRITICAL = 0
    HIGH = 10
    NORMAL = 50
    LOW = 90
    MONITOR = 100  # Solo para observar, se ejecuta al final


@dataclass
class Event:
    """
    Representa un evento del sistema.
    
    Attributes:
        name: Nombre del evento (ej: 'command.received', 'skill.executed')
        data: Datos asociados al evento
        source: Módulo que emitió el evento
        timestamp: Cuándo ocurrió
        propagate: Si False, detiene la propagación a listeners restantes
    """
    name: str
    data: Any = None
    source: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    propagate: bool = True

    def stop_propagation(self) -> None:
        """Detiene la propagación del evento a listeners restantes."""
        self.propagate = False


@dataclass
class Listener:
    """Un listener registrado para un evento."""
    callback: Callable
    priority: Priority
    once: bool = False  # Si True, se elimina después de ejecutarse una vez
    _id: int = 0


class EventBus:
    """
    Bus de eventos asíncrono central.
    
    Permite comunicación desacoplada entre módulos del sistema.
    Soporta:
    - Eventos tipados con datos
    - Prioridad de listeners
    - Listeners de un solo uso (once)
    - Wildcard matching (ej: 'skill.*' captura 'skill.executed', 'skill.error')
    - Historial de eventos recientes
    """

    def __init__(self, history_size: int = 100):
        self._listeners: Dict[str, List[Listener]] = {}
        self._listener_counter: int = 0
        self._history: List[Event] = []
        self._history_size = history_size
        self._stats: Dict[str, int] = {}  # Conteo de eventos emitidos
        log.debug("Event Bus inicializado")

    def on(
        self,
        event_name: str,
        callback: Callable,
        priority: Priority = Priority.NORMAL,
        once: bool = False,
    ) -> int:
        """
        Registra un listener para un evento.
        
        Args:
            event_name: Nombre del evento (soporta wildcards: 'skill.*')
            callback: Función async o sync a ejecutar
            priority: Prioridad de ejecución
            once: Si True, se ejecuta una sola vez y se remueve
            
        Returns:
            ID del listener (para poder eliminarlo después)
        """
        self._listener_counter += 1
        listener = Listener(
            callback=callback,
            priority=priority,
            once=once,
            _id=self._listener_counter,
        )

        if event_name not in self._listeners:
            self._listeners[event_name] = []

        self._listeners[event_name].append(listener)
        # Mantener ordenados por prioridad
        self._listeners[event_name].sort(key=lambda l: l.priority)

        log.debug(f"Listener #{listener._id} registrado para '{event_name}' (prioridad={priority.name})")
        return listener._id

    def once(self, event_name: str, callback: Callable, priority: Priority = Priority.NORMAL) -> int:
        """Registra un listener que se ejecuta una sola vez."""
        return self.on(event_name, callback, priority, once=True)

    def off(self, listener_id: int) -> bool:
        """
        Elimina un listener por su ID.
        
        Returns:
            True si se encontró y eliminó, False si no existía
        """
        for event_name, listeners in self._listeners.items():
            for listener in listeners:
                if listener._id == listener_id:
                    listeners.remove(listener)
                    log.debug(f"Listener #{listener_id} eliminado de '{event_name}'")
                    return True
        return False

    def off_all(self, event_name: str) -> int:
        """Elimina todos los listeners de un evento. Retorna cuántos se eliminaron."""
        count = len(self._listeners.get(event_name, []))
        self._listeners.pop(event_name, None)
        return count

    async def emit(self, event: Event) -> None:
        """
        Emite un evento y ejecuta todos los listeners correspondientes.
        
        Los listeners se ejecutan en orden de prioridad.
        Si un listener llama event.stop_propagation(), los restantes no se ejecutan.
        """
        # Registrar en historial
        self._history.append(event)
        if len(self._history) > self._history_size:
            self._history.pop(0)

        # Estadísticas
        self._stats[event.name] = self._stats.get(event.name, 0) + 1

        # Recopilar listeners que coincidan (exacto + wildcards)
        matching_listeners: List[Listener] = []
        to_remove: List[tuple] = []

        for pattern, listeners in self._listeners.items():
            if self._matches(pattern, event.name):
                for listener in listeners:
                    matching_listeners.append(listener)
                    if listener.once:
                        to_remove.append((pattern, listener))

        # Ordenar todos por prioridad
        matching_listeners.sort(key=lambda l: l.priority)

        # Ejecutar
        for listener in matching_listeners:
            if not event.propagate:
                break
            try:
                if asyncio.iscoroutinefunction(listener.callback):
                    await listener.callback(event)
                else:
                    listener.callback(event)
            except Exception as e:
                log.error(f"Error en listener para '{event.name}': {e}", exc_info=True)

        # Limpiar listeners de un solo uso
        for pattern, listener in to_remove:
            if pattern in self._listeners and listener in self._listeners[pattern]:
                self._listeners[pattern].remove(listener)

    async def emit_simple(self, name: str, data: Any = None, source: str = "") -> None:
        """Atajo para emitir un evento sin crear el objeto Event manualmente."""
        await self.emit(Event(name=name, data=data, source=source))

    def _matches(self, pattern: str, event_name: str) -> bool:
        """
        Verifica si un patrón coincide con un nombre de evento.
        Soporta wildcard '*' al final: 'skill.*' coincide con 'skill.executed'
        """
        if pattern == event_name:
            return True
        if pattern.endswith(".*"):
            prefix = pattern[:-2]
            return event_name.startswith(prefix + ".")
        if pattern == "*":
            return True
        return False

    @property
    def history(self) -> List[Event]:
        """Historial de eventos recientes."""
        return list(self._history)

    @property
    def stats(self) -> Dict[str, int]:
        """Estadísticas de eventos emitidos."""
        return dict(self._stats)

    @property
    def registered_events(self) -> Set[str]:
        """Conjunto de nombres de eventos con listeners registrados."""
        return set(self._listeners.keys())

    def clear(self) -> None:
        """Limpia todos los listeners y el historial."""
        self._listeners.clear()
        self._history.clear()
        self._stats.clear()
        log.debug("Event Bus limpiado completamente")

    def __repr__(self) -> str:
        total = sum(len(v) for v in self._listeners.values())
        return f"<EventBus listeners={total} events={len(self._listeners)} history={len(self._history)}>"
