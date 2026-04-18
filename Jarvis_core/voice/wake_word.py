"""
JARVIS — Wake Word Detection
===============================
Detección de "Hey Jarvis" para activar el asistente.
"""

import asyncio
from typing import Optional
from utils.logger import get_logger

log = get_logger("voice.wake_word")


class WakeWordDetector:
    """
    Detector de wake word ("Hey Jarvis").
    Usa SpeechRecognition en loop continuo para detectar la frase de activación.
    """

    def __init__(self, wake_word: str = "hey jarvis", timeout: int = 2):
        self._wake_word = wake_word.lower()
        self._timeout = timeout
        self._available = False
        self._listening = False

        try:
            import speech_recognition as sr
            self._recognizer = sr.Recognizer()
            self._mic_class = sr.Microphone
            self._available = True
        except ImportError:
            log.warning("SpeechRecognition no disponible — Wake Word deshabilitado")

    async def wait_for_wake_word(self) -> bool:
        """
        Escucha continuamente hasta detectar el wake word.
        
        Returns:
            True si se detectó el wake word
        """
        if not self._available:
            return False

        self._listening = True
        log.info(f"Esperando wake word: '{self._wake_word}'...")

        try:
            while self._listening:
                detected = await self._listen_once()
                if detected:
                    log.info(f"Wake word detectado: '{self._wake_word}'")
                    return True
                await asyncio.sleep(0.1)
        except asyncio.CancelledError:
            self._listening = False
            return False

        return False

    async def _listen_once(self) -> bool:
        """Escucha una vez y verifica si contiene el wake word."""
        try:
            def detect():
                import speech_recognition as sr
                mic = self._mic_class()
                with mic as source:
                    try:
                        audio = self._recognizer.listen(
                            source,
                            timeout=self._timeout,
                            phrase_time_limit=3,
                        )
                        text = self._recognizer.recognize_google(audio, language="es-ES")
                        return self._wake_word in text.lower()
                    except (sr.WaitTimeoutError, sr.UnknownValueError):
                        return False
                    except sr.RequestError:
                        return False

            return await asyncio.to_thread(detect)
        except Exception:
            return False

    def stop(self) -> None:
        """Detiene la detección."""
        self._listening = False

    @property
    def is_available(self) -> bool:
        return self._available

    def __repr__(self) -> str:
        status = "✓" if self._available else "✗"
        return f"<WakeWordDetector word='{self._wake_word}' status={status}>"
