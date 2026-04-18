"""
JARVIS Skill — Conversación
==============================
Maneja saludos, despedidas, hora, fecha, chistes, ayuda, y respuestas generales.
"""

import random
from datetime import datetime
from typing import List
from skills.base_skill import BaseSkill, SkillCategory, SkillContext, SkillResult
from utils.logger import get_logger
from utils.helpers import get_time_greeting

log = get_logger("skills.conversation")


# Respuestas de conversación
GREETINGS = [
    "¡Hola! ¿En qué puedo ayudarte?",
    "{greeting}, señor. JARVIS a su servicio.",
    "¡Hey! ¿Qué necesitas?",
    "{greeting}. Estoy listo para lo que necesites.",
    "¡Hola! Sistema JARVIS operativo. ¿Qué deseas hacer?",
]

FAREWELLS = [
    "Hasta luego, señor. Fue un placer ayudarte.",
    "¡Adiós! Si necesitas algo más, aquí estaré.",
    "Nos vemos. JARVIS entrando en modo standby.",
    "¡Chao! Hasta la próxima.",
    "Hasta pronto. Cerrando sistemas...",
]

THANKS_RESPONSES = [
    "¡De nada! Para eso estoy.",
    "Con mucho gusto, señor.",
    "¡No hay de qué! ¿Necesitas algo más?",
    "Es un placer ayudarte.",
    "¡Cuando quieras!",
]

STATUS_RESPONSES = [
    "Todos los sistemas operativos. Rendimiento óptimo.",
    "Estoy funcionando perfectamente. ¿En qué puedo ayudarte?",
    "Sistema JARVIS al 100%. Listo para la acción.",
    "Todo en orden, señor. Sensores activos, skills cargados.",
]

JOKES = [
    "¿Por qué los programadores prefieren el modo oscuro? Porque la luz atrae insectos... y los bugs también. 🐛",
    "¿Qué le dijo un bit a otro? Nos vemos en el bus. 🚌",
    "Un programador va al supermercado. Su esposa le dice: 'Compra una botella de leche, y si hay huevos, compra 12.' Volvió con 12 botellas de leche. 🥛",
    "¿Cuál es el animal más viejo del mundo? La cebra, porque está en blanco y negro. 🦓",
    "¿Por qué los programadores confunden Halloween con Navidad? Porque OCT 31 = DEC 25. 🎃",
    "Hay 10 tipos de personas en el mundo: las que entienden binario y las que no. 🔢",
    "¿Cómo se llama un programador argentino? Hackermen. 💻",
    "Un SQL query entra a un bar, se acerca a dos tablas y pregunta: '¿Puedo hacer un JOIN con ustedes?' 🍺",
]


class ConversationSkill(BaseSkill):
    """Skill para interacciones conversacionales."""

    @property
    def name(self) -> str:
        return "conversation"

    @property
    def description(self) -> str:
        return "Maneja saludos, despedidas, hora, fecha, chistes y charla general"

    @property
    def intents(self) -> List[str]:
        return ["greeting", "farewell", "time_query", "date_query", "thanks", "help", "status_query", "joke"]

    @property
    def category(self) -> SkillCategory:
        return SkillCategory.CONVERSATION

    @property
    def patterns(self) -> List[str]:
        return ["hola", "adios", "hora", "fecha", "gracias", "ayuda", "chiste"]

    @property
    def examples(self) -> List[str]:
        return [
            "hola jarvis",
            "¿qué hora es?",
            "¿qué día es hoy?",
            "cuéntame un chiste",
            "gracias",
            "ayuda",
            "¿cómo estás?",
            "adiós",
        ]

    @property
    def priority(self) -> int:
        return 90  # Baja prioridad, otros skills deben tener precedencia

    async def execute(self, context: SkillContext) -> SkillResult:
        """Ejecuta la respuesta conversacional."""
        handlers = {
            "greeting": self._greeting,
            "farewell": self._farewell,
            "time_query": self._time,
            "date_query": self._date,
            "thanks": self._thanks,
            "help": self._help,
            "status_query": self._status,
            "joke": self._joke,
        }

        handler = handlers.get(context.intent)
        if handler:
            return await handler(context)
        return SkillResult.ok("No estoy seguro de qué quieres decir. Escribe 'ayuda' para ver lo que puedo hacer.")

    async def _greeting(self, context: SkillContext) -> SkillResult:
        greeting = get_time_greeting()
        response = random.choice(GREETINGS).format(greeting=greeting)
        return SkillResult.ok(f"👋 {response}")

    async def _farewell(self, context: SkillContext) -> SkillResult:
        response = random.choice(FAREWELLS)
        result = SkillResult.ok(f"👋 {response}")
        result.data = {"action": "exit"}
        return result

    async def _time(self, context: SkillContext) -> SkillResult:
        now = datetime.now()
        time_str = now.strftime("%H:%M:%S")
        return SkillResult.ok(f"🕐 Son las **{time_str}**")

    async def _date(self, context: SkillContext) -> SkillResult:
        now = datetime.now()
        days = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        months = [
            "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
            "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
        ]
        day_name = days[now.weekday()]
        month_name = months[now.month - 1]
        return SkillResult.ok(f"📅 Hoy es **{day_name} {now.day} de {month_name} del {now.year}**")

    async def _thanks(self, context: SkillContext) -> SkillResult:
        return SkillResult.ok(f"😊 {random.choice(THANKS_RESPONSES)}")

    async def _help(self, context: SkillContext) -> SkillResult:
        help_text = """🤖 **JARVIS — Comandos Disponibles**

🚀 **Aplicaciones:**
  • "abre chrome" / "cierra firefox"
  
🔊 **Audio:**
  • "sube el volumen" / "baja el volumen" / "silencia"
  
☀️ **Brillo:**
  • "sube el brillo" / "pon el brillo al 50"
  
🌐 **Navegador:**
  • "busca qué es python" / "abre google.com"
  
📁 **Archivos:**
  • "crea un archivo notas.txt" / "lista archivos"
  
📸 **Pantalla:**
  • "toma una captura de pantalla"
  
📊 **Sistema:**
  • "dime el estado del CPU" / "cuánta RAM tengo"
  
⚡ **Comandos:**
  • "ejecuta el comando dir en cmd"
  
💬 **Conversación:**
  • "¿qué hora es?" / "cuéntame un chiste"
  
⚡ **Sistema:**
  • "apaga la computadora" / "bloquea la pantalla"

💡 **Tip:** Puedes combinar comandos: "abre chrome y busca python"
🔇 **Salir:** "adiós" / "salir" / "exit"
"""
        return SkillResult.ok(help_text, speak=False)

    async def _status(self, context: SkillContext) -> SkillResult:
        response = random.choice(STATUS_RESPONSES)
        return SkillResult.ok(f"✅ {response}")

    async def _joke(self, context: SkillContext) -> SkillResult:
        joke = random.choice(JOKES)
        return SkillResult.ok(f"😄 {joke}")
