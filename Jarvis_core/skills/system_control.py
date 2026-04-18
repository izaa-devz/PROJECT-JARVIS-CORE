"""
JARVIS Skill — Control del Sistema
=====================================
Control de volumen, brillo, apagar, reiniciar, bloquear, suspender.
"""

import asyncio
import subprocess
import ctypes
import os
from typing import List
from skills.base_skill import BaseSkill, SkillCategory, SkillContext, SkillResult
from utils.logger import get_logger
from utils.helpers import parse_percentage

log = get_logger("skills.system_control")


class SystemControlSkill(BaseSkill):
    """Skill para control del sistema: volumen, brillo, energía."""

    @property
    def name(self) -> str:
        return "system_control"

    @property
    def description(self) -> str:
        return "Controla volumen, brillo, y opciones de energía del sistema"

    @property
    def intents(self) -> List[str]:
        return [
            "volume_up", "volume_down", "volume_set", "volume_mute",
            "brightness_up", "brightness_down", "brightness_set",
            "shutdown_pc", "restart_pc", "sleep_pc", "lock_pc",
        ]

    @property
    def category(self) -> SkillCategory:
        return SkillCategory.SYSTEM

    @property
    def patterns(self) -> List[str]:
        return [
            "volumen", "brillo", "apagar", "reiniciar", "suspender",
            "bloquear", "silenciar", "mutear",
        ]

    @property
    def examples(self) -> List[str]:
        return [
            "sube el volumen",
            "baja el brillo",
            "pon el volumen al 50",
            "silencia el sistema",
            "apaga la computadora",
            "reinicia el equipo",
            "bloquea la pantalla",
        ]

    @property
    def priority(self) -> int:
        return 5

    async def execute(self, context: SkillContext) -> SkillResult:
        """Ejecuta la acción de control correspondiente."""
        intent = context.intent

        handlers = {
            "volume_up": self._volume_up,
            "volume_down": self._volume_down,
            "volume_set": self._volume_set,
            "volume_mute": self._volume_mute,
            "brightness_up": self._brightness_up,
            "brightness_down": self._brightness_down,
            "brightness_set": self._brightness_set,
            "shutdown_pc": self._shutdown,
            "restart_pc": self._restart,
            "sleep_pc": self._sleep,
            "lock_pc": self._lock,
        }

        handler = handlers.get(intent)
        if handler:
            return await handler(context)

        return SkillResult.fail(f"Acción de sistema no reconocida: {intent}")

    # ─── Volume Control ────────────────────────────────────────

    async def _volume_up(self, context: SkillContext) -> SkillResult:
        """Sube el volumen."""
        amount = context.entities.get("amount", 10)
        try:
            volume = await self._set_volume_relative(amount)
            return SkillResult.ok(f"🔊 Volumen subido. Nivel actual: **{volume}%**")
        except Exception as e:
            return await self._volume_fallback("up", e)

    async def _volume_down(self, context: SkillContext) -> SkillResult:
        """Baja el volumen."""
        amount = context.entities.get("amount", 10)
        try:
            volume = await self._set_volume_relative(-amount)
            return SkillResult.ok(f"🔉 Volumen bajado. Nivel actual: **{volume}%**")
        except Exception as e:
            return await self._volume_fallback("down", e)

    async def _volume_set(self, context: SkillContext) -> SkillResult:
        """Establece el volumen a un nivel específico."""
        amount = context.entities.get("amount")
        if amount is None:
            pct = parse_percentage(context.raw_command)
            amount = pct if pct is not None else 50

        try:
            volume = await self._set_volume_absolute(amount)
            return SkillResult.ok(f"🔊 Volumen establecido a **{volume}%**")
        except Exception as e:
            return SkillResult.fail(str(e), message=f"❌ Error al establecer volumen: {e}")

    async def _volume_mute(self, context: SkillContext) -> SkillResult:
        """Silencia/desmutea el volumen."""
        try:
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

            def toggle_mute():
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume = cast(interface, POINTER(IAudioEndpointVolume))
                current = volume.GetMute()
                volume.SetMute(not current, None)
                return not current

            is_muted = await asyncio.to_thread(toggle_mute)
            status = "silenciado 🔇" if is_muted else "activado 🔊"
            return SkillResult.ok(f"Audio {status}")
        except ImportError:
            # Fallback con nircmd o teclas multimedia
            return await self._volume_fallback("mute", None)
        except Exception as e:
            return SkillResult.fail(str(e), message=f"❌ Error al silenciar: {e}")

    async def _set_volume_relative(self, change: int) -> int:
        """Cambia el volumen relativamente. Retorna el nuevo nivel."""
        try:
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

            def adjust():
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume = cast(interface, POINTER(IAudioEndpointVolume))
                current = volume.GetMasterVolumeLevelScalar()
                new_level = max(0.0, min(1.0, current + (change / 100.0)))
                volume.SetMasterVolumeLevelScalar(new_level, None)
                return int(new_level * 100)

            return await asyncio.to_thread(adjust)
        except ImportError:
            raise

    async def _set_volume_absolute(self, level: int) -> int:
        """Establece el volumen a un nivel absoluto."""
        try:
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume

            level = max(0, min(100, level))

            def set_vol():
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume = cast(interface, POINTER(IAudioEndpointVolume))
                volume.SetMasterVolumeLevelScalar(level / 100.0, None)
                return level

            return await asyncio.to_thread(set_vol)
        except ImportError:
            raise

    async def _volume_fallback(self, action: str, error) -> SkillResult:
        """Fallback de volumen usando nircmd o PowerShell."""
        try:
            if action == "up":
                cmd = 'powershell -Command "(New-Object -ComObject WScript.Shell).SendKeys([char]175)"'
            elif action == "down":
                cmd = 'powershell -Command "(New-Object -ComObject WScript.Shell).SendKeys([char]174)"'
            elif action == "mute":
                cmd = 'powershell -Command "(New-Object -ComObject WScript.Shell).SendKeys([char]173)"'
            else:
                return SkillResult.fail(f"Acción desconocida: {action}")

            await asyncio.to_thread(subprocess.run, cmd, shell=True, capture_output=True)
            actions_msg = {"up": "🔊 Volumen subido", "down": "🔉 Volumen bajado", "mute": "🔇 Audio silenciado"}
            return SkillResult.ok(actions_msg.get(action, "Volumen ajustado"))
        except Exception as e2:
            return SkillResult.fail(str(e2), message=f"❌ Error controlando volumen: {e2}")

    # ─── Brightness Control ────────────────────────────────────

    async def _brightness_up(self, context: SkillContext) -> SkillResult:
        """Sube el brillo."""
        amount = context.entities.get("amount", 10)
        try:
            import screen_brightness_control as sbc
            current = await asyncio.to_thread(sbc.get_brightness)
            if isinstance(current, list):
                current = current[0]
            new_level = min(100, current + amount)
            await asyncio.to_thread(sbc.set_brightness, new_level)
            return SkillResult.ok(f"☀️ Brillo subido a **{new_level}%**")
        except ImportError:
            return SkillResult.fail("screen-brightness-control no instalado", message="❌ Módulo de brillo no disponible")
        except Exception as e:
            return SkillResult.fail(str(e), message=f"❌ Error ajustando brillo: {e}")

    async def _brightness_down(self, context: SkillContext) -> SkillResult:
        """Baja el brillo."""
        amount = context.entities.get("amount", 10)
        try:
            import screen_brightness_control as sbc
            current = await asyncio.to_thread(sbc.get_brightness)
            if isinstance(current, list):
                current = current[0]
            new_level = max(0, current - amount)
            await asyncio.to_thread(sbc.set_brightness, new_level)
            return SkillResult.ok(f"🔅 Brillo bajado a **{new_level}%**")
        except ImportError:
            return SkillResult.fail("screen-brightness-control no instalado", message="❌ Módulo de brillo no disponible")
        except Exception as e:
            return SkillResult.fail(str(e), message=f"❌ Error ajustando brillo: {e}")

    async def _brightness_set(self, context: SkillContext) -> SkillResult:
        """Establece el brillo a un nivel específico."""
        amount = context.entities.get("amount")
        if amount is None:
            pct = parse_percentage(context.raw_command)
            amount = pct if pct is not None else 50

        try:
            import screen_brightness_control as sbc
            level = max(0, min(100, amount))
            await asyncio.to_thread(sbc.set_brightness, level)
            return SkillResult.ok(f"☀️ Brillo establecido a **{level}%**")
        except ImportError:
            return SkillResult.fail("screen-brightness-control no instalado")
        except Exception as e:
            return SkillResult.fail(str(e), message=f"❌ Error: {e}")

    # ─── Power Management ──────────────────────────────────────

    async def _shutdown(self, context: SkillContext) -> SkillResult:
        """Apaga el equipo."""
        log.warning("Solicitud de apagado del sistema")
        try:
            await asyncio.to_thread(subprocess.run, ["shutdown", "/s", "/t", "5"], capture_output=True)
            return SkillResult.ok("⚡ El sistema se apagará en 5 segundos...")
        except Exception as e:
            return SkillResult.fail(str(e), message=f"❌ Error al apagar: {e}")

    async def _restart(self, context: SkillContext) -> SkillResult:
        """Reinicia el equipo."""
        log.warning("Solicitud de reinicio del sistema")
        try:
            await asyncio.to_thread(subprocess.run, ["shutdown", "/r", "/t", "5"], capture_output=True)
            return SkillResult.ok("🔄 El sistema se reiniciará en 5 segundos...")
        except Exception as e:
            return SkillResult.fail(str(e), message=f"❌ Error al reiniciar: {e}")

    async def _sleep(self, context: SkillContext) -> SkillResult:
        """Suspende el equipo."""
        try:
            await asyncio.to_thread(
                subprocess.run,
                ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"],
                capture_output=True,
            )
            return SkillResult.ok("😴 Suspendiendo el sistema...")
        except Exception as e:
            return SkillResult.fail(str(e), message=f"❌ Error al suspender: {e}")

    async def _lock(self, context: SkillContext) -> SkillResult:
        """Bloquea la sesión."""
        try:
            await asyncio.to_thread(ctypes.windll.user32.LockWorkStation)
            return SkillResult.ok("🔒 Pantalla bloqueada")
        except Exception as e:
            return SkillResult.fail(str(e), message=f"❌ Error al bloquear: {e}")
