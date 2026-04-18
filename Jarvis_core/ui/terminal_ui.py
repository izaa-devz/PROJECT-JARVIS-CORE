"""
JARVIS — Terminal UI (Interfaz de Terminal Hacker)
====================================================
Terminal profesional estilo hacker usando rich.
Banner ASCII, colores neón, spinners, tablas formateadas.
"""

import os
import sys
from typing import Optional
from datetime import datetime
from utils.logger import get_logger

log = get_logger("ui.terminal")

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.table import Table
    from rich.markdown import Markdown
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.theme import Theme
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    log.warning("rich no disponible — UI básica")


# Banner ASCII de JARVIS
JARVIS_BANNER = r"""
     ██╗ █████╗ ██████╗ ██╗   ██╗██╗███████╗
     ██║██╔══██╗██╔══██╗██║   ██║██║██╔════╝
     ██║███████║██████╔╝██║   ██║██║███████╗
██   ██║██╔══██║██╔══██╗╚██╗ ██╔╝██║╚════██║
╚█████╔╝██║  ██║██║  ██║ ╚████╔╝ ██║███████║
 ╚════╝ ╚═╝  ╚═╝╚═╝  ╚═╝  ╚═══╝  ╚═╝╚══════╝
"""

JARVIS_SUBTITLE = "Just A Rather Very Intelligent System"


class TerminalUI:
    """
    Interfaz de terminal profesional con tema hacker.
    
    Características:
    - Banner ASCII al iniciar
    - Colores cyan/verde neón sobre negro
    - Markdown rendering para respuestas
    - Spinners para operaciones largas
    - Tablas formateadas
    - Timestamps opcionales
    """

    def __init__(
        self,
        theme: str = "hacker",
        show_banner: bool = True,
        show_timestamps: bool = True,
        prompt_symbol: str = "❯",
    ):
        self._show_banner = show_banner
        self._show_timestamps = show_timestamps
        self._prompt_symbol = prompt_symbol

        if RICH_AVAILABLE:
            custom_theme = Theme({
                "info": "cyan",
                "warning": "yellow",
                "error": "bold red",
                "success": "bold green",
                "jarvis": "bold cyan",
                "user": "bold white",
                "dim": "dim white",
                "accent": "bold magenta",
            })
            self._console = Console(theme=custom_theme)
        else:
            self._console = None

    def show_banner(self, version: str = "1.0.0", skills_count: int = 0) -> None:
        """Muestra el banner de inicio de JARVIS."""
        if not RICH_AVAILABLE:
            print(JARVIS_BANNER)
            print(f"  {JARVIS_SUBTITLE}")
            print(f"  v{version} | {skills_count} skills cargados")
            print("=" * 60)
            return

        # Banner con rich
        banner_text = Text(JARVIS_BANNER, style="bold cyan")

        info_text = Text()
        info_text.append(f"\n  {JARVIS_SUBTITLE}\n", style="italic dim white")
        info_text.append(f"  v{version}", style="bold green")
        info_text.append(" | ", style="dim")
        info_text.append(f"{skills_count} skills", style="bold magenta")
        info_text.append(" cargados | ", style="dim")
        info_text.append(datetime.now().strftime("%d/%m/%Y %H:%M"), style="dim cyan")
        info_text.append("\n")

        panel = Panel(
            Text.assemble(banner_text, info_text),
            border_style="cyan",
            box=box.DOUBLE,
            padding=(0, 2),
        )
        self._console.print(panel)
        self._console.print()

    def show_ready(self) -> None:
        """Muestra mensaje de sistema listo."""
        if RICH_AVAILABLE:
            self._console.print(
                "  [bold green]✓[/] Sistema JARVIS [bold cyan]OPERATIVO[/]  "
                "[dim]| Escribe [bold]'ayuda'[/bold] para ver comandos | [bold]'salir'[/bold] para terminar[/dim]"
            )
            self._console.print()
        else:
            print("  ✓ Sistema JARVIS OPERATIVO | Escribe 'ayuda' para ver comandos")
            print()

    def get_input(self) -> str:
        """Obtiene input del usuario con prompt estilizado."""
        try:
            if RICH_AVAILABLE:
                timestamp = ""
                if self._show_timestamps:
                    timestamp = f"[dim]{datetime.now().strftime('%H:%M:%S')}[/dim] "

                self._console.print(
                    f"\n  {timestamp}[bold cyan]JARVIS[/] [bold white]{self._prompt_symbol}[/] ",
                    end="",
                )
                return input().strip()
            else:
                prompt = f"\n  JARVIS {self._prompt_symbol} "
                return input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            return "salir"

    def show_response(self, message: str, skill_name: str = "", duration_ms: float = 0) -> None:
        """Muestra la respuesta de JARVIS."""
        if not message:
            return

        if RICH_AVAILABLE:
            # Header de respuesta
            header_parts = ["  "]
            if self._show_timestamps:
                header_parts.append(f"[dim]{datetime.now().strftime('%H:%M:%S')}[/dim] ")
            header_parts.append("[bold cyan]╰─[/] ")

            self._console.print("".join(header_parts), end="")

            # Intentar renderizar como Markdown
            try:
                md = Markdown(message)
                self._console.print(md)
            except Exception:
                self._console.print(message)

            # Footer con metadata
            if duration_ms > 0:
                self._console.print(f"  [dim]   ⚡ {duration_ms:.0f}ms[/dim]", end="")
                if skill_name:
                    self._console.print(f" [dim]| skill: {skill_name}[/dim]", end="")
                self._console.print()

        else:
            print(f"\n  JARVIS: {message}")
            if duration_ms > 0:
                print(f"  [{duration_ms:.0f}ms]")

    def show_error(self, message: str) -> None:
        """Muestra un error."""
        if RICH_AVAILABLE:
            self._console.print(f"  [bold red]✗[/] {message}")
        else:
            print(f"  ERROR: {message}")

    def show_warning(self, message: str) -> None:
        """Muestra una advertencia."""
        if RICH_AVAILABLE:
            self._console.print(f"  [yellow]⚠[/] {message}")
        else:
            print(f"  WARNING: {message}")

    def show_info(self, message: str) -> None:
        """Muestra información."""
        if RICH_AVAILABLE:
            self._console.print(f"  [cyan]ℹ[/] {message}")
        else:
            print(f"  INFO: {message}")

    def show_processing(self, message: str = "Procesando...") -> None:
        """Muestra indicador de procesamiento."""
        if RICH_AVAILABLE:
            self._console.print(f"  [dim cyan]⟳ {message}[/]")

    def show_farewell(self) -> None:
        """Muestra mensaje de despedida."""
        if RICH_AVAILABLE:
            self._console.print()
            panel = Panel(
                "[bold cyan]Sistema JARVIS desconectado[/]\n[dim]Hasta la próxima, señor.[/]",
                border_style="dim cyan",
                box=box.ROUNDED,
                padding=(0, 2),
            )
            self._console.print(panel)
        else:
            print("\n  Sistema JARVIS desconectado. Hasta la próxima.")

    def show_table(self, title: str, headers: list, rows: list) -> None:
        """Muestra una tabla formateada."""
        if RICH_AVAILABLE:
            table = Table(title=title, box=box.SIMPLE_HEAVY, border_style="cyan")
            for header in headers:
                table.add_column(header, style="bold")
            for row in rows:
                table.add_row(*[str(cell) for cell in row])
            self._console.print(table)
        else:
            print(f"\n  {title}")
            print("  " + " | ".join(headers))
            print("  " + "-" * 60)
            for row in rows:
                print("  " + " | ".join(str(cell) for cell in row))

    def clear(self) -> None:
        """Limpia la terminal."""
        os.system("cls" if os.name == "nt" else "clear")

    def __repr__(self) -> str:
        return f"<TerminalUI rich={RICH_AVAILABLE}>"
