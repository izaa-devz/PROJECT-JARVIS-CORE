"""
JARVIS — Skill Registry (Auto-Descubrimiento)
================================================
Sistema de registro automático de skills.
Escanea la carpeta /skills/ y registra cualquier clase que herede de BaseSkill.
"""

import os
import sys
import importlib
import inspect
from typing import Dict, List, Optional, Type
from skills.base_skill import BaseSkill, SkillContext
from utils.logger import get_logger

log = get_logger("skills.registry")


class SkillRegistry:
    """
    Registro centralizado de skills.
    
    Características:
    - Auto-descubrimiento: escanea /skills/ y registra automáticamente
    - No requiere modificar el core para añadir nuevos skills
    - Validación de skills al registrar
    - Búsqueda por intent, nombre, o contexto
    """

    def __init__(self):
        self._skills: Dict[str, BaseSkill] = {}  # name -> skill instance
        self._intent_map: Dict[str, List[BaseSkill]] = {}  # intent -> [skills]
        self._disabled: set = set()

    async def discover_and_load(self, skills_dir: str = "skills", disabled: List[str] = None) -> int:
        """
        Auto-descubre y carga todos los skills del directorio.
        
        Args:
            skills_dir: Directorio donde buscar skills
            disabled: Lista de nombres de skills a deshabilitar
            
        Returns:
            Cantidad de skills cargados exitosamente
        """
        self._disabled = set(disabled or [])
        loaded = 0

        # Asegurar que el directorio de skills esté en el path
        skills_path = os.path.abspath(skills_dir)
        if skills_path not in sys.path:
            sys.path.insert(0, os.path.dirname(skills_path))

        # Escanear archivos .py en el directorio de skills
        if not os.path.exists(skills_dir):
            log.warning(f"Directorio de skills no encontrado: {skills_dir}")
            return 0

        for filename in os.listdir(skills_dir):
            if not filename.endswith(".py"):
                continue
            if filename.startswith("_") or filename in ("base_skill.py", "skill_registry.py"):
                continue

            module_name = filename[:-3]  # quitar .py
            try:
                loaded += await self._load_module(skills_dir, module_name)
            except Exception as e:
                log.error(f"Error cargando módulo '{module_name}': {e}", exc_info=True)

        log.info(f"Skills cargados: {loaded}/{len(self._skills)} — Intents mapeados: {len(self._intent_map)}")
        return loaded

    async def _load_module(self, skills_dir: str, module_name: str) -> int:
        """Carga un módulo individual y registra sus skills."""
        loaded = 0
        full_module = f"skills.{module_name}"

        try:
            # Importar o reimportar el módulo
            if full_module in sys.modules:
                module = importlib.reload(sys.modules[full_module])
            else:
                module = importlib.import_module(full_module)
        except Exception as e:
            log.error(f"Error importando '{full_module}': {e}")
            return 0

        # Buscar clases que hereden de BaseSkill
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if (
                inspect.isclass(attr)
                and issubclass(attr, BaseSkill)
                and attr is not BaseSkill
                and not inspect.isabstract(attr)
            ):
                try:
                    skill_instance = attr()
                    if skill_instance.name in self._disabled:
                        log.debug(f"Skill deshabilitado: {skill_instance.name}")
                        continue
                    await self._register(skill_instance)
                    loaded += 1
                except Exception as e:
                    log.error(f"Error instanciando skill '{attr_name}': {e}")

        return loaded

    async def _register(self, skill: BaseSkill) -> None:
        """Registra un skill validado."""
        # Validar
        if not skill.name:
            log.warning(f"Skill sin nombre, ignorado: {skill}")
            return
        if not skill.intents:
            log.warning(f"Skill '{skill.name}' sin intents, ignorado")
            return

        # Registrar
        self._skills[skill.name] = skill

        # Mapear intents
        for intent in skill.intents:
            if intent not in self._intent_map:
                self._intent_map[intent] = []
            self._intent_map[intent].append(skill)
            # Ordenar por prioridad
            self._intent_map[intent].sort(key=lambda s: s.priority)

        # Llamar setup
        try:
            await skill.setup()
        except Exception as e:
            log.warning(f"Error en setup de '{skill.name}': {e}")

        log.debug(f"Skill registrado: '{skill.name}' → intents={skill.intents}")

    def find_by_intent(self, intent: str) -> Optional[BaseSkill]:
        """
        Encuentra el mejor skill para un intent dado.
        Retorna el de mayor prioridad (menor número).
        """
        skills = self._intent_map.get(intent, [])
        return skills[0] if skills else None

    def find_all_by_intent(self, intent: str) -> List[BaseSkill]:
        """Encuentra todos los skills que manejan un intent."""
        return list(self._intent_map.get(intent, []))

    def find_by_name(self, name: str) -> Optional[BaseSkill]:
        """Encuentra un skill por nombre."""
        return self._skills.get(name)

    def find_handler(self, context: SkillContext) -> Optional[BaseSkill]:
        """
        Encuentra el mejor skill que pueda manejar un contexto.
        Primero busca por intent, luego hace can_handle check.
        """
        # Buscar por intent
        skill = self.find_by_intent(context.intent)
        if skill and skill.can_handle(context):
            return skill

        # Fallback: preguntar a todos los skills
        for s in self._skills.values():
            if s.can_handle(context):
                return s

        return None

    def get_all_skills(self) -> Dict[str, BaseSkill]:
        """Retorna todos los skills registrados."""
        return dict(self._skills)

    def get_all_intents(self) -> List[str]:
        """Retorna todos los intents registrados."""
        return list(self._intent_map.keys())

    def get_skill_info(self) -> List[dict]:
        """Retorna información de todos los skills."""
        return [
            {
                "name": s.name,
                "description": s.description,
                "category": s.category.name,
                "intents": s.intents,
                "patterns": s.patterns,
                "examples": s.examples,
                "priority": s.priority,
                "dangerous": s.is_dangerous,
            }
            for s in self._skills.values()
        ]

    async def teardown_all(self) -> None:
        """Ejecuta teardown en todos los skills."""
        for skill in self._skills.values():
            try:
                await skill.teardown()
            except Exception as e:
                log.warning(f"Error en teardown de '{skill.name}': {e}")

    @property
    def count(self) -> int:
        return len(self._skills)

    def __repr__(self) -> str:
        return f"<SkillRegistry skills={self.count} intents={len(self._intent_map)}>"
