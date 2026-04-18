"""
JARVIS Skill — Capturas de Pantalla
======================================
Toma capturas de pantalla del escritorio.
"""

import os
import asyncio
from datetime import datetime
from typing import List
from skills.base_skill import BaseSkill, SkillCategory, SkillContext, SkillResult
from utils.logger import get_logger
from utils.config_loader import config
from utils.helpers import ensure_dir

log = get_logger("skills.screenshot")


class ScreenshotSkill(BaseSkill):
    """Skill para tomar capturas de pantalla."""

    @property
    def name(self) -> str:
        return "screenshot"

    @property
    def description(self) -> str:
        return "Toma capturas de pantalla del escritorio"

    @property
    def intents(self) -> List[str]:
        return ["take_screenshot"]

    @property
    def category(self) -> SkillCategory:
        return SkillCategory.UTILITY

    @property
    def patterns(self) -> List[str]:
        return ["screenshot", "captura", "pantallazo", "foto de pantalla"]

    @property
    def examples(self) -> List[str]:
        return [
            "toma una captura de pantalla",
            "haz un screenshot",
            "captura la pantalla",
        ]

    @property
    def priority(self) -> int:
        return 10

    async def execute(self, context: SkillContext) -> SkillResult:
        """Toma una captura de pantalla."""
        try:
            import pyautogui

            screenshot_dir = config.get("skills", "screenshot_dir", default="screenshots")
            ensure_dir(screenshot_dir)

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            filepath = os.path.abspath(os.path.join(screenshot_dir, filename))

            def take():
                img = pyautogui.screenshot()
                img.save(filepath)
                return filepath

            saved_path = await asyncio.to_thread(take)

            log.info(f"Screenshot guardado: {saved_path}")
            return SkillResult.ok(
                f"📸 Captura guardada: `{saved_path}`",
                data={"path": saved_path, "filename": filename},
            )

        except ImportError:
            return SkillResult.fail(
                "pyautogui no disponible",
                message="❌ El módulo `pyautogui` no está instalado. Instálalo con: `pip install pyautogui`",
            )
        except Exception as e:
            log.error(f"Error tomando screenshot: {e}")
            return SkillResult.fail(str(e), message=f"❌ Error al capturar pantalla: {e}")
