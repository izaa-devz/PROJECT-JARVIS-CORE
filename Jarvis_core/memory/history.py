"""
JARVIS — Historial de Comandos
================================
Registra y consulta el historial de comandos ejecutados.
"""

import json
import os
from typing import Any, Dict, List, Optional
from datetime import datetime
from utils.logger import get_logger

log = get_logger("memory.history")


class CommandRecord:
    """Registro individual de un comando ejecutado."""

    def __init__(
        self,
        command: str,
        intent: str = "",
        skill: str = "",
        result: str = "",
        success: bool = True,
        duration_ms: float = 0,
        entities: Optional[Dict] = None,
        timestamp: Optional[str] = None,
    ):
        self.command = command
        self.intent = intent
        self.skill = skill
        self.result = result
        self.success = success
        self.duration_ms = duration_ms
        self.entities = entities or {}
        self.timestamp = timestamp or datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "command": self.command,
            "intent": self.intent,
            "skill": self.skill,
            "result": self.result,
            "success": self.success,
            "duration_ms": self.duration_ms,
            "entities": self.entities,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CommandRecord":
        return cls(**data)


class History:
    """
    Gestor de historial de comandos.
    
    Almacena los últimos N comandos ejecutados con su resultado,
    skill utilizado, duración, etc. Persiste en JSON.
    """

    def __init__(self, data_dir: str = "data", max_entries: int = 1000):
        self._data_dir = data_dir
        self._max_entries = max_entries
        self._records: List[CommandRecord] = []
        self._file_path = os.path.join(data_dir, "history.json")

    def load(self) -> None:
        """Carga el historial desde disco."""
        if os.path.exists(self._file_path):
            try:
                with open(self._file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._records = [CommandRecord.from_dict(r) for r in data]
                log.debug(f"Historial cargado: {len(self._records)} registros")
            except Exception as e:
                log.error(f"Error cargando historial: {e}")
                self._records = []

    def save(self) -> None:
        """Guarda el historial en disco."""
        try:
            os.makedirs(self._data_dir, exist_ok=True)
            with open(self._file_path, "w", encoding="utf-8") as f:
                json.dump([r.to_dict() for r in self._records], f, indent=2, ensure_ascii=False)
            log.debug(f"Historial guardado: {len(self._records)} registros")
        except Exception as e:
            log.error(f"Error guardando historial: {e}")

    def add(self, record: CommandRecord) -> None:
        """Agrega un registro al historial."""
        self._records.append(record)
        # Limitar tamaño
        if len(self._records) > self._max_entries:
            self._records = self._records[-self._max_entries:]

    def get_recent(self, count: int = 10) -> List[CommandRecord]:
        """Obtiene los últimos N registros."""
        return self._records[-count:]

    def search(self, query: str) -> List[CommandRecord]:
        """Busca en el historial por texto del comando."""
        query_lower = query.lower()
        return [r for r in self._records if query_lower in r.command.lower()]

    def get_by_skill(self, skill_name: str) -> List[CommandRecord]:
        """Obtiene registros por nombre de skill."""
        return [r for r in self._records if r.skill == skill_name]

    def get_by_intent(self, intent: str) -> List[CommandRecord]:
        """Obtiene registros por intención."""
        return [r for r in self._records if r.intent == intent]

    def get_most_used_commands(self, limit: int = 10) -> List[dict]:
        """Obtiene los comandos más usados."""
        command_counts: Dict[str, int] = {}
        for r in self._records:
            key = r.intent or r.command[:50]
            command_counts[key] = command_counts.get(key, 0) + 1
        sorted_commands = sorted(command_counts.items(), key=lambda x: x[1], reverse=True)
        return [{"command": cmd, "count": count} for cmd, count in sorted_commands[:limit]]

    def get_stats(self) -> dict:
        """Obtiene estadísticas del historial."""
        if not self._records:
            return {"total": 0, "success_rate": 0, "avg_duration_ms": 0}

        total = len(self._records)
        successes = sum(1 for r in self._records if r.success)
        avg_duration = sum(r.duration_ms for r in self._records) / total

        return {
            "total": total,
            "success_rate": round(successes / total * 100, 1),
            "avg_duration_ms": round(avg_duration, 1),
            "first_command": self._records[0].timestamp if self._records else None,
            "last_command": self._records[-1].timestamp if self._records else None,
        }

    def clear(self) -> None:
        """Limpia todo el historial."""
        self._records.clear()
        self.save()

    @property
    def count(self) -> int:
        return len(self._records)

    def __repr__(self) -> str:
        return f"<History records={len(self._records)} max={self._max_entries}>"
