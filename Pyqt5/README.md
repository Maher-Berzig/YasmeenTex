# YasmeenTeX

**YasmeenTeX** is a desktop application for managing, viewing, and exporting LaTeX mathematical exercises, with an integrated AI assistant and KaTeX-powered rendering.

---

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [LaTeX Export](#latex-export)
- [AI Providers](#ai-providers)
- [Keyboard Shortcuts](#keyboard-shortcuts)
- [Technologies](#technologies)
- [License](#license)

---

## Features

- **LaTeX exercise management** — add, edit, delete, and search exercises with a unique keycode system (`EX-YYYYMMDD.HHMMSS.F`)
- **KaTeX rendering** — exercises and solutions rendered beautifully in an embedded web view
- **Hierarchical topic tree** — organise exercises under a three-level topic hierarchy; drag & drop to reorder
- **Advanced search** — filter by name, keycode, content, keywords, level, or topic
- **LaTeX export** — select exercises and generate a fully compilable `.tex` document with configurable layout, section structure, table of contents, and clickable cross-references between exercises and solutions
- **Print / PDF** — print the current exercise (and its solution) directly to a printer or save as PDF
- **AI assistant** — generate exercises, create solutions, and chat about mathematics using multiple AI providers
- **Offline mode** — rule-based assistant that works without an internet connection
- **Multi-language UI** — English, French, and Arabic (including full RTL layout for Arabic)
- **Database settings** — use the default database or point the app to any SQLite file at runtime
- **Statistics dialog** — live overview of your exercise collection

---

## Requirements

- Python 3.8 or later
- Windows (for the default `%APPDATA%\YasmeenTex` database location; macOS/Linux fall back to the working directory)

Python packages:

```
PyQt5>=5.15.0
PyQtWebEngine>=5.15.0
requests>=2.28.0
```

All other dependencies (`sqlite3`, `json`, `pathlib`, `datetime`, …) are part of the Python standard library.

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/Maher-Berzig/YasmeenTeX.git
cd YasmeenTeX

# 2. (Recommended) Create a virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the application
python main.py
```

> **Note for Windows users:** If you see a blank white window when the app starts, make sure your graphics drivers are up to date. PyQtWebEngine requires hardware acceleration.

---

## Usage

### Launching

```bash
python main.py
```

### Adding an exercise

1. Click **+ Add Exercise** or press `Ctrl+N`.
2. Fill in the name, LaTeX content, optional solution, level, topics, and keywords.
3. Click **OK**. The exercise receives an auto-generated keycode.

### Browsing exercises

- Click **🔍 Search Exercises** or press `Ctrl+F` to open the search dialog.
- Filter by text, level, or topic.
- Double-click a result to load it.

### Topic tree

- Click **Show Tree** to reveal the topic panel on the left.
- Right-click any topic for context-menu options (add child, rename, delete, move).
- Drag and drop topics to reorganise them.

### AI assistant

1. Open **Tools → AI Configuration** and choose a provider and model.
2. Switch to the **AI Assistant** tab.
3. Type a question or request (e.g. *"Generate an intermediate-level exercise on eigenvalues"*) and press `Ctrl+Enter` to send.

### Printing and saving as PDF

With an exercise loaded, click the **🖨 Print / PDF** button in the toolbar:

- **Print to printer…** — opens the system print dialog. If the solution panel is visible, exercise and solution are printed consecutively.
- **Save as PDF…** — saves the exercise (and, if visible, the solution as a separate file) using the built-in `QWebEnginePage.printToPdf` API. No external tools required.

### Settings

Open **Options → Settings** to change:

| Setting | Description |
|---|---|
| **Language** | English / Français / العربية |
| **Discipline** | Mathematics, Physics, Computer Science, … or a custom label used by the AI assistant |
| **Database** | Use the default `exercises.db` in `%APPDATA%\YasmeenTex`, or browse to any `.db` file |

Changing the database takes effect immediately — the application reconnects without restarting.

---

## Project Structure

```
YasmeenTeX/
│
├── main.py                  # Entry point
├── main_window.py           # Main window and application logic
├── database.py              # SQLite database manager (CRUD + topic hierarchy)
├── dialogs.py               # All QDialog subclasses (search, add/edit, settings, …)
├── export_dialog.py         # Export Exercises to LaTeX dialog
├── topic_tree.py            # Custom QTreeWidget for the topic panel
├── ai_assistant_tab.py      # AI Assistant tab widget
├── ai_config_dialog.py      # AI provider configuration dialog
├── online_ai_provider.py    # HTTP clients for each AI provider
├── latex_renderer.py        # KaTeX rendering helpers
├── katex_loader.py          # HTML builders for KaTeX-powered chat view
├── translations.py          # UI string translations (en / fr / ar)
│
├── requirements.txt
└── README.md
```

---

## Configuration

### Database

The default database is stored at:

```
%APPDATA%\YasmeenTex\exercises.db      # Windows
```

On non-Windows systems the file is created in the working directory. You can change the path at any time via **Options → Settings → Database Settings**.

All configuration files are stored inside `%APPDATA%\YasmeenTex\` alongside the default database:

```
%APPDATA%\YasmeenTex\
├── exercises.db          # default database
├── app_settings.json     # language, discipline, database path
└── ai_config.json        # AI provider, model, API key
```

On non-Windows systems all three files fall back to the directory containing `main.py`.

---

## LaTeX Export

Open **Edit → Export Exercises to LaTeX…** (`Ctrl+X`) to open the export dialog.

### Selecting exercises

The left panel works identically to the search dialog: filter by text, level, or topic, then check the exercises you want. **Select All** and **Deselect All** buttons are available, along with a live counter.

### Document title

Type a title freely, or click **↻ Auto-fill from selected topic** to generate a title of the form:

> Series of exercises with solutions of *Topic → Subtopic*

### Layout

| Option | Description |
|---|---|
| **① Interleaved** | Exercise 1 → Solution 1 → Exercise 2 → Solution 2 → … |
| **② Grouped** | All exercises first, then all solutions on a new page |

### Options

| Checkbox | Effect |
|---|---|
| Include topic tree as sections / subsections | Wraps exercises in `\section`, `\subsection`, `\subsubsection` derived from the topic path |
| Generate table of contents | Inserts `\tableofcontents` followed by `\newpage` |
| Include exercises without solutions | When unchecked, exercises that have no solution are silently skipped |

### Cross-references

Every exercise box ends with a footer line showing the keycode, difficulty level, and a clickable **[Solution]** link that jumps directly to the corresponding solution — useful in grouped mode where solutions are on separate pages. Each solution box carries a reciprocal **↑ Exercise N** back-link.

Labels follow the convention `ex:EX-YYYYMMDD-HHMMSS-F` and `sol:EX-YYYYMMDD-HHMMSS-F`.

### LaTeX corrections

`export_dialog.py` exposes a module-level `LATEX_CORRECTIONS` list applied to every exercise and solution body before the file is written. Each entry is a `(pattern, replacement, is_regex)` tuple:

```python
LATEX_CORRECTIONS = [
    # Bare # → \#  (negative lookbehind skips already-escaped \#)
    (r'(?<!\\)#',            r'\\#',               True),
    # Custom macro → standard LaTeX
    (r'\\implique\b',        r'\\implies',          True),
    # \step N → \textbf{Step N}
    (r'\\step\s+(\w+)',      r'\\textbf{Step \1}',  True),
    # Add your own below …
]
```

Set `is_regex=False` for plain string replacements; `True` enables full `re.sub` with back-references.

The generated `.tex` file compiles with a single `pdflatex` run (all packages ship with a standard TeX Live / MiKTeX installation).

---

## AI Providers

| Provider | Requires key | Notes |
|---|---|---|
| **Groq** | Yes (free tier available) | Fast inference; recommended for most users |
| **Hugging Face** | Optional | Free; slower for large models |
| **OpenAI** | Yes | GPT-4o, GPT-3.5-turbo |
| **Anthropic** | Yes | Claude 3 family |
| **Google Gemini** | Yes | Gemini Pro |
| **DeepSeek** | Yes | deepseek-chat, deepseek-reasoner |
| **Qwen (Alibaba)** | Yes | qwen-turbo, qwen-plus, qwen-max |

Get free API keys:
- Groq: https://console.groq.com
- Hugging Face: https://huggingface.co/settings/tokens
- OpenAI: https://platform.openai.com/api-keys
- Anthropic: https://console.anthropic.com
- Google AI Studio: https://aistudio.google.com
- DeepSeek: https://platform.deepseek.com
- Qwen: https://dashscope.console.aliyun.com

---

## Keyboard Shortcuts

| Shortcut | Action |
|---|---|
| `Ctrl+N` | Add exercise |
| `Ctrl+E` | Edit current exercise |
| `Ctrl+F` | Search exercises |
| `Ctrl+X` | Export exercises to LaTeX |
| `Ctrl+Enter` | Send AI chat message |
| `Delete` | Delete current exercise |
| `F5` | Refresh |
| `Ctrl+Q` | Quit |
| `Ctrl+↑` / `Ctrl+↓` | Move topic up / down |
| `Ctrl+←` / `Ctrl+→` | Promote / demote topic |

---

## Technologies

| Library | Purpose | License |
|---|---|---|
| [PyQt5](https://riverbankcomputing.com/software/pyqt/) | GUI framework | GPL v3 |
| [PyQtWebEngine](https://riverbankcomputing.com/software/pyqtwebengine/) | Embedded web view for KaTeX | GPL v3 |
| [KaTeX](https://katex.org) | Fast LaTeX math rendering in the browser | MIT |
| [requests](https://requests.readthedocs.io) | HTTP client for AI providers | Apache 2.0 |
| SQLite | Embedded database (stdlib) | Public domain |

---

## Developer

Maher Berzig

---

## License

YasmeenTeX is free software: you can redistribute it and/or modify it under the terms of the **GNU General Public License version 3** as published by the Free Software Foundation.

This program is distributed in the hope that it will be useful, but **without any warranty**; without even the implied warranty of merchantability or fitness for a particular purpose. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

> **Note on dependencies:** PyQt5 and PyQtWebEngine are licensed under the GPL v3, which is compatible with this project's licence. KaTeX is used under the [MIT License](https://github.com/KaTeX/KaTeX/blob/main/LICENSE) — Copyright (c) 2013–2020 Khan Academy and other contributors.
