"""
JARVIS — Engine Core (Motor Principal)
========================================
El corazón del sistema. Orquesta todos los subsistemas:
- Inicialización
- Event loop principal
- Routing de comandos
- Input/Output (CLI y voz)
- Shutdown limpio
"""

import asyncio
import sys
import os
import time
from typing import Optional

# Asegurar que el directorio raíz está en sys.path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from core.state import StateManager, SystemStatus, InteractionMode
from core.event_bus import EventBus, Event, Priority
from core.exceptions import ShutdownRequested, JarvisError
from router.command_router import CommandRouter
from skills.skill_registry import SkillRegistry
from memory.memory_manager import MemoryManager
from task_engine.task_manager import TaskManager
from task_engine.scheduler import Scheduler
from task_engine.background import BackgroundRunner
from voice.voice_engine import VoiceEngine
from ui.terminal_ui import TerminalUI
from utils.logger import JarvisLogger, get_logger
from utils.config_loader import config


class JarvisEngine:
    """
    Motor principal de JARVIS.
    
    Responsabilidades:
    - Inicializar todos los subsistemas
    - Gestionar el event loop principal
    - Coordinar input/output
    - Manejar ciclo de vida (startup → run → shutdown)
    """

    def __init__(self, config_path: str = "config.json"):
        # Cargar configuración
        config.load(config_path)

        # Inicializar logger
        jarvis_config = config.get("jarvis", default={})
        JarvisLogger.initialize(
            log_dir="logs",
            log_file="jarvis.log",
            max_size_mb=jarvis_config.get("max_log_size_mb", 10),
            backup_count=jarvis_config.get("log_backup_count", 5),
            level=jarvis_config.get("log_level", "INFO"),
            debug=jarvis_config.get("debug", False),
        )

        self._log = get_logger("core.engine")

        # Subsistemas
        self.state = StateManager()
        self.event_bus = EventBus()
        self.memory = MemoryManager(
            data_dir=config.get("memory", "data_dir", default="data"),
            max_history=config.get("memory", "history_max_entries", default=1000),
            auto_save_interval=config.get("memory", "auto_save_interval_seconds", default=60),
        )
        self.skill_registry = SkillRegistry()
        self.task_manager = TaskManager(
            max_concurrent=config.get("task_engine", "max_concurrent_tasks", default=10),
            default_timeout=config.get("task_engine", "task_timeout_seconds", default=300),
        )
        self.scheduler = Scheduler(
            check_interval=config.get("task_engine", "scheduler_check_interval", default=1),
        )
        self.background = BackgroundRunner()
        self.voice = VoiceEngine()
        self.router: Optional[CommandRouter] = None  # Se crea después de cargar skills

        # UI
        ui_config = config.get("ui", default={})
        self.ui = TerminalUI(
            theme=ui_config.get("theme", "hacker"),
            show_banner=ui_config.get("show_banner", True),
            show_timestamps=ui_config.get("show_timestamps", True),
            prompt_symbol=config.get("interaction", "prompt_symbol", default="❯"),
        )

        self._should_exit = False

    async def start(self) -> None:
        """
        Inicia todos los subsistemas y arranca el loop principal.
        Este es el entry point principal del sistema.
        """
        try:
            await self._initialize()
            await self._run_loop()
        except KeyboardInterrupt:
            self._log.info("Interrupción de teclado recibida")
        except ShutdownRequested:
            self._log.info("Apagado solicitado")
        except Exception as e:
            self._log.critical(f"Error fatal: {e}", exc_info=True)
            self.ui.show_error(f"Error fatal: {e}")
        finally:
            await self._shutdown()

    async def _initialize(self) -> None:
        """Inicializa todos los subsistemas en orden."""
        await self.state.set_status(SystemStatus.INITIALIZING)

        self._log.info("=" * 60)
        self._log.info("JARVIS Core — Iniciando sistema")
        self._log.info("=" * 60)

        # 1. Memoria
        await self.memory.initialize()
        await self.memory.start_auto_save()

        # 2. Cargar skills
        skills_config = config.get("skills", default={})
        loaded = await self.skill_registry.discover_and_load(
            skills_dir=skills_config.get("skills_dir", "skills"),
            disabled=skills_config.get("disabled_skills", []),
        )

        # Registrar skills en state
        for skill_name in self.skill_registry.get_all_skills():
            self.state.register_skill(skill_name)

        # 3. Router (necesita skills y memoria)
        nlp_config = config.get("nlp", default={})
        self.router = CommandRouter(
            skill_registry=self.skill_registry,
            memory=self.memory,
            event_bus=self.event_bus,
            spacy_model=nlp_config.get("spacy_model", "es_core_news_md"),
            use_spacy=nlp_config.get("use_spacy", True),
            fuzzy_threshold=nlp_config.get("fuzzy_threshold", 70),
        )

        # 4. Scheduler
        if config.get("task_engine", "enable_scheduler", default=True):
            await self.scheduler.start()

        # 5. Voz (si está habilitada)
        if config.get("voice", "enabled", default=False):
            await self.voice.initialize()

        # 6. Modo de interacción
        mode_str = config.get("interaction", "mode", default="text")
        mode = InteractionMode(mode_str)
        await self.state.set_mode(mode)

        # 7. Registrar event listeners
        await self._setup_events()

        # 8. Listo
        await self.state.set_status(SystemStatus.READY)

        # Mostrar banner
        if config.get("ui", "show_banner", default=True):
            self.ui.show_banner(
                version=config.get("jarvis", "version", default="1.0.0"),
                skills_count=self.skill_registry.count,
            )

        self.ui.show_ready()
        self._log.info(f"JARVIS listo — {loaded} skills cargados, modo: {mode.value}")

    async def _setup_events(self) -> None:
        """Configura los listeners de eventos internos."""
        # Logging de eventos
        async def log_command(event: Event):
            self._log.debug(f"Evento: {event.name} → {event.data}")

        self.event_bus.on("command.*", log_command, priority=Priority.MONITOR)
        self.event_bus.on("skill.*", log_command, priority=Priority.MONITOR)

    async def _run_loop(self) -> None:
        """Loop principal de interacción."""
        while not self._should_exit:
            try:
                # Obtener input según el modo
                mode = self.state.mode

                if mode == InteractionMode.TEXT:
                    user_input = await asyncio.to_thread(self.ui.get_input)
                elif mode == InteractionMode.VOICE:
                    user_input = await self._voice_input()
                elif mode == InteractionMode.HYBRID:
                    # En modo híbrido, preferir texto pero aceptar voz
                    user_input = await asyncio.to_thread(self.ui.get_input)
                else:
                    user_input = await asyncio.to_thread(self.ui.get_input)

                if not user_input:
                    continue

                # Procesar comando
                await self._process_command(user_input)

            except KeyboardInterrupt:
                self._should_exit = True
            except EOFError:
                self._should_exit = True
            except Exception as e:
                self._log.error(f"Error en loop principal: {e}", exc_info=True)
                self.ui.show_error(f"Error interno: {e}")

    async def _process_command(self, text: str) -> None:
        """Procesa un comando del usuario."""
        await self.state.set_status(SystemStatus.PROCESSING)
        await self.state.record_command(text)

        start = time.time()

        try:
            # Routing
            result = await self.router.route(text)

            duration_ms = result.duration_ms

            # Mostrar resultados
            for skill_result in result.results:
                self.ui.show_response(
                    message=skill_result.message,
                    skill_name=result.skill_name,
                    duration_ms=duration_ms,
                )

                # TTS si está habilitado
                if skill_result.speak and self.voice.is_enabled:
                    await self.voice.speak(skill_result.message)

                # Verificar acción especial
                if skill_result.data and isinstance(skill_result.data, dict):
                    if skill_result.data.get("action") == "exit":
                        self._should_exit = True
                        return

            # Registrar skill usado
            if result.skill_name:
                await self.state.record_skill_usage(result.skill_name)

            await self.state.record_response(
                result.results[0].message if result.results else ""
            )

        except JarvisError as e:
            self.ui.show_error(str(e))
            await self.state.record_error()
        except Exception as e:
            self._log.error(f"Error procesando '{text}': {e}", exc_info=True)
            self.ui.show_error(f"Error inesperado: {e}")
            await self.state.record_error()
        finally:
            await self.state.set_status(SystemStatus.READY)

    async def _voice_input(self) -> Optional[str]:
        """Obtiene input por voz."""
        if not self.voice.is_enabled:
            return await asyncio.to_thread(self.ui.get_input)

        self.ui.show_info("Escuchando...")
        await self.state.set_status(SystemStatus.LISTENING)
        text = await self.voice.listen()

        if text:
            self.ui.show_info(f"Escuché: \"{text}\"")
            return text
        else:
            self.ui.show_warning("No pude entender. Intenta de nuevo.")
            return None

    async def _shutdown(self) -> None:
        """Apagado limpio de todos los subsistemas."""
        self._log.info("Iniciando secuencia de apagado...")
        await self.state.set_status(SystemStatus.SHUTTING_DOWN)

        # Detener scheduler
        await self.scheduler.stop()

        # Detener task manager
        await self.task_manager.shutdown()

        # Teardown de skills
        await self.skill_registry.teardown_all()

        # Guardar memoria
        await self.memory.shutdown()

        # Cerrar background runner
        self.background.shutdown()

        # Limpiar event bus
        self.event_bus.clear()

        # Cerrar logger
        JarvisLogger.shutdown()

        # Despedida
        self.ui.show_farewell()
