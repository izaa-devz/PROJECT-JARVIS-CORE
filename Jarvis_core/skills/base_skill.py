"""
JARVIS — Base Skill (Clase Abstracta)
=======================================
Define el contrato que todo skill debe implementar.
Usa Protocol + ABC para máxima flexibilidad y type-safety.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum, auto


class SkillCategory(Enum):
    """Categorías de skills."""
    SYSTEM = auto()       # Control del sistema
    APP = auto()          # Gestión de aplicaciones
    FILE = auto()         # Gestión de archivos
    BROWSER = auto()      # Navegador / web
    INFO = auto()         # Información del sistema
    MEDIA = auto()        # Multimedia
    CONVERSATION = auto() # Conversacional
    UTILITY = auto()      # Utilidades


@dataclass
class SkillContext:
    """
    Contexto pasado a un skill cuando se ejecuta.
    Contiene toda la información necesaria para ejecutar la acción.
    """
    raw_command: str                           # Texto original del usuario
    intent: str = ""                           # Intención clasificada
    action: str = ""                           # Sub-acción específica
    entities: Dict[str, Any] = field(default_factory=dict)  # Entidades extraídas
    confidence: float = 0.0                    # Confianza de la clasificación
    parameters: Dict[str, Any] = field(default_factory=dict)  # Params adicionales
    session_data: Dict[str, Any] = field(default_factory=dict)  # Datos de sesión


@dataclass
class SkillResult:
    """
    Resultado devuelto por un skill después de ejecutarse.
    """
    success: bool = True
    message: str = ""                          # Mensaje para mostrar al usuario
    speak: bool = True                         # Si debe hablar la respuesta
    data: Any = None                           # Datos estructurados adicionales
    follow_up: Optional[str] = None            # Comando de seguimiento
    error: Optional[str] = None                # Mensaje de error si falló

    @classmethod
    def ok(cls, message: str = "", data: Any = None, speak: bool = True) -> "SkillResult":
        """Crea un resultado exitoso."""
        return cls(success=True, message=message, data=data, speak=speak)

    @classmethod
    def fail(cls, error: str, message: str = "") -> "SkillResult":
        """Crea un resultado fallido."""
        display_msg = message or f"Error: {error}"
        return cls(success=False, message=display_msg, error=error, speak=True)


class BaseSkill(ABC):
    """
    Clase base abstracta para todos los skills de JARVIS.
    
    Cada skill debe implementar:
    - name: Nombre único del skill
    - description: Descripción breve
    - intents: Lista de intenciones que puede manejar
    - patterns: Palabras clave/patrones para matched rápido
    - execute(): Método principal de ejecución
    
    Opcionalmente puede sobreescribir:
    - can_handle(): Lógica personalizada de matching
    - setup(): Inicialización al cargar
    - teardown(): Limpieza al descargar
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Nombre único del skill."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Descripción breve del skill."""
        ...

    @property
    @abstractmethod
    def intents(self) -> List[str]:
        """
        Lista de intenciones que este skill puede manejar.
        Ejemplo: ['open_app', 'launch_app', 'start_app']
        """
        ...

    @property
    def category(self) -> SkillCategory:
        """Categoría del skill. Por defecto UTILITY."""
        return SkillCategory.UTILITY

    @property
    def patterns(self) -> List[str]:
        """
        Palabras clave o patrones para matching rápido basado en reglas.
        Ejemplo: ['abrir', 'abre', 'ejecutar', 'iniciar', 'lanzar']
        """
        return []

    @property
    def examples(self) -> List[str]:
        """Ejemplos de comandos que este skill puede manejar."""
        return []

    @property
    def priority(self) -> int:
        """
        Prioridad del skill (0 = más alta).
        Usado para resolver conflictos cuando múltiples skills pueden manejar un intent.
        """
        return 50

    @property
    def is_dangerous(self) -> bool:
        """Si True, requiere confirmación antes de ejecutar."""
        return False

    def can_handle(self, context: SkillContext) -> bool :
        """
        Determina si este skill puede manejar el contexto dado.
        
        La implementación por defecto verifica si el intent está en self.intents.
        Sobreescribir para lógica más compleja.
        """
        return context.intent in self.intents

    async def setup(self) -> None:
        """
        Inicialización del skill al cargarse.
        Sobreescribir si el skill necesita preparación (ej: conectar a DB).
        """
        pass

    @abstractmethod
    async def execute(self, context: SkillContext) -> SkillResult:
        """
        Ejecuta la acción del skill.
        
        Args:
            context: Contexto con toda la información del comando
            
        Returns:
            SkillResult con el resultado de la ejecución
        """
        ...

    async def teardown(self) -> None:
        """
        Limpieza al descargar el skill.
        Sobreescribir si necesita liberar recursos.
        """
        pass

    def __repr__(self) -> str:
        return f"<Skill '{self.name}' intents={self.intents}>"
