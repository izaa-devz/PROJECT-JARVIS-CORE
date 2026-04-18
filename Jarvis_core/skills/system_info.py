"""
JARVIS Skill — Información del Sistema
=========================================
Muestra información de CPU, RAM, disco, batería.
"""

import asyncio
import platform
from typing import List
from skills.base_skill import BaseSkill, SkillCategory, SkillContext, SkillResult
from utils.logger import get_logger
from utils.helpers import format_bytes

log = get_logger("skills.system_info")


class SystemInfoSkill(BaseSkill):
    """Skill para obtener información del sistema."""

    @property
    def name(self) -> str:
        return "system_info"

    @property
    def description(self) -> str:
        return "Muestra información del sistema: CPU, RAM, disco, batería"

    @property
    def intents(self) -> List[str]:
        return ["system_info"]

    @property
    def category(self) -> SkillCategory:
        return SkillCategory.INFO

    @property
    def patterns(self) -> List[str]:
        return ["cpu", "ram", "memoria", "disco", "bateria", "procesador", "sistema", "hardware"]

    @property
    def examples(self) -> List[str]:
        return [
            "¿cuánta RAM tengo?",
            "dime el estado del CPU",
            "muestra info del sistema",
            "cómo está el disco",
            "cuánta batería queda",
        ]

    @property
    def priority(self) -> int:
        return 15

    async def execute(self, context: SkillContext) -> SkillResult:
        """Obtiene y muestra información del sistema."""
        try:
            import psutil

            raw = context.raw_command.lower()

            # Determinar qué info específica piden
            show_cpu = any(w in raw for w in ["cpu", "procesador", "rendimiento"])
            show_ram = any(w in raw for w in ["ram", "memoria"])
            show_disk = any(w in raw for w in ["disco", "almacenamiento", "espacio"])
            show_battery = any(w in raw for w in ["bateria", "carga"])

            # Si no especifica, mostrar todo
            show_all = not any([show_cpu, show_ram, show_disk, show_battery])

            def get_info():
                info = {}

                if show_all or show_cpu:
                    info["cpu"] = {
                        "percent": psutil.cpu_percent(interval=1),
                        "cores_physical": psutil.cpu_count(logical=False),
                        "cores_logical": psutil.cpu_count(logical=True),
                        "freq": psutil.cpu_freq(),
                    }

                if show_all or show_ram:
                    mem = psutil.virtual_memory()
                    info["ram"] = {
                        "total": mem.total,
                        "available": mem.available,
                        "used": mem.used,
                        "percent": mem.percent,
                    }

                if show_all or show_disk:
                    partitions = psutil.disk_partitions()
                    disks = []
                    for part in partitions:
                        try:
                            usage = psutil.disk_usage(part.mountpoint)
                            disks.append({
                                "device": part.device,
                                "mountpoint": part.mountpoint,
                                "total": usage.total,
                                "used": usage.used,
                                "free": usage.free,
                                "percent": usage.percent,
                            })
                        except PermissionError:
                            pass
                    info["disk"] = disks

                if show_all or show_battery:
                    battery = psutil.sensors_battery()
                    if battery:
                        info["battery"] = {
                            "percent": battery.percent,
                            "plugged": battery.power_plugged,
                            "secs_left": battery.secsleft if battery.secsleft != psutil.POWER_TIME_UNLIMITED else None,
                        }

                return info

            info = await asyncio.to_thread(get_info)

            # Formatear mensaje
            lines = ["📊 **Información del Sistema**", ""]

            # OS Info
            if show_all:
                lines.append(f"🖥️ **Sistema**: {platform.system()} {platform.release()} ({platform.architecture()[0]})")
                lines.append(f"    Hostname: {platform.node()}")
                lines.append("")

            if "cpu" in info:
                cpu = info["cpu"]
                lines.append(f"🧠 **CPU**: {cpu['percent']}% de uso")
                lines.append(f"    Núcleos: {cpu['cores_physical']} físicos, {cpu['cores_logical']} lógicos")
                if cpu["freq"]:
                    lines.append(f"    Frecuencia: {cpu['freq'].current:.0f} MHz")
                lines.append("")

            if "ram" in info:
                ram = info["ram"]
                lines.append(f"💾 **RAM**: {ram['percent']}% en uso")
                lines.append(f"    Usada: {format_bytes(ram['used'])} / {format_bytes(ram['total'])}")
                lines.append(f"    Disponible: {format_bytes(ram['available'])}")
                lines.append("")

            if "disk" in info:
                for disk in info["disk"]:
                    lines.append(f"💿 **Disco** ({disk['device']}): {disk['percent']}% usado")
                    lines.append(f"    Usado: {format_bytes(disk['used'])} / {format_bytes(disk['total'])}")
                    lines.append(f"    Libre: {format_bytes(disk['free'])}")
                lines.append("")

            if "battery" in info:
                bat = info["battery"]
                icon = "🔌" if bat["plugged"] else "🔋"
                lines.append(f"{icon} **Batería**: {bat['percent']}%")
                status = "Cargando" if bat["plugged"] else "En batería"
                lines.append(f"    Estado: {status}")
                if bat["secs_left"] and not bat["plugged"]:
                    mins = int(bat["secs_left"] / 60)
                    lines.append(f"    Tiempo restante: ~{mins} minutos")

            return SkillResult.ok("\n".join(lines), data=info)

        except ImportError:
            return SkillResult.fail(
                "psutil no disponible",
                message="❌ Módulo `psutil` no instalado. Instálalo con: `pip install psutil`",
            )
        except Exception as e:
            return SkillResult.fail(str(e), message=f"❌ Error obteniendo info del sistema: {e}")
