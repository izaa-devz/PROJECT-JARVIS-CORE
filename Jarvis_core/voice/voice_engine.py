"""
JARVIS — Voice Engine
=======================
Motor de voz central que coordina TTS, STT y Wake Word.
"""

import asyncio
from typing import Optional
from voice.tts import TTS
from voice.stt import STT
from voice.wake_word import WakeWordDetector
from utils.logger import get_logger
from utils.config_loader import config

log = get_logger("voice.engine")


class VoiceEngine:
    """
    Motor de voz central.
    
    Coordina:
    - TTS (Text-to-Speech)
    - STT (Speech-to-Text)
    - Wake Word Detection
    """

    def __init__(self):
        voice_config = config.get("voice", default={})

        self.tts = TTS(
            rate=voice_config.get("tts_rate", 180),
            volume=voice_config.get("tts_volume", 0.9),
            voice_index=voice_config.get("tts_voice_index", 0),
        )
        self.stt = STT(
            language=voice_config.get("stt_language", "es-ES"),
            timeout=voice_config.get("stt_timeout", 5),
            phrase_limit=voice_config.get("stt_phrase_limit", 10),
        )
        self.wake_word = WakeWordDetector(
            wake_word=config.get("interaction", "wake_word", default="hey jarvis"),
            timeout=voice_config.get("wake_word_timeout", 2),
        )

        self._enabled = voice_config.get("enabled", False)
        self._wake_word_enabled = voice_config.get("wake_word_enabled", False)

    async def initialize(self) -> bool:
        """Inicializa todos los subsistemas de voz."""
        if not self._enabled:
            log.info("Sistema de voz deshabilitado en configuración")
            return False

        success = True

        tts_ok = await self.tts.initialize()
        if not tts_ok:
            log.warning("TTS no se pudo inicializar")
            success = False

        stt_ok = await self.stt.initialize()
        if not stt_ok:
            log.warning("STT no se pudo inicializar")
            success = False

        status = "operativo" if success else "parcial"
        log.info(f"Voice Engine: {status} (TTS={'✓' if tts_ok else '✗'} STT={'✓' if stt_ok else '✗'})")
        return success

    async def speak(self, text: str) -> bool:
        """Habla el texto dado."""
        if not self._enabled or not self.tts.is_available:
            return False
        return await self.tts.speak(text)

    async def listen(self) -> Optional[str]:
        """Escucha y convierte a texto."""
        if not self._enabled or not self.stt.is_available:
            return None
        return await self.stt.listen()

    async def wait_for_activation(self) -> bool:
        """Espera detección de wake word."""
        if not self._wake_word_enabled or not self.wake_word.is_available:
            return True  # Si no hay wake word, siempre activo
        return await self.wake_word.wait_for_wake_word()

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    @property
    def has_tts(self) -> bool:
        return self.tts.is_available

    @property
    def has_stt(self) -> bool:
        return self.stt.is_available

    def __repr__(self) -> str:
        return f"<VoiceEngine enabled={self._enabled} tts={self.tts} stt={self.stt}>"
