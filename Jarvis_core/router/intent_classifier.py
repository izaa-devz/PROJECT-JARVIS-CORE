"""
JARVIS — Intent Classifier (Clasificador de Intención)
========================================================
Sistema híbrido de clasificación de comandos:
1. Reglas rápidas (keywords/patterns) — prioridad máxima
2. spaCy NLP (similitud semántica, lematización)
3. Fuzzy matching (fallback)
4. Correcciones aprendidas del usuario
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from utils.logger import get_logger
from utils.helpers import normalize_text, remove_accents

log = get_logger("router.intent_classifier")

# Intentar cargar dependencias opcionales
try:
    from rapidfuzz import fuzz, process as rfprocess
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    log.warning("rapidfuzz no disponible — fuzzy matching deshabilitado")


@dataclass
class IntentMatch:
    """Resultado de una clasificación de intención."""
    intent: str
    action: str = ""
    confidence: float = 0.0
    method: str = ""  # 'rules', 'spacy', 'fuzzy', 'correction'
    matched_pattern: str = ""


# ─── Definición de intenciones y patrones en español ──────────

INTENT_RULES: Dict[str, dict] = {
    # --- Aplicaciones ---
    "open_app": {
        "patterns": [
            r"\b(abre|abrir|abreme|ejecuta|ejecutar|inicia|iniciar|lanza|lanzar|arranca|arrancar|corre|correr|pon|poner)\b",
        ],
        "keywords": ["abre", "abrir", "ejecuta", "ejecutar", "inicia", "iniciar", "lanza", "lanzar", "arranca"],
        "anti_keywords": ["archivo", "carpeta", "documento", "pagina", "web", "url", "link"],
        "priority": 10,
    },
    "close_app": {
        "patterns": [
            r"\b(cierra|cerrar|mata|matar|termina|terminar|detener|deten|para|parar|finaliza|finalizar)\b.*\b(app|aplicacion|programa|ventana|proceso)\b",
            r"\b(cierra|cerrar|mata|matar|termina|terminar|deten|detener)\b",
        ],
        "keywords": ["cierra", "cerrar", "mata", "matar", "termina", "terminar", "detener", "finaliza"],
        "priority": 10,
    },

    # --- Control del sistema ---
    "volume_up": {
        "patterns": [
            r"\b(sube|subir|aumenta|aumentar|mas|alza|alzar)\b.*\b(volumen|vol|sonido|audio)\b",
            r"\b(volumen|vol|sonido)\b.*\b(arriba|sube|mas|alto)\b",
        ],
        "keywords": [],
        "priority": 5,
    },
    "volume_down": {
        "patterns": [
            r"\b(baja|bajar|reduce|reducir|menos|disminuye|disminuir)\b.*\b(volumen|vol|sonido|audio)\b",
            r"\b(volumen|vol|sonido)\b.*\b(abajo|baja|menos|bajo)\b",
        ],
        "keywords": [],
        "priority": 5,
    },
    "volume_set": {
        "patterns": [
            r"\b(pon|poner|coloca|colocar|establece|establecer|fija|fijar)\b.*\b(volumen|vol|sonido)\b.*\b\d+",
            r"\b(volumen|vol)\b.*\b(a|al|en)\b.*\b\d+",
        ],
        "keywords": [],
        "priority": 5,
    },
    "volume_mute": {
        "patterns": [
            r"\b(silencia|silenciar|mutea|mutear|mute|calla|callar)\b",
            r"\b(quita|quitar)\b.*\b(sonido|audio|volumen)\b",
        ],
        "keywords": ["silencia", "silenciar", "mutea", "mutear", "mute"],
        "priority": 5,
    },
    "brightness_up": {
        "patterns": [
            r"\b(sube|subir|aumenta|aumentar|mas)\b.*\b(brillo|pantalla|luminosidad)\b",
            r"\b(brillo|pantalla)\b.*\b(arriba|sube|mas|alto)\b",
        ],
        "keywords": [],
        "priority": 5,
    },
    "brightness_down": {
        "patterns": [
            r"\b(baja|bajar|reduce|reducir|menos|disminuye)\b.*\b(brillo|pantalla|luminosidad)\b",
            r"\b(brillo|pantalla)\b.*\b(abajo|baja|menos|bajo)\b",
        ],
        "keywords": [],
        "priority": 5,
    },
    "brightness_set": {
        "patterns": [
            r"\b(pon|poner|establece|fija)\b.*\b(brillo)\b.*\b\d+",
            r"\b(brillo)\b.*\b(a|al|en)\b.*\b\d+",
        ],
        "keywords": [],
        "priority": 5,
    },
    "shutdown_pc": {
        "patterns": [
            r"\b(apaga|apagar)\b.*\b(pc|computador|computadora|equipo|ordenador|sistema|maquina)\b",
        ],
        "keywords": [],
        "priority": 1,
    },
    "restart_pc": {
        "patterns": [
            r"\b(reinicia|reiniciar|restart|reboot)\b.*\b(pc|computador|computadora|equipo|ordenador|sistema|maquina)\b",
            r"\b(reinicia|reiniciar|restart|reboot)\b",
        ],
        "keywords": [],
        "priority": 1,
    },
    "sleep_pc": {
        "patterns": [
            r"\b(suspende|suspender|dormir|duerme|hibernar|hiberna)\b.*\b(pc|computador|computadora|equipo|ordenador)?\b",
        ],
        "keywords": ["suspende", "suspender", "hibernar"],
        "priority": 1,
    },
    "lock_pc": {
        "patterns": [
            r"\b(bloquea|bloquear|lock)\b.*\b(pc|computador|computadora|equipo|pantalla|sesion)?\b",
        ],
        "keywords": ["bloquea", "bloquear", "lock"],
        "priority": 2,
    },

    # --- Navegador ---
    "open_url": {
        "patterns": [
            r"\b(abre|abrir|ve a|ir a|navega|navegar|visita|visitar)\b.*(https?://|www\.)",
            r"\b(abre|abrir|ve a|ir a)\b.*\.(com|org|net|io|dev|es)",
        ],
        "keywords": [],
        "priority": 8,
    },
    "search_web": {
        "patterns": [
            r"\b(busca|buscar|googlea|googlear|investiga|investigar|encuentra|encontrar)\b.*\b(en|sobre|acerca|de|que|como|por que)\b",
            r"\b(busca|buscar|googlea|googlear)\b",
        ],
        "keywords": ["busca", "buscar", "googlea", "googlear", "investiga"],
        "priority": 15,
    },

    # --- Archivos ---
    "create_file": {
        "patterns": [
            r"\b(crea|crear|genera|generar|haz|hacer)\b.*\b(archivo|fichero|documento|nota|txt|file)\b",
        ],
        "keywords": [],
        "priority": 15,
    },
    "find_file": {
        "patterns": [
            r"\b(busca|buscar|encuentra|encontrar|localiza|localizar|donde esta)\b.*\b(archivo|fichero|documento|carpeta|folder)\b",
        ],
        "keywords": [],
        "priority": 15,
    },
    "list_files": {
        "patterns": [
            r"\b(lista|listar|muestra|mostrar|enseña|ensenar)\b.*\b(archivos|ficheros|documentos|carpetas|folders|contenido)\b",
        ],
        "keywords": [],
        "priority": 15,
    },

    # --- Screenshot ---
    "take_screenshot": {
        "patterns": [
            r"\b(toma|tomar|haz|hacer|captura|capturar|saca|sacar)\b.*\b(captura|screenshot|pantallazo|foto|imagen)\b.*\b(pantalla)?\b",
            r"\b(screenshot|pantallazo|captura de pantalla)\b",
        ],
        "keywords": ["screenshot", "pantallazo", "captura"],
        "priority": 10,
    },

    # --- Info del sistema ---
    "system_info": {
        "patterns": [
            r"\b(dime|decir|muestra|mostrar|cual|cuanto|cuanta|como esta)\b.*\b(cpu|ram|memoria|disco|bateria|procesador|sistema|rendimiento|hardware)\b",
            r"\b(info|informacion|estado|status)\b.*\b(sistema|pc|computador|equipo)\b",
            r"\b(cpu|ram|memoria|disco|procesador|bateria)\b",
        ],
        "keywords": ["cpu", "ram", "memoria", "disco", "bateria", "procesador", "hardware"],
        "priority": 15,
    },

    # --- CMD / PowerShell ---
    "execute_cmd": {
        "patterns": [
            r"\b(ejecuta|ejecutar|corre|correr|run)\b.*\b(comando|cmd|powershell|terminal|consola|shell)\b",
            r"\b(en|por)\b.*\b(cmd|powershell|terminal|consola)\b",
        ],
        "keywords": [],
        "priority": 20,
    },

    # --- Conversación ---
    "greeting": {
        "patterns": [
            r"^(hola|hey|buenas|buenos dias|buenas tardes|buenas noches|saludos|que tal|hi|hello)\b",
        ],
        "keywords": ["hola", "hey", "buenas", "saludos"],
        "priority": 90,
    },
    "farewell": {
        "patterns": [
            r"\b(adios|chao|chau|hasta luego|nos vemos|bye|exit|salir|quit|apagar jarvis)\b",
        ],
        "keywords": ["adios", "chao", "chau", "salir", "exit", "quit", "bye"],
        "priority": 5,
    },
    "time_query": {
        "patterns": [
            r"\b(que hora|hora actual|dime la hora|hora es)\b",
        ],
        "keywords": [],
        "priority": 30,
    },
    "date_query": {
        "patterns": [
            r"\b(que dia|que fecha|dia es hoy|fecha actual|fecha de hoy)\b",
        ],
        "keywords": [],
        "priority": 30,
    },
    "thanks": {
        "patterns": [
            r"\b(gracias|thank|thanks|merci|agradezco|te agradezco)\b",
        ],
        "keywords": ["gracias", "thanks"],
        "priority": 90,
    },
    "help": {
        "patterns": [
            r"\b(ayuda|help|que puedes hacer|que sabes hacer|comandos|habilidades|skills)\b",
        ],
        "keywords": ["ayuda", "help"],
        "priority": 80,
    },
    "status_query": {
        "patterns": [
            r"\b(como estas|que tal estas|estado del sistema|status)\b",
        ],
        "keywords": [],
        "priority": 90,
    },
    "joke": {
        "patterns": [
            r"\b(chiste|broma|joke|cuentame algo|dime algo gracioso|hazme reir)\b",
        ],
        "keywords": ["chiste", "broma"],
        "priority": 90,
    },
}


class IntentClassifier:
    """
    Clasificador de intención híbrido.
    
    Pipeline:
    1. Correcciones aprendidas (máxima prioridad)
    2. Reglas basadas en patrones regex
    3. spaCy NLP (similitud semántica)
    4. Fuzzy matching (última opción)
    """

    def __init__(self, spacy_model: str = "es_core_news_md", use_spacy: bool = True, fuzzy_threshold: int = 70):
        self._nlp = None
        self._spacy_model = spacy_model
        self._use_spacy = use_spacy
        self._fuzzy_threshold = fuzzy_threshold
        self._corrections: Dict[str, str] = {}  # command -> correct_intent

        # Intentar cargar spaCy
        if use_spacy:
            try:
                import spacy
                self._nlp = spacy.load(spacy_model)
                log.info(f"spaCy cargado: modelo '{spacy_model}'")
            except Exception as e:
                log.warning(f"spaCy no disponible ({e}). Usando solo reglas.")
                self._nlp = None

    def load_corrections(self, corrections: List[dict]) -> None:
        """Carga correcciones aprendidas del usuario."""
        for c in corrections:
            self._corrections[c["command"].lower()] = c["correct_intent"]
        if corrections:
            log.debug(f"Cargadas {len(corrections)} correcciones de intención")

    def classify(self, text: str) -> IntentMatch:
        """
        Clasifica un texto en una intención.
        
        Args:
            text: Texto del usuario (raw)
            
        Returns:
            IntentMatch con intent, confidence, y método utilizado
        """
        normalized = normalize_text(text)

        # 1. Verificar correcciones aprendidas
        correction = self._corrections.get(normalized)
        if correction:
            log.debug(f"Corrección encontrada para '{text}' → {correction}")
            return IntentMatch(
                intent=correction,
                confidence=1.0,
                method="correction",
                matched_pattern=normalized,
            )

        # 2. Reglas basadas en patrones regex
        rule_match = self._match_rules(normalized)
        if rule_match and rule_match.confidence >= 0.7:
            return rule_match

        # 3. spaCy NLP
        if self._nlp:
            spacy_match = self._match_spacy(normalized)
            if spacy_match and spacy_match.confidence > 0.6:
                # Si rule_match existe pero con baja confianza, comparar
                if rule_match and rule_match.confidence > spacy_match.confidence:
                    return rule_match
                return spacy_match

        # 4. Fuzzy matching
        if RAPIDFUZZ_AVAILABLE:
            fuzzy_match = self._match_fuzzy(normalized)
            if fuzzy_match:
                # Preferir rule_match si existe
                if rule_match and rule_match.confidence >= fuzzy_match.confidence:
                    return rule_match
                return fuzzy_match

        # 5. Retornar rule_match con baja confianza si existe
        if rule_match:
            return rule_match

        # 6. No se encontró nada
        return IntentMatch(intent="unknown", confidence=0.0, method="none")

    def _match_rules(self, text: str) -> Optional[IntentMatch]:
        """Matching basado en reglas regex y keywords."""
        best_match: Optional[IntentMatch] = None
        best_score: float = 0.0

        for intent, rules in INTENT_RULES.items():
            score = 0.0
            matched_pattern = ""

            # Verificar anti-keywords (si existen, reducen la confianza)
            anti_keywords = rules.get("anti_keywords", [])
            has_anti = any(kw in text for kw in anti_keywords)

            # Patterns (regex)
            for pattern in rules.get("patterns", []):
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    pattern_score = 0.85
                    if has_anti:
                        pattern_score *= 0.5
                    if pattern_score > score:
                        score = pattern_score
                        matched_pattern = pattern
                    break

            # Keywords (simple)
            if not matched_pattern:
                for keyword in rules.get("keywords", []):
                    if keyword in text.split():
                        kw_score = 0.65
                        if has_anti:
                            kw_score *= 0.5
                        if kw_score > score:
                            score = kw_score
                            matched_pattern = keyword

            # Comparar con mejor match actual (considerando prioridad)
            if score > 0 and (score > best_score or
                (score == best_score and rules.get("priority", 50) < 
                 INTENT_RULES.get(best_match.intent, {}).get("priority", 50) if best_match else True)):
                best_score = score
                best_match = IntentMatch(
                    intent=intent,
                    confidence=score,
                    method="rules",
                    matched_pattern=matched_pattern,
                )

        return best_match

    def _match_spacy(self, text: str) -> Optional[IntentMatch]:
        """Matching usando spaCy NLP."""
        if not self._nlp:
            return None

        try:
            doc = self._nlp(text)

            # Extraer lemas y tokens significativos
            tokens = [token.lemma_.lower() for token in doc if not token.is_stop and not token.is_punct]

            # Mapeo de lemas a intents
            lemma_intents = {
                "abrir": "open_app",
                "cerrar": "close_app",
                "buscar": "search_web",
                "crear": "create_file",
                "capturar": "take_screenshot",
                "ejecutar": "execute_cmd",
                "silenciar": "volume_mute",
                "apagar": "shutdown_pc",
                "reiniciar": "restart_pc",
                "bloquear": "lock_pc",
                "suspender": "sleep_pc",
            }

            for token in tokens:
                if token in lemma_intents:
                    return IntentMatch(
                        intent=lemma_intents[token],
                        confidence=0.75,
                        method="spacy",
                        matched_pattern=f"lemma:{token}",
                    )

        except Exception as e:
            log.debug(f"Error en spaCy matching: {e}")

        return None

    def _match_fuzzy(self, text: str) -> Optional[IntentMatch]:
        """Matching usando fuzzy string comparison."""
        if not RAPIDFUZZ_AVAILABLE:
            return None

        # Crear lista de ejemplos por intent para comparar
        intent_examples = {
            "open_app": ["abre la aplicacion", "abrir programa", "ejecutar app", "iniciar aplicacion"],
            "close_app": ["cierra la aplicacion", "cerrar programa", "matar proceso", "terminar app"],
            "search_web": ["buscar en internet", "buscar en google", "googlear algo", "buscar informacion"],
            "take_screenshot": ["tomar captura de pantalla", "hacer screenshot", "capturar pantalla"],
            "system_info": ["informacion del sistema", "estado del cpu", "cuanta memoria hay"],
            "volume_up": ["subir el volumen", "mas volumen", "aumentar sonido"],
            "volume_down": ["bajar el volumen", "menos volumen", "reducir sonido"],
            "brightness_up": ["subir el brillo", "mas brillo", "aumentar brillo"],
            "brightness_down": ["bajar el brillo", "menos brillo", "reducir brillo"],
            "create_file": ["crear un archivo", "generar documento", "hacer un archivo"],
            "greeting": ["hola jarvis", "buenos dias", "buenas tardes", "que tal"],
            "farewell": ["adios jarvis", "hasta luego", "chao", "nos vemos"],
            "help": ["que puedes hacer", "ayuda", "comandos disponibles"],
        }

        best_intent = ""
        best_score = 0.0
        best_example = ""

        for intent, examples in intent_examples.items():
            for example in examples:
                score = fuzz.ratio(text, example) / 100.0
                if score > best_score:
                    best_score = score
                    best_intent = intent
                    best_example = example

        if best_score >= self._fuzzy_threshold / 100.0:
            return IntentMatch(
                intent=best_intent,
                confidence=best_score * 0.8,  # Reducir confianza para fuzzy
                method="fuzzy",
                matched_pattern=best_example,
            )

        return None

    def get_all_intents(self) -> List[str]:
        """Retorna todos los intents configurados."""
        return list(INTENT_RULES.keys())

    def __repr__(self) -> str:
        spacy_status = "✓" if self._nlp else "✗"
        fuzzy_status = "✓" if RAPIDFUZZ_AVAILABLE else "✗"
        return f"<IntentClassifier rules={len(INTENT_RULES)} spaCy={spacy_status} fuzzy={fuzzy_status}>"
