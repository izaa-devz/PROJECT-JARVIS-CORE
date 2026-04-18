"""
JARVIS Skill — Ejecutor de Comandos CMD/PowerShell
=====================================================
Ejecuta comandos del sistema en CMD o PowerShell.
"""

import asyncio
import subprocess
from typing import List
from skills.base_skill import BaseSkill, SkillCategory, SkillContext, SkillResult
from utils.logger import get_logger

log = get_logger("skills.cmd_executor")


class CmdExecutorSkill(BaseSkill):
    """Skill para ejecutar comandos en CMD/PowerShell."""

    @property
    def name(self) -> str:
        return "cmd_executor"

    @property
    def description(self) -> str:
        return "Ejecuta comandos en CMD o PowerShell"

    @property
    def intents(self) -> List[str]:
        return ["execute_cmd"]

    @property
    def category(self) -> SkillCategory:
        return SkillCategory.SYSTEM

    @property
    def patterns(self) -> List[str]:
        return ["ejecuta comando", "cmd", "powershell", "terminal", "consola", "shell"]

    @property
    def examples(self) -> List[str]:
        return [
            "ejecuta el comando dir",
            "ejecuta ipconfig en cmd",
            "corre 'Get-Process' en powershell",
        ]

    @property
    def priority(self) -> int:
        return 20

    @property
    def is_dangerous(self) -> bool:
        return True  # Ejecutar comandos arbitrarios es potencialmente peligroso

    async def execute(self, context: SkillContext) -> SkillResult:
        """Ejecuta un comando en el shell."""
        command_text = context.entities.get("command_text", context.entities.get("target", "")).strip()
        shell = context.entities.get("shell", "cmd")

        if not command_text:
            return SkillResult.fail(
                "No especificaste qué comando ejecutar",
                message="¿Qué comando quieres ejecutar? Ejemplo: 'ejecuta el comando dir'",
            )

        # Comandos peligrosos a bloquear
        dangerous_commands = ["format", "del /f", "rmdir /s", "rm -rf", "rd /s"]
        cmd_lower = command_text.lower()
        for dangerous in dangerous_commands:
            if dangerous in cmd_lower:
                return SkillResult.fail(
                    f"Comando peligroso bloqueado: {command_text}",
                    message=f"⛔ **Comando bloqueado** por seguridad: `{command_text}`\n"
                            "Este tipo de comandos destructivos no están permitidos.",
                )

        try:
            log.info(f"Ejecutando en {shell}: {command_text}")

            if shell == "powershell":
                full_cmd = ["powershell", "-Command", command_text]
            else:
                full_cmd = ["cmd", "/c", command_text]

            def run_cmd():
                result = subprocess.run(
                    full_cmd,
                    capture_output=True,
                    text=True,
                    timeout=30,
                    encoding="utf-8",
                    errors="replace",
                )
                return result

            result = await asyncio.to_thread(run_cmd)

            # Formatear output
            output = result.stdout.strip() if result.stdout else ""
            error = result.stderr.strip() if result.stderr else ""

            lines = [f"⚡ Comando ejecutado en **{shell}**: `{command_text}`", ""]

            if output:
                # Limitar output
                if len(output) > 2000:
                    output = output[:2000] + "\n... (output truncado)"
                lines.append("**Salida:**")
                lines.append(f"```\n{output}\n```")

            if error:
                if len(error) > 500:
                    error = error[:500] + "\n..."
                lines.append("**Errores:**")
                lines.append(f"```\n{error}\n```")

            if result.returncode != 0:
                lines.append(f"⚠️ Código de salida: {result.returncode}")

            success = result.returncode == 0
            return SkillResult(
                success=success,
                message="\n".join(lines),
                data={"output": output, "error": error, "returncode": result.returncode},
            )

        except subprocess.TimeoutExpired:
            return SkillResult.fail(
                "Timeout",
                message=f"⏱️ El comando `{command_text}` excedió el tiempo límite (30s)",
            )
        except Exception as e:
            return SkillResult.fail(str(e), message=f"❌ Error ejecutando comando: {e}")
