"""
JARVIS — Speech-to-Text (STT)
================================
Reconocimiento de voz usando SpeechRecognition.
"""

import asyncio
from typing import Optional
from utils.logger import get_logger

log = get_logger("voice.stt")


class STT:
    """
    Motor de Speech-to-Text usando SpeechRecognition.
    
    Soporta:
    - Google Speech API (default, gratis)
    - Configuración de idioma
    - Timeout configurable
    """

    def __init__(self, language: str = "es-ES", timeout: int = 5, phrase_limit: int = 10):
        self._language = language
        self._timeout = timeout
        self._phrase_limit = phrase_limit
        self._available = False

        try:
            import speech_recognition as sr
            self._recognizer = sr.Recognizer()
            self._mic_class = sr.Microphone
            self._available = True
            log.info("STT (SpeechRecognition) disponible")
        except ImportError:
            log.warning("SpeechRecognition no disponible — STT deshabilitado")

    async def initialize(self) -> bool:
        """Verifica que el micrófono funcione."""
        if not self._available:
            return False

        try:
            def check_mic():
                mic = self._mic_class()
                with mic as source:
                    self._recognizer.adjust_for_ambient_noise(source, duration=0.5)
                return True

            result = await asyncio.to_thread(check_mic)
            log.info("Micrófono inicializado y calibrado")
            return result

        except Exception as e:
            log.error(f"Error inicializando micrófono: {e}")
            self._available = False
            return False

    async def listen(self) -> Optional[str]:
        """
        Escucha el micrófono y convierte a texto.
        
        Returns:
            Texto reconocido o None si no se entendió
        """
        if not self._available:
            return None

        try:
            def do_listen():
                import speech_recognition as sr
                mic = self._mic_class()
                with mic as source:
                    log.debug("Escuchando...")
                    audio = self._recognizer.listen(
                        source,
                        timeout=self._timeout,
                        phrase_time_limit=self._phrase_limit,
                    )

                try:
                    text = self._recognizer.recognize_google(audio, language=self._language)
                    return text
                except sr.UnknownValueError:
                    log.debug("No se pudo entender el audio")
                    return None
                except sr.RequestError as e:
                    log.error(f"Error en servicio de reconocimiento: {e}")
                    return None

            text = await asyncio.to_thread(do_listen)
            if text:
                log.info(f"Reconocido: '{text}'")
            return text

        except Exception as e:
            log.error(f"Error en STT: {e}")
            return None

    @property
    def is_available(self) -> bool:
        return self._available

    def __repr__(self) -> str:
        status = "✓" if self._available else "✗"
        return f"<STT engine=google status={status} lang={self._language}>"
