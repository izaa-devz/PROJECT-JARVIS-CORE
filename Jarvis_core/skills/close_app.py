"""
JARVIS Skill — Cerrar Aplicaciones
=====================================
Cierra aplicaciones del sistema por nombre.
"""

import asyncio
import subprocess
from typing import List
from skills.base_skill import BaseSkill, SkillCategory, SkillContext, SkillResult
from utils.logger import get_logger
from utils.config_loader import config

log = get_logger("skills.close_app")


class CloseAppSkill(BaseSkill):
    """Skill para cerrar aplicaciones del sistema."""

    @property
    def name(self) -> str:
        return "close_app"

    @property
    def description(self) -> str:
        return "Cierra aplicaciones y programas en ejecución"

    @property
    def intents(self) -> List[str]:
        return ["close_app", "kill_app", "stop_app"]

    @property
    def category(self) -> SkillCategory:
        return SkillCategory.APP

    @property
    def patterns(self) -> List[str]:
        return ["cierra", "cerrar", "mata", "matar", "termina", "terminar", "detener", "finaliza"]

    @property
    def examples(self) -> List[str]:
        return [
            "cierra chrome",
            "mata el proceso de firefox",
            "termina spotify",
            "cierra el bloc de notas",
        ]

    @property
    def priority(self) -> int:
        return 10

    @property
    def is_dangerous(self) -> bool:
        return False  # Cerrar apps no es destructivo

    async def execute(self, context: SkillContext) -> SkillResult:
        """Cierra la aplicación especificada."""
        app_name = context.entities.get("app_name", context.entities.get("target", "")).strip().lower()

        if not app_name:
            return SkillResult.fail(
                "No especificaste qué cerrar",
                message="¿Qué aplicación quieres que cierre? Ejemplo: 'cierra chrome'",
            )

        # Resolver nombre a ejecutable
        apps_registry = config.get("skills", "apps_registry", default={})
        executable = apps_registry.get(app_name, "")

        # Si no está en el registro, usar el nombre directamente
        if not executable:
            for registered_name, exe in apps_registry.items():
                if app_name in registered_name or registered_name in app_name:
                    executable = exe
                    break

        if not executable:
            executable = app_name
            if not executable.endswith(".exe"):
                executable = f"{app_name}.exe"

        try:
            log.info(f"Cerrando aplicación: {app_name} → {executable}")

            # Usar taskkill en Windows
            result = await asyncio.to_thread(
                subprocess.run,
                ["taskkill", "/IM", executable, "/F"],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                return SkillResult.ok(
                    message=f"✅ **{app_name}** cerrado correctamente",
                    data={"app": app_name, "executable": executable},
                )
            elif "no se encontr" in result.stderr.lower() or "not found" in result.stderr.lower():
                return SkillResult.fail(
                    f"{app_name} no está en ejecución",
                    message=f"⚠️ **{app_name}** no está corriendo actualmente",
                )
            else:
                log.warning(f"taskkill output: {result.stderr}")
                return SkillResult.fail(
                    result.stderr,
                    message=f"⚠️ No pude cerrar **{app_name}**: {result.stderr.strip()}",
                )

        except Exception as e:
            log.error(f"Error cerrando {app_name}: {e}")
            return SkillResult.fail(str(e), message=f"❌ Error al cerrar **{app_name}**: {e}")
