"""
JARVIS — Command Router
=========================
El cerebro del sistema. Recibe texto del usuario, lo clasifica, extrae entidades,
y lo enruta al skill correcto para ejecución.
"""

import time
from typing import Optional, Tuple
from dataclasses import dataclass
from router.intent_classifier import IntentClassifier, IntentMatch
from router.entity_extractor import EntityExtractor
from router.pipeline_splitter import PipelineSplitter, SubCommand
from skills.base_skill import SkillContext, SkillResult
from skills.skill_registry import SkillRegistry
from memory.memory_manager import MemoryManager
from core.event_bus import EventBus, Event
from utils.logger import get_logger

log = get_logger("router.command_router")


@dataclass
class RouteResult:
    """Resultado del routing de un comando."""
    success: bool
    results: list  # List[SkillResult]
    intent: str = ""
    skill_name: str = ""
    duration_ms: float = 0
    sub_commands: int = 1


class CommandRouter:
    """
    Router principal de comandos.
    
    Pipeline:
    1. Pipeline Splitter → divide en sub-comandos si es complejo
    2. Para cada sub-comando:
       a. Intent Classifier → determina intención
       b. Entity Extractor → extrae entidades
       c. Skill Registry → encuentra el skill correcto
       d. Skill.execute() → ejecuta la acción
    3. Registra en memoria
    4. Emite eventos
    """

    def __init__(
        self,
        skill_registry: SkillRegistry,
        memory: MemoryManager,
        event_bus: EventBus,
        spacy_model: str = "es_core_news_md",
        use_spacy: bool = True,
        fuzzy_threshold: int = 70,
    ):
        self._registry = skill_registry
        self._memory = memory
        self._event_bus = event_bus

        # Sub-componentes
        self._classifier = IntentClassifier(
            spacy_model=spacy_model,
            use_spacy=use_spacy,
            fuzzy_threshold=fuzzy_threshold,
        )
        self._extractor = EntityExtractor()
        self._splitter = PipelineSplitter()

        # Cargar correcciones aprendidas
        corrections = memory.preferences.get_corrections()
        if corrections:
            self._classifier.load_corrections(corrections)

    async def route(self, text: str) -> RouteResult:
        """
        Procesa un comando completo del usuario.
        
        Args:
            text: Texto original del usuario
            
        Returns:
            RouteResult con los resultados de todas las sub-ejecuciones
        """
        start_time = time.time()
        text = text.strip()

        if not text:
            return RouteResult(success=False, results=[SkillResult.fail("Comando vacío")])

        # Emitir evento de comando recibido
        await self._event_bus.emit_simple("command.received", data={"text": text}, source="router")

        # 1. Dividir en sub-comandos
        sub_commands = self._splitter.split(text)

        # 2. Ejecutar cada sub-comando
        all_results = []
        last_intent = ""
        last_skill = ""

        for sub_cmd in sub_commands:
            result, intent_match = await self._route_single(sub_cmd.text, text)
            all_results.append(result)
            if intent_match:
                last_intent = intent_match.intent
                last_skill = result.data.get("skill_name", "") if result.data and isinstance(result.data, dict) else ""

            # Si un paso falla y el siguiente depende de él, abortar
            if not result.success and sub_cmd.depends_on_previous:
                log.warning(f"Sub-comando falló, abortando pipeline: {sub_cmd.text}")
                break

        # 3. Calcular duración total
        duration_ms = (time.time() - start_time) * 1000

        # 4. Registrar en memoria
        final_success = all(r.success for r in all_results)
        combined_message = " | ".join(r.message for r in all_results if r.message)
        self._memory.record_command(
            command=text,
            intent=last_intent,
            skill=last_skill,
            result=combined_message[:200],
            success=final_success,
            duration_ms=duration_ms,
        )

        # 5. Emitir evento de comando procesado
        await self._event_bus.emit_simple(
            "command.processed",
            data={
                "text": text,
                "intent": last_intent,
                "skill": last_skill,
                "success": final_success,
                "duration_ms": duration_ms,
            },
            source="router",
        )

        return RouteResult(
            success=final_success,
            results=all_results,
            intent=last_intent,
            skill_name=last_skill,
            duration_ms=duration_ms,
            sub_commands=len(sub_commands),
        )

    async def _route_single(self, text: str, original_text: str = "") -> Tuple[SkillResult, Optional[IntentMatch]]:
        """
        Enruta un único sub-comando.
        
        Returns:
            Tuple de (SkillResult, IntentMatch o None)
        """
        # 1. Clasificar intención
        intent_match = self._classifier.classify(text)
        log.debug(
            f"Clasificación: '{text[:50]}' → intent='{intent_match.intent}' "
            f"confidence={intent_match.confidence:.2f} method={intent_match.method}"
        )

        # 2. Intent desconocido
        if intent_match.intent == "unknown" or intent_match.confidence < 0.3:
            await self._event_bus.emit_simple(
                "command.unknown",
                data={"text": text, "match": intent_match},
                source="router",
            )
            return (
                SkillResult.fail(
                    "No entendí el comando",
                    message=f"No entendí qué quieres hacer con: \"{text}\"\n"
                            "Escribe 'ayuda' para ver los comandos disponibles.",
                ),
                intent_match,
            )

        # 3. Extraer entidades
        entities = self._extractor.extract(text, intent=intent_match.intent)
        log.debug(f"Entidades extraídas: {entities}")

        # 4. Construir contexto
        context = SkillContext(
            raw_command=original_text or text,
            intent=intent_match.intent,
            entities=entities,
            confidence=intent_match.confidence,
            parameters={"method": intent_match.method, "pattern": intent_match.matched_pattern},
        )

        # 5. Buscar skill
        skill = self._registry.find_handler(context)
        if not skill:
            return (
                SkillResult.fail(
                    f"Sin skill para '{intent_match.intent}'",
                    message=f"Entendí que quieres '{intent_match.intent}', pero no tengo un skill para eso.",
                ),
                intent_match,
            )

        # 6. Ejecutar skill
        log.info(f"Ejecutando: skill='{skill.name}' intent='{intent_match.intent}' entities={entities}")

        try:
            await self._event_bus.emit_simple(
                "skill.executing",
                data={"skill": skill.name, "intent": intent_match.intent},
                source="router",
            )

            result = await skill.execute(context)

            # Agregar metadata al resultado
            if result.data is None:
                result.data = {}
            if isinstance(result.data, dict):
                result.data["skill_name"] = skill.name

            await self._event_bus.emit_simple(
                "skill.executed",
                data={
                    "skill": skill.name,
                    "intent": intent_match.intent,
                    "success": result.success,
                },
                source="router",
            )

            return (result, intent_match)

        except Exception as e:
            log.error(f"Error ejecutando skill '{skill.name}': {e}", exc_info=True)
            await self._event_bus.emit_simple(
                "skill.error",
                data={"skill": skill.name, "error": str(e)},
                source="router",
            )
            return (
                SkillResult.fail(str(e), message=f"Error al ejecutar '{skill.name}': {e}"),
                intent_match,
            )

    def __repr__(self) -> str:
        return f"<CommandRouter classifier={self._classifier} registry={self._registry}>"
