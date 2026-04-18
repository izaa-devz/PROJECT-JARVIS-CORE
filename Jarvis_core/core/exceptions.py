"""
JARVIS — Excepciones Personalizadas
=====================================
Jerarquía de excepciones para manejo de errores profesional.
"""


class JarvisError(Exception):
    """Excepción base de JARVIS. Todas las excepciones del sistema heredan de esta."""

    def __init__(self, message: str = "Error interno de JARVIS", code: str = "JARVIS_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


# ─── Core Errors ──────────────────────────────────────────────

class EngineError(JarvisError):
    """Error en el motor principal."""
    def __init__(self, message: str = "Error en el motor de JARVIS"):
        super().__init__(message, "ENGINE_ERROR")


class StateError(JarvisError):
    """Error en el manejo de estado."""
    def __init__(self, message: str = "Error de estado"):
        super().__init__(message, "STATE_ERROR")


class ShutdownRequested(JarvisError):
    """Señal de apagado del sistema (no es un error, es una señal de control)."""
    def __init__(self):
        super().__init__("Apagado solicitado", "SHUTDOWN")


# ─── Router Errors ────────────────────────────────────────────

class RouterError(JarvisError):
    """Error en el router de comandos."""
    def __init__(self, message: str = "Error en el router de comandos"):
        super().__init__(message, "ROUTER_ERROR")


class IntentNotFoundError(RouterError):
    """No se pudo determinar la intención del comando."""
    def __init__(self, command: str = ""):
        msg = f"No pude entender el comando: '{command}'" if command else "Intención no reconocida"
        super().__init__(msg)
        self.code = "INTENT_NOT_FOUND"


class AmbiguousIntentError(RouterError):
    """Múltiples intenciones posibles para un comando."""
    def __init__(self, command: str = "", candidates: list = None):
        self.candidates = candidates or []
        msg = f"Comando ambiguo: '{command}'. Candidatos: {self.candidates}"
        super().__init__(msg)
        self.code = "AMBIGUOUS_INTENT"


# ─── Skill Errors ─────────────────────────────────────────────

class SkillError(JarvisError):
    """Error en la ejecución de un skill."""
    def __init__(self, skill_name: str = "", message: str = "Error en skill"):
        self.skill_name = skill_name
        full_msg = f"[{skill_name}] {message}" if skill_name else message
        super().__init__(full_msg, "SKILL_ERROR")


class SkillNotFoundError(SkillError):
    """Skill no encontrado en el registro."""
    def __init__(self, skill_name: str = ""):
        super().__init__(skill_name, f"Skill '{skill_name}' no encontrado")
        self.code = "SKILL_NOT_FOUND"


class SkillLoadError(SkillError):
    """Error al cargar un skill."""
    def __init__(self, skill_name: str = "", reason: str = ""):
        msg = f"No se pudo cargar el skill '{skill_name}'"
        if reason:
            msg += f": {reason}"
        super().__init__(skill_name, msg)
        self.code = "SKILL_LOAD_ERROR"


class SkillExecutionError(SkillError):
    """Error durante la ejecución de un skill."""
    def __init__(self, skill_name: str = "", reason: str = ""):
        msg = f"Error ejecutando '{skill_name}'"
        if reason:
            msg += f": {reason}"
        super().__init__(skill_name, msg)
        self.code = "SKILL_EXEC_ERROR"


# ─── Voice Errors ─────────────────────────────────────────────

class VoiceError(JarvisError):
    """Error en el sistema de voz."""
    def __init__(self, message: str = "Error en el sistema de voz"):
        super().__init__(message, "VOICE_ERROR")


class TTSError(VoiceError):
    """Error en Text-to-Speech."""
    def __init__(self, message: str = "Error en síntesis de voz"):
        super().__init__(message)
        self.code = "TTS_ERROR"


class STTError(VoiceError):
    """Error en Speech-to-Text."""
    def __init__(self, message: str = "Error en reconocimiento de voz"):
        super().__init__(message)
        self.code = "STT_ERROR"


class WakeWordError(VoiceError):
    """Error en detección de wake word."""
    def __init__(self, message: str = "Error en detección de wake word"):
        super().__init__(message)
        self.code = "WAKEWORD_ERROR"


# ─── Memory Errors ────────────────────────────────────────────

class MemoryError(JarvisError):
    """Error en el sistema de memoria."""
    def __init__(self, message: str = "Error en el sistema de memoria"):
        super().__init__(message, "MEMORY_ERROR")


# ─── Task Errors ──────────────────────────────────────────────

class TaskError(JarvisError):
    """Error en el motor de tareas."""
    def __init__(self, message: str = "Error en el motor de tareas"):
        super().__init__(message, "TASK_ERROR")


class TaskTimeoutError(TaskError):
    """Tarea excedió el tiempo límite."""
    def __init__(self, task_id: str = "", timeout: int = 0):
        msg = f"Tarea '{task_id}' excedió el tiempo límite de {timeout}s"
        super().__init__(msg)
        self.code = "TASK_TIMEOUT"
