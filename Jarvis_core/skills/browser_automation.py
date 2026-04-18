"""
JARVIS Skill — Automatización del Navegador
==============================================
Abre URLs, realiza búsquedas web.
"""

import webbrowser
import asyncio
from typing import List
from urllib.parse import quote_plus
from skills.base_skill import BaseSkill, SkillCategory, SkillContext, SkillResult
from utils.logger import get_logger
from utils.config_loader import config
from utils.helpers import is_url

log = get_logger("skills.browser_automation")


# Motores de búsqueda soportados
SEARCH_ENGINES = {
    "google": "https://www.google.com/search?q={}",
    "bing": "https://www.bing.com/search?q={}",
    "duckduckgo": "https://duckduckgo.com/?q={}",
    "youtube": "https://www.youtube.com/results?search_query={}",
}


class BrowserAutomationSkill(BaseSkill):
    """Skill para automatización del navegador."""

    @property
    def name(self) -> str:
        return "browser_automation"

    @property
    def description(self) -> str:
        return "Abre URLs y realiza búsquedas en el navegador"

    @property
    def intents(self) -> List[str]:
        return ["open_url", "search_web"]

    @property
    def category(self) -> SkillCategory:
        return SkillCategory.BROWSER

    @property
    def patterns(self) -> List[str]:
        return ["busca", "buscar", "googlea", "googlear", "navega", "visita", "url", "web"]

    @property
    def examples(self) -> List[str]:
        return [
            "abre google.com",
            "busca qué es python",
            "googlea tutorial de javascript",
            "abre https://github.com",
            "busca en youtube música relajante",
        ]

    @property
    def priority(self) -> int:
        return 15

    async def execute(self, context: SkillContext) -> SkillResult:
        """Ejecuta la acción del navegador."""
        if context.intent == "open_url":
            return await self._open_url(context)
        elif context.intent == "search_web":
            return await self._search_web(context)
        return SkillResult.fail("Acción de navegador no reconocida")

    async def _open_url(self, context: SkillContext) -> SkillResult:
        """Abre una URL en el navegador."""
        url = context.entities.get("url", context.entities.get("target", ""))

        if not url:
            return SkillResult.fail(
                "No especificaste URL",
                message="¿Qué URL quieres abrir? Ejemplo: 'abre google.com'",
            )

        # Agregar protocolo si no lo tiene
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        try:
            log.info(f"Abriendo URL: {url}")
            await asyncio.to_thread(webbrowser.open, url)
            return SkillResult.ok(f"🌐 Abriendo **{url}**")
        except Exception as e:
            return SkillResult.fail(str(e), message=f"❌ Error al abrir URL: {e}")

    async def _search_web(self, context: SkillContext) -> SkillResult:
        """Realiza una búsqueda web."""
        query = context.entities.get("search_query", context.entities.get("target", ""))

        if not query:
            return SkillResult.fail(
                "No especificaste qué buscar",
                message="¿Qué quieres buscar? Ejemplo: 'busca qué es python'",
            )

        # Determinar motor de búsqueda
        engine = config.get("skills", "default_search_engine", default="google")
        raw = context.raw_command.lower()

        # Detectar si especifica motor
        if "youtube" in raw:
            engine = "youtube"
        elif "bing" in raw:
            engine = "bing"
        elif "duckduckgo" in raw or "duck" in raw:
            engine = "duckduckgo"

        search_url_template = SEARCH_ENGINES.get(engine, SEARCH_ENGINES["google"])
        search_url = search_url_template.format(quote_plus(query))

        try:
            log.info(f"Buscando en {engine}: {query}")
            await asyncio.to_thread(webbrowser.open, search_url)
            return SkillResult.ok(
                f"🔍 Buscando en **{engine}**: \"{query}\"",
                data={"engine": engine, "query": query, "url": search_url},
            )
        except Exception as e:
            return SkillResult.fail(str(e), message=f"❌ Error al buscar: {e}")
