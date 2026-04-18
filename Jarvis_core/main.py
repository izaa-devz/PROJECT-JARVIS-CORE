"""
╔══════════════════════════════════════════════════════════╗
║           JARVIS Core — Main Entry Point                ║
║      Just A Rather Very Intelligent System              ║
║                                                         ║
║  Asistente virtual de control total para PC             ║
║  Arquitectura: asyncio + NLP + plugins + memoria        ║
╚══════════════════════════════════════════════════════════╝

USO:
    python main.py                  # Modo texto (default)
    python main.py --mode voice     # Modo voz
    python main.py --mode hybrid    # Modo híbrido
    python main.py --debug          # Modo debug
    python main.py --config mi_config.json  # Config personalizada
"""

import asyncio
import sys
import os
import argparse

# Forzar UTF-8 en Windows para Unicode
if sys.platform == "win32":
    os.system("")
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    os.environ.setdefault('PYTHONIOENCODING', 'utf-8')

# Asegurar que el directorio del proyecto está en sys.path
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)


def parse_args():
    """Parsea argumentos de línea de comandos."""
    parser = argparse.ArgumentParser(
        description="JARVIS — Asistente Virtual Inteligente",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python main.py                    Iniciar en modo texto
  python main.py --mode voice       Iniciar en modo voz
  python main.py --debug            Iniciar en modo debug
  python main.py --config mi_cfg.json  Usar configuración personalizada
        """,
    )
    parser.add_argument(
        "--mode",
        choices=["text", "voice", "hybrid"],
        default=None,
        help="Modo de interacción (default: config.json)",
    )
    parser.add_argument(
        "--config",
        default="config.json",
        help="Ruta al archivo de configuración (default: config.json)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Activar modo debug (logging verbose)",
    )
    parser.add_argument(
        "--no-banner",
        action="store_true",
        help="No mostrar banner de inicio",
    )
    return parser.parse_args()


async def main():
    """Entry point principal del sistema JARVIS."""
    args = parse_args()

    # Cambiar al directorio del proyecto
    os.chdir(PROJECT_DIR)

    # Importar engine (después de configurar sys.path)
    from core.engine import JarvisEngine
    from utils.config_loader import config

    # Crear engine
    engine = JarvisEngine(config_path=args.config)

    # Aplicar overrides de CLI
    if args.debug:
        config.set("jarvis", "debug", True)
        config.set("jarvis", "log_level", "DEBUG")

    if args.mode:
        config.set("interaction", "mode", args.mode)

    if args.no_banner:
        config.set("ui", "show_banner", False)

    # Iniciar
    await engine.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n  JARVIS desconectado.")
        sys.exit(0)
