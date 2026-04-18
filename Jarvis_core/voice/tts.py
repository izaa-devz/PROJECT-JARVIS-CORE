"""
JARVIS — Text-to-Speech (TTS)
================================
Síntesis de voz usando pyttsx3.
Envuelto en run_in_executor para no bloquear el event loop.
"""

import asyncio
from typing import Optional
from utils.logger import get_logger

log = get_logger("voice.tts")


class TTS:
    """
    Motor de Text-to-Speech basado en pyttsx3.
    
    Características:
    - No bloquea el event loop (usa threading)
    - Configurable: voz, velocidad, volumen
    - Soporte para español
    """

    def __init__(self, rate: int = 180, volume: float = 0.9, voice_index: int = 0):
        self._rate = rate
        self._volume = volume
        self._voice_index = voice_index
        self._available = False
        self._engine = None

        try:
            import pyttsx3
            self._available = True
            log.info("TTS (pyttsx3) disponible")
        except ImportError:
            log.warning("pyttsx3 no disponible — TTS deshabilitado")

    async def initialize(self) -> bool:
        """Inicializa el motor TTS."""
        if not self._available:
            return False

        try:
            def init_engine():
                import pyttsx3
                engine = pyttsx3.init()
                engine.setProperty("rate", self._rate)
                engine.setProperty("volume", self._volume)

                # Intentar seleccionar voz en español
                voices = engine.getProperty("voices")
                spanish_voice = None
                for voice in voices:
                    if "spanish" in voice.name.lower() or "español" in voice.name.lower() or "es" in voice.id.lower():
                        spanish_voice = voice
                        break

                if spanish_voice:
                    engine.setProperty("voice", spanish_voice.id)
                    log.info(f"Voz seleccionada: {spanish_voice.name}")
                elif voices and self._voice_index < len(voices):
                    engine.setProperty("voice", voices[self._voice_index].id)
                    log.info(f"Voz por defecto: {voices[self._voice_index].name}")

                return True

            await asyncio.to_thread(init_engine)
            return True

        except Exception as e:
            log.error(f"Error inicializando TTS: {e}")
            self._available = False
            return False

    async def speak(self, text: str) -> bool:
        """
        Sintetiza y reproduce texto como voz.
        No bloquea el event loop.
        """
        if not self._available or not text:
            return False

        try:
            def do_speak():
                import pyttsx3
                engine = pyttsx3.init()
                engine.setProperty("rate", self._rate)
                engine.setProperty("volume", self._volume)
                
                # Limpiar markdown del texto
                clean = text.replace("**", "").replace("*", "").replace("`", "").replace("#", "")
                # Eliminar emojis comunes
                for emoji in ["✅", "❌", "⚡", "🔊", "🔉", "🔇", "☀️", "🔅", "📸", "📊", "📁", "📄", "🌐", "🔍", 
                              "🖥️", "🧠", "💾", "💿", "🔋", "🔌", "👋", "😊", "😄", "🕐", "📅", "🤖", "💡", "⚠️", "⛔", "🐛"]:
                    clean = clean.replace(emoji, "")
                
                engine.say(clean.strip())
                engine.runAndWait()

            await asyncio.to_thread(do_speak)
            return True

        except Exception as e:
            log.error(f"Error en TTS: {e}")
            return False

    async def set_rate(self, rate: int) -> None:
        """Cambia la velocidad."""
        self._rate = rate

    async def set_volume(self, volume: float) -> None:
        """Cambia el volumen (0.0 - 1.0)."""
        self._volume = max(0.0, min(1.0, volume))

    @property
    def is_available(self) -> bool:
        return self._available

    def __repr__(self) -> str:
        status = "✓" if self._available else "✗"
        return f"<TTS engine=pyttsx3 status={status} rate={self._rate}>"
