"""
JARVIS Skill — Gestor de Archivos
====================================
Crear, buscar, listar archivos y directorios.
"""

import os
import asyncio
import glob
from typing import List
from skills.base_skill import BaseSkill, SkillCategory, SkillContext, SkillResult
from utils.logger import get_logger
from utils.helpers import format_bytes, sanitize_filename

log = get_logger("skills.file_manager")


class FileManagerSkill(BaseSkill):
    """Skill para gestión de archivos."""

    @property
    def name(self) -> str:
        return "file_manager"

    @property
    def description(self) -> str:
        return "Crea, busca y lista archivos y carpetas"

    @property
    def intents(self) -> List[str]:
        return ["create_file", "find_file", "list_files"]

    @property
    def category(self) -> SkillCategory:
        return SkillCategory.FILE

    @property
    def patterns(self) -> List[str]:
        return ["archivo", "fichero", "documento", "carpeta", "folder"]

    @property
    def examples(self) -> List[str]:
        return [
            "crea un archivo llamado notas.txt",
            "busca archivos .py en el escritorio",
            "lista los archivos del directorio actual",
            "crea un archivo test.txt con contenido hola mundo",
        ]

    @property
    def priority(self) -> int:
        return 15

    async def execute(self, context: SkillContext) -> SkillResult:
        """Ejecuta la acción de archivos."""
        if context.intent == "create_file":
            return await self._create_file(context)
        elif context.intent == "find_file":
            return await self._find_file(context)
        elif context.intent == "list_files":
            return await self._list_files(context)
        return SkillResult.fail("Acción de archivos no reconocida")

    async def _create_file(self, context: SkillContext) -> SkillResult:
        """Crea un archivo."""
        file_name = context.entities.get("file_name", "").strip()
        content = context.entities.get("content", "")

        if not file_name:
            return SkillResult.fail(
                "No especificaste nombre de archivo",
                message="¿Cómo quieres que se llame el archivo? Ejemplo: 'crea un archivo llamado notas.txt'",
            )

        file_name = sanitize_filename(file_name)
        # Agregar extensión si no tiene
        if "." not in file_name:
            file_name += ".txt"

        try:
            file_path = os.path.abspath(file_name)

            def create():
                os.makedirs(os.path.dirname(file_path) if os.path.dirname(file_path) != "" else ".", exist_ok=True)
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)

            await asyncio.to_thread(create)

            msg = f"📄 Archivo creado: **{file_name}**"
            if content:
                msg += f"\nContenido: \"{content[:100]}\""
            msg += f"\nRuta: `{file_path}`"

            return SkillResult.ok(msg, data={"path": file_path, "name": file_name})

        except Exception as e:
            return SkillResult.fail(str(e), message=f"❌ Error al crear archivo: {e}")

    async def _find_file(self, context: SkillContext) -> SkillResult:
        """Busca archivos."""
        query = context.entities.get("file_name", context.entities.get("target", "*.txt"))
        search_path = context.entities.get("path", os.path.expanduser("~"))

        if not query:
            return SkillResult.fail("No especificaste qué buscar")

        try:
            # Agregar wildcard si no tiene
            if "*" not in query and "?" not in query:
                query = f"*{query}*"

            pattern = os.path.join(search_path, "**", query)

            def search():
                return list(glob.glob(pattern, recursive=True))[:20]

            results = await asyncio.to_thread(search)

            if not results:
                return SkillResult.ok(f"🔍 No encontré archivos que coincidan con '{query}'")

            msg_lines = [f"🔍 Encontrados **{len(results)}** archivos:"]
            for f_path in results[:15]:
                size = os.path.getsize(f_path)
                msg_lines.append(f"  📄 `{f_path}` ({format_bytes(size)})")

            if len(results) > 15:
                msg_lines.append(f"  ... y {len(results) - 15} más")

            return SkillResult.ok("\n".join(msg_lines), data={"files": results})

        except Exception as e:
            return SkillResult.fail(str(e), message=f"❌ Error buscando archivos: {e}")

    async def _list_files(self, context: SkillContext) -> SkillResult:
        """Lista archivos de un directorio."""
        path = context.entities.get("path", ".")

        try:
            path = os.path.abspath(path)

            def list_dir():
                items = []
                for item in os.listdir(path):
                    full = os.path.join(path, item)
                    is_dir = os.path.isdir(full)
                    size = os.path.getsize(full) if not is_dir else 0
                    items.append({"name": item, "is_dir": is_dir, "size": size})
                return items

            items = await asyncio.to_thread(list_dir)

            if not items:
                return SkillResult.ok(f"📂 Directorio vacío: `{path}`")

            msg_lines = [f"📂 Contenido de `{path}`:"]
            # Directorios primero
            dirs = [i for i in items if i["is_dir"]]
            files = [i for i in items if not i["is_dir"]]

            for d in dirs[:20]:
                msg_lines.append(f"  📁 {d['name']}/")
            for f in files[:20]:
                msg_lines.append(f"  📄 {f['name']} ({format_bytes(f['size'])})")

            total = len(dirs) + len(files)
            if total > 40:
                msg_lines.append(f"  ... y {total - 40} elementos más")

            msg_lines.append(f"\n  Total: {len(dirs)} carpetas, {len(files)} archivos")

            return SkillResult.ok("\n".join(msg_lines), data={"items": items, "path": path})

        except Exception as e:
            return SkillResult.fail(str(e), message=f"❌ Error listando directorio: {e}")
