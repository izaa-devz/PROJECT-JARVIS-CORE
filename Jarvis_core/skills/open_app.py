"""
JARVIS Skill — Abrir Aplicaciones
====================================
Abre aplicaciones del sistema usando el registro de apps configurado
o búsqueda directa por nombre de ejecutable.
"""

import os
import subprocess
import asyncio
from typing import List
from skills.base_skill import BaseSkill, SkillCategory, SkillContext, SkillResult
from utils.logger import get_logger
from utils.config_loader import config

log = get_logger("skills.open_app")


class OpenAppSkill(BaseSkill):
    """Skill para abrir aplicaciones del sistema."""

    @property
    def name(self) -> str:
        return "open_app"

    @property
    def description(self) -> str:
        return "Abre aplicaciones y programas del sistema"

    @property
    def intents(self) -> List[str]:
        return ["open_app", "launch_app", "start_app"]

    @property
    def category(self) -> SkillCategory:
        return SkillCategory.APP

    @property
    def patterns(self) -> List[str]:
        return ["abre", "abrir", "ejecuta", "ejecutar", "inicia", "iniciar", "lanza", "lanzar", "arranca"]

    @property
    def examples(self) -> List[str]:
        return [
            "abre chrome",
            "abre el bloc de notas",
            "inicia spotify",
            "lanza visual studio code",
            "ejecuta la calculadora",
        ]

    @property
    def priority(self) -> int:
        return 10

    async def execute(self, context: SkillContext) -> SkillResult:
        """Abre la aplicación especificada."""
        app_name = context.entities.get("app_name", context.entities.get("target", "")).strip().lower()

        if not app_name:
            return SkillResult.fail(
                "No especificaste qué aplicación abrir",
                message="¿Qué aplicación quieres que abra? Ejemplo: 'abre chrome'",
            )

        # Buscar en el registro de apps
        apps_registry = config.get("skills", "apps_registry", default={})

        # Buscar coincidencia
        executable = None
        matched_name = app_name

        # Búsqueda exacta
        if app_name in apps_registry:
            executable = apps_registry[app_name]
            matched_name = app_name

        # Búsqueda parcial
        if not executable:
            for registered_name, exe in apps_registry.items():
                if app_name in registered_name or registered_name in app_name:
                    executable = exe
                    matched_name = registered_name
                    break

        # Si no está en el registro, intentar ejecutar directamente
        if not executable:
            executable = app_name
            # Agregar .exe si no lo tiene
            if not executable.endswith(".exe"):
                executable = f"{app_name}.exe"

        # Ejecutar
        try:
            log.info(f"Abriendo aplicación: {matched_name} → {executable}")

            # Usar subprocess para abrir la aplicación
            if os.name == "nt":  # Windows
                process = await asyncio.to_thread(
                    subprocess.Popen,
                    executable,
                    shell=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                process = await asyncio.to_thread(
                    subprocess.Popen,
                    [executable],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

            return SkillResult.ok(
                message=f"✅ Abriendo **{matched_name}**",
                data={"app": matched_name, "executable": executable, "pid": process.pid},
            )

        except FileNotFoundError:
            # Intentar con 'start' en Windows
            try:
                if os.name == "nt":
                    await asyncio.to_thread(
                        subprocess.Popen,
                        f'start "" "{app_name}"',
                        shell=True,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    return SkillResult.ok(message=f"✅ Abriendo **{app_name}**")
            except Exception:
                pass

            return SkillResult.fail(
                f"No encontré la aplicación '{app_name}'",
                message=f"❌ No pude encontrar **{app_name}**. ¿Está instalada?",
            )
        except Exception as e:
            log.error(f"Error abriendo {app_name}: {e}")
            return SkillResult.fail(str(e), message=f"❌ Error al abrir **{app_name}**: {e}")
