# 🧠 JARVIS Core — Asistente Virtual Inteligente

> **Just A Rather Very Intelligent System**  
> Sistema completo de asistente virtual para control total de PC con Windows.

---

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────┐
│                    INPUT LAYER                       │
│          CLI Terminal  │  Voice Engine               │
└──────────┬─────────────┼───────────────────────────┘
           │             │
┌──────────▼─────────────▼───────────────────────────┐
│              CORE ENGINE (asyncio)                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │  State   │  │ Event    │  │ Command Router   │  │
│  │ Manager  │  │   Bus    │  │ (NLP + Rules)    │  │
│  └──────────┘  └──────────┘  └───────┬──────────┘  │
│                                      │              │
│  ┌───────────────────────────────────▼──────────┐  │
│  │           SKILL REGISTRY                      │  │
│  │  Auto-Discovery + Plugin System               │  │
│  │  ┌─────────┐┌─────────┐┌─────────────────┐   │  │
│  │  │open_app ││close_app││system_control    │   │  │
│  │  │browser  ││file_mgr ││screenshot        │   │  │
│  │  │sys_info ││cmd_exec ││conversation      │   │  │
│  │  └─────────┘└─────────┘└─────────────────┘   │  │
│  └───────────────────────────────────────────────┘  │
│                                                      │
│  ┌──────────┐  ┌──────────┐  ┌───────────────────┐  │
│  │ Memory   │  │ Task     │  │ Background        │  │
│  │ System   │  │ Engine   │  │ Runner            │  │
│  └──────────┘  └──────────┘  └───────────────────┘  │
└──────────────────────────────────────────────────────┘
```

---

## 🚀 Instalación Rápida

### 1. Requisitos Previos
- Python 3.9+
- Windows 10/11
- pip

### 2. Instalar Dependencias

```bash
cd Jarvis_core
pip install -r requirements.txt
```

### 3. Instalar Modelo NLP (spaCy español)

```bash
python -m spacy download es_core_news_md
```

> **Nota:** Si no quieres instalar spaCy (es grande ~40MB), JARVIS funcionará con el sistema de reglas. Cambia `"use_spacy": false` en `config.json`.

### 4. Ejecutar

```bash
python main.py
```

---

## 🎮 Modos de Ejecución

```bash
# Modo texto (default)
python main.py

# Modo voz
python main.py --mode voice

# Modo híbrido
python main.py --mode hybrid

# Modo debug (logging verbose)
python main.py --debug

# Config personalizada
python main.py --config mi_config.json

# Sin banner
python main.py --no-banner
```

---

## 💬 Comandos Disponibles

### 🚀 Aplicaciones
```
abre chrome
cierra firefox
inicia spotify
lanza la calculadora
```

### 🔊 Audio
```
sube el volumen
baja el volumen
pon el volumen al 50
silencia el sistema
```

### ☀️ Brillo
```
sube el brillo
baja el brillo
pon el brillo al 70
```

### 🌐 Navegador
```
abre google.com
busca qué es python
googlea tutorial de javascript
busca en youtube música relajante
```

### 📁 Archivos
```
crea un archivo llamado notas.txt
busca archivos .py
lista los archivos del directorio actual
```

### 📸 Capturas
```
toma una captura de pantalla
haz un screenshot
```

### 📊 Sistema
```
dime el estado del CPU
cuánta RAM tengo
cómo está el disco
```

### ⚡ Comandos
```
ejecuta el comando dir
ejecuta ipconfig en cmd
corre Get-Process en powershell
```

### 💬 Conversación
```
hola jarvis
¿qué hora es?
¿qué día es hoy?
cuéntame un chiste
ayuda
adiós
```

### 🔗 Comandos Compuestos
```
abre chrome y busca tutorial de python
sube el volumen y abre spotify
```

### ⚡ Sistema
```
apaga la computadora
reinicia el equipo
bloquea la pantalla
suspende el sistema
```

---

## 🧩 Cómo Añadir Nuevas Skills

### 1. Crea un archivo en `/skills/`

```python
# skills/mi_skill.py
from typing import List
from skills.base_skill import BaseSkill, SkillCategory, SkillContext, SkillResult

class MiSkill(BaseSkill):
    @property
    def name(self) -> str:
        return "mi_skill"

    @property
    def description(self) -> str:
        return "Descripción de lo que hace mi skill"

    @property
    def intents(self) -> List[str]:
        return ["mi_intent"]

    @property
    def category(self) -> SkillCategory:
        return SkillCategory.UTILITY

    @property
    def patterns(self) -> List[str]:
        return ["palabra_clave1", "palabra_clave2"]

    @property
    def examples(self) -> List[str]:
        return ["ejemplo de comando"]

    async def execute(self, context: SkillContext) -> SkillResult:
        # Tu lógica aquí
        target = context.entities.get("target", "")
        return SkillResult.ok(f"Ejecuté mi skill con: {target}")
```

### 2. Añade patrones de intención (opcional)

Para que el clasificador NLP reconozca tu skill, puedes añadir reglas en `router/intent_classifier.py`:

```python
"mi_intent": {
    "patterns": [r"\b(palabra_clave)\b"],
    "keywords": ["palabra_clave"],
    "priority": 50,
},
```

### 3. ¡Listo!

Reinicia JARVIS y tu nuevo skill será detectado automáticamente.

---

## ⚙️ Configuración

Edita `config.json` para personalizar:

| Sección | Qué controla |
|---------|-------------|
| `jarvis` | Versión, debug, logging |
| `interaction` | Modo, wake word, prompt |
| `voice` | TTS, STT, wake word |
| `nlp` | Modelo spaCy, umbrales |
| `memory` | Persistencia, auto-save |
| `task_engine` | Concurrencia, timeouts |
| `skills` | Apps registradas, directorio |
| `ui` | Tema, colores, banner |

---

## 📁 Estructura del Proyecto

```
Jarvis_core/
├── main.py              # Entry point
├── config.json          # Configuración
├── requirements.txt     # Dependencias
├── README.md            # Este archivo
├── core/                # Motor principal
│   ├── engine.py        # Loop principal (asyncio)
│   ├── state.py         # Estado global
│   ├── event_bus.py     # Sistema pub/sub
│   └── exceptions.py    # Excepciones
├── router/              # Inteligencia NLP
│   ├── command_router.py    # Router principal
│   ├── intent_classifier.py # Clasificador de intención
│   ├── entity_extractor.py  # Extractor de entidades
│   └── pipeline_splitter.py # Divide comandos complejos
├── skills/              # Plugins de acción
│   ├── base_skill.py        # Clase base abstracta
│   ├── skill_registry.py    # Auto-descubrimiento
│   ├── open_app.py          # Abrir aplicaciones
│   ├── close_app.py         # Cerrar aplicaciones
│   ├── system_control.py    # Volumen, brillo, energía
│   ├── browser_automation.py # Navegador y búsquedas
│   ├── file_manager.py      # Gestión de archivos
│   ├── screenshot.py        # Capturas de pantalla
│   ├── system_info.py       # Info del sistema
│   ├── cmd_executor.py      # CMD/PowerShell
│   └── conversation.py      # Charla y ayuda
├── memory/              # Persistencia
│   ├── memory_manager.py
│   ├── history.py
│   └── preferences.py
├── task_engine/         # Ejecución de tareas
│   ├── task_manager.py
│   ├── scheduler.py
│   └── background.py
├── voice/               # Sistema de voz
│   ├── voice_engine.py
│   ├── tts.py
│   ├── stt.py
│   └── wake_word.py
├── ui/                  # Interfaz
│   └── terminal_ui.py
├── utils/               # Utilidades
│   ├── logger.py
│   ├── config_loader.py
│   └── helpers.py
└── data/                # Datos persistentes
    ├── history.json
    └── preferences.json
```

---

## 🛡️ Seguridad

- Comandos destructivos (`format`, `del /f`, `rmdir /s`) están bloqueados
- Acciones peligrosas (apagar PC) piden confirmación
- Logs detallados de toda actividad
- No se envían datos a internet (todo local, excepto STT de Google)

---

## 📜 Licencia

Proyecto personal. Uso libre.
