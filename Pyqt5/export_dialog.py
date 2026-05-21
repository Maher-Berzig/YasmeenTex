"""
export_dialog.py: Dialog for selecting exercises and exporting to a LaTeX document.
"""
import re

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QGroupBox, QListWidget, QListWidgetItem,
    QComboBox, QCheckBox, QRadioButton, QSplitter, QFileDialog,
    QButtonGroup, QMessageBox, QWidget
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


# ══════════════════════════════════════════════════════════════════════════════
# LATEX CORRECTIONS DICTIONARY
# ══════════════════════════════════════════════════════════════════════════════
# Applied IN ORDER to every piece of LaTeX content (exercises and solutions)
# before the .tex file is written.
#
# Each entry is a tuple:  (pattern, replacement, is_regex)
#
#   is_regex=False  →  plain string replacement  (fast, no special chars)
#   is_regex=True   →  re.sub(pattern, replacement, text, flags=re.MULTILINE)
#                       Back-references \1 \2 … are available.
#
# Add new rows as you discover issues.  Order matters: earlier rules run first.
# ══════════════════════════════════════════════════════════════════════════════

LATEX_CORRECTIONS = [
    # ── Special characters ────────────────────────────────────────────────
    # Bare # (not already escaped) → \#
    # The negative lookbehind (?<!\\) prevents double-escaping \# → \\#
    (r'(?<!\\)#',                       r'\\#',                  True),

    # ── Custom macros → standard LaTeX ───────────────────────────────────
    (r'\\implique\b',                   r'\\implies',            True),

    # ── Formatting conventions ────────────────────────────────────────────
    # \step N  (number or word after \step)  →  \textbf{Step N}
    (r'\\step\s+(\w+)',                 r'\\textbf{Step \1}',    True),

    # ── Add your own corrections below ───────────────────────────────────
    # Examples:
    #   Plain replacement:
    #     ('\\abs',           '\\left|#1\\right|',   False),
    #   Regex with back-reference:
    #     (r'\\vect\{([^}]+)\}',  r'\\vec{\1}',      True),
]


class ExportExercisesDialog(QDialog):
    """
    Select exercises (with filtering / search identical to SearchDialog)
    and generate a fully compilable .tex document with configurable layout.
    """

    def __init__(self, parent=None, db=None):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.db = db
        self._flat_topics = []          # [(id, display_label, path_list), …]

        self.setWindowTitle("Export Exercises to LaTeX")
        self.setMinimumSize(980, 680)
        self.resize(1080, 730)

        self._build_ui()
        self._populate_filters()
        self._run_search()              # show all exercises on first open

    # ──────────────────────────────────────────────────────────────────────
    # UI CONSTRUCTION
    # ──────────────────────────────────────────────────────────────────────

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(8)

        hdr = QLabel("Select exercises and configure the LaTeX document")
        hdr.setFont(QFont("Segoe UI", 10, QFont.Bold))
        root.addWidget(hdr)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self._build_left())
        splitter.addWidget(self._build_right())
        splitter.setSizes([580, 440])
        root.addWidget(splitter, 1)

        # Close button
        bot = QHBoxLayout()
        bot.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setFixedWidth(90)
        close_btn.clicked.connect(self.reject)
        bot.addWidget(close_btn)
        root.addLayout(bot)

    # ── Left panel: search + checklist ────────────────────────────────────

    def _build_left(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 8, 0)
        lay.setSpacing(6)

        # Search bar
        srow = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search by name, keycode or keyword …")
        self.search_edit.returnPressed.connect(self._run_search)
        sb = QPushButton("🔍 Search")
        sb.clicked.connect(self._run_search)
        srow.addWidget(self.search_edit)
        srow.addWidget(sb)
        lay.addLayout(srow)

        # Filters row
        frow = QHBoxLayout()
        frow.addWidget(QLabel("Level:"))
        self.level_combo = QComboBox()
        self.level_combo.setMinimumWidth(100)
        self.level_combo.currentIndexChanged.connect(self._run_search)
        frow.addWidget(self.level_combo)
        frow.addSpacing(8)
        frow.addWidget(QLabel("Topic:"))
        self.topic_combo = QComboBox()
        self.topic_combo.setMinimumWidth(220)
        self.topic_combo.currentIndexChanged.connect(self._on_topic_changed)
        frow.addWidget(self.topic_combo)
        frow.addStretch()
        lay.addLayout(frow)

        # Checkable exercise list
        self.list_widget = QListWidget()
        self.list_widget.setSelectionMode(QListWidget.NoSelection)
        self.list_widget.itemChanged.connect(self._update_sel_label)
        lay.addWidget(self.list_widget, 1)

        # Select / deselect row
        brow = QHBoxLayout()
        sa = QPushButton("Select All")
        sa.clicked.connect(self._select_all)
        da = QPushButton("Deselect All")
        da.clicked.connect(self._deselect_all)
        self.sel_label = QLabel("0 selected")
        brow.addWidget(sa)
        brow.addWidget(da)
        brow.addStretch()
        brow.addWidget(self.sel_label)
        lay.addLayout(brow)

        return w

    # ── Right panel: export options ───────────────────────────────────────

    def _build_right(self):
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(8, 0, 0, 0)
        lay.setSpacing(10)

        # ── Title ──────────────────────────────────────────────────────────
        tg = QGroupBox("Document Title")
        tg_lay = QVBoxLayout(tg)
        self.title_edit = QLineEdit("Series of Exercises")
        tg_lay.addWidget(self.title_edit)
        auto_btn = QPushButton("↻  Auto-fill from selected topic")
        auto_btn.clicked.connect(lambda: self._auto_fill_title())
        tg_lay.addWidget(auto_btn)
        lay.addWidget(tg)

        # ── Layout ─────────────────────────────────────────────────────────
        lg = QGroupBox("Exercise / Solution Layout")
        lg_lay = QVBoxLayout(lg)
        self.rb_interleaved = QRadioButton(
            "① Interleaved\n"
            "    Exercise 1 → Solution 1 → Exercise 2 → Solution 2 → …"
        )
        self.rb_interleaved.setChecked(True)
        self.rb_grouped = QRadioButton(
            "② Grouped\n"
            "    Exercise 1, Exercise 2, … → Solution 1, Solution 2, …"
        )
        self._btn_grp = QButtonGroup(self)
        self._btn_grp.addButton(self.rb_interleaved, 0)
        self._btn_grp.addButton(self.rb_grouped, 1)
        lg_lay.addWidget(self.rb_interleaved)
        lg_lay.addWidget(self.rb_grouped)
        lay.addWidget(lg)

        # ── Options ────────────────────────────────────────────────────────
        og = QGroupBox("Options")
        og_lay = QVBoxLayout(og)
        self.tree_cb = QCheckBox("Include topic tree as sections / subsections")
        self.tree_cb.setChecked(True)
        self.toc_cb = QCheckBox("Generate table of contents")
        self.toc_cb.setChecked(True)
        self.nosol_cb = QCheckBox("Include exercises that have no solution")
        self.nosol_cb.setChecked(True)
        og_lay.addWidget(self.tree_cb)
        og_lay.addWidget(self.toc_cb)
        og_lay.addWidget(self.nosol_cb)
        lay.addWidget(og)

        lay.addStretch()

        # ── Generate button ────────────────────────────────────────────────
        gen_btn = QPushButton("⬇  Generate .tex Document")
        gen_btn.setMinimumHeight(42)
        gen_btn.setFont(QFont("Segoe UI", 10, QFont.Bold))
        gen_btn.setStyleSheet(
            "QPushButton{background:#0078d4;color:white;border-radius:5px;padding:6px 12px}"
            "QPushButton:hover{background:#005ea2}"
            "QPushButton:pressed{background:#004880}"
        )
        gen_btn.clicked.connect(self._generate)
        lay.addWidget(gen_btn)

        return w

    # ──────────────────────────────────────────────────────────────────────
    # FILTER / SEARCH
    # ──────────────────────────────────────────────────────────────────────

    def _populate_filters(self):
        """Fill level and topic combo boxes from the database."""
        self.level_combo.addItem("All levels", None)
        for level in self.db.get_all_levels():
            self.level_combo.addItem(level, level)

        self.topic_combo.addItem("All topics", None)
        self._walk_topics(self.db.get_topic_tree(), depth=0, path=[])
        for tid, label, _path in self._flat_topics:
            self.topic_combo.addItem(label, tid)

    def _walk_topics(self, nodes, depth, path):
        prefix = "  " * depth + ("└ " if depth > 0 else "")
        for n in nodes:
            p = path + [n['name']]
            self._flat_topics.append((n['id'], prefix + n['name'], p))
            if n.get('children'):
                self._walk_topics(n['children'], depth + 1, p)

    def _run_search(self):
        query  = self.search_edit.text().strip()
        level  = self.level_combo.currentData()
        tid    = self.topic_combo.currentData()
        t_ids  = [tid] if tid else None

        rows = self.db.search_exercises(query=query, level=level, topic_ids=t_ids)

        self.list_widget.blockSignals(True)
        self.list_widget.clear()
        for ex_id, keycode, name, lvl, date in rows:
            label = f"{keycode}  —  {name}" + (f"  [{lvl}]" if lvl else "")
            item  = QListWidgetItem(label)
            item.setData(Qt.UserRole, ex_id)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.list_widget.addItem(item)
        self.list_widget.blockSignals(False)
        self._update_sel_label()

    def _on_topic_changed(self):
        self._run_search()
        title = self.title_edit.text().strip()
        if not title or title.startswith("Series of Exercises"):
            self._auto_fill_title(silent=True)

    def _auto_fill_title(self, silent=False):
        tid = self.topic_combo.currentData()
        if tid:
            path = self.db.get_topic_path(tid)
            section = " – ".join(path) if path else "Selected Topic"
            self.title_edit.setText(
                f"Series of exercises with solutions of {section}"
            )
        else:
            self.title_edit.setText("Series of Exercises with Solutions")

    # ──────────────────────────────────────────────────────────────────────
    # SELECTION HELPERS
    # ──────────────────────────────────────────────────────────────────────

    def _select_all(self):
        self.list_widget.blockSignals(True)
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setCheckState(Qt.Checked)
        self.list_widget.blockSignals(False)
        self._update_sel_label()

    def _deselect_all(self):
        self.list_widget.blockSignals(True)
        for i in range(self.list_widget.count()):
            self.list_widget.item(i).setCheckState(Qt.Unchecked)
        self.list_widget.blockSignals(False)
        self._update_sel_label()

    def _update_sel_label(self):
        n = sum(
            1 for i in range(self.list_widget.count())
            if self.list_widget.item(i).checkState() == Qt.Checked
        )
        self.sel_label.setText(f"{n} selected")

    def _get_checked_ids(self):
        return [
            self.list_widget.item(i).data(Qt.UserRole)
            for i in range(self.list_widget.count())
            if self.list_widget.item(i).checkState() == Qt.Checked
        ]

    # ──────────────────────────────────────────────────────────────────────
    # GENERATION
    # ──────────────────────────────────────────────────────────────────────

    def _generate(self):
        ids = self._get_checked_ids()
        if not ids:
            QMessageBox.warning(self, "Nothing selected",
                                "Please check at least one exercise.")
            return

        title       = self.title_edit.text().strip() or "Series of Exercises"
        interleaved = self.rb_interleaved.isChecked()
        use_tree    = self.tree_cb.isChecked()
        use_toc     = self.toc_cb.isChecked()
        incl_nosol  = self.nosol_cb.isChecked()

        # Fetch full exercise data from the database
        exercises = []
        for eid in ids:
            row = self.db.get_exercise(eid)
            if row is None:
                continue
            eid2, keycode, name, latex, solution, date, level = row
            has_sol = bool(solution and solution.strip())
            if not incl_nosol and not has_sol:
                continue
            tids  = self.db.get_exercise_topics(eid2)
            tpath = self.db.get_topic_path(tids[0]) if tids else []
            exercises.append({
                'id':       eid2,
                'keycode':  keycode,
                'name':     name,
                'latex':    latex    or '',
                'solution': solution or '',
                'level':    level,
                'path':     tpath,
            })

        if not exercises:
            QMessageBox.warning(
                self, "Nothing to export",
                "No exercises matched the export criteria.\n"
                "(All selected exercises may lack solutions while "
                "\"Include exercises without solutions\" is unchecked.)"
            )
            return

        doc = self._build_document(exercises, title, interleaved, use_tree, use_toc)

        # Pick a save location
        safe  = "".join(c if c.isalnum() or c in " _-" else "_" for c in title)
        default = safe.replace(" ", "_")[:60] + ".tex"
        path, _ = QFileDialog.getSaveFileName(
            self, "Save LaTeX Document", default,
            "LaTeX files (*.tex);;All files (*)"
        )
        if not path:
            return

        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(doc)
            QMessageBox.information(
                self, "Saved",
                f"LaTeX document saved:\n{path}\n\n"
                f"{len(exercises)} exercise(s) exported.\n\n"
                "Compile with:\n  pdflatex \"" + path + "\""
            )
        except OSError as exc:
            QMessageBox.critical(self, "Save Error", str(exc))

    # ──────────────────────────────────────────────────────────────────────
    # LaTeX DOCUMENT BUILDER
    # ──────────────────────────────────────────────────────────────────────

    def _build_document(self, exercises, title, interleaved, use_tree, use_toc):
        L = []

        # ── Preamble ──────────────────────────────────────────────────────
        L += [
            r"\documentclass[12pt,a4paper]{article}",
            r"\usepackage[utf8]{inputenc}",
            r"\usepackage[T1]{fontenc}",
            r"\usepackage{amsmath,amssymb,amsthm}",
            r"\usepackage{geometry}",
            r"\usepackage{enumitem}",
            r"\usepackage[dvipsnames]{xcolor}",
            r"\usepackage{mdframed}",
            r"\usepackage[hidelinks]{hyperref}",
            r"\hypersetup{",
            r"  colorlinks=true,",
            r"  linkcolor=blue!60!black,",
            r"  urlcolor=blue!60!black}",
            r"\geometry{margin=2.5cm}",
            r"",
            r"% ── Theorem environments ─────────────────────────────────────",
            r"\newtheoremstyle{exstyle}",
            r"  {8pt}{8pt}{\normalfont}{0pt}",
            r"  {\bfseries\color{blue!70!black}}{.}{.5em}{}",
            r"\theoremstyle{exstyle}",
            r"\newtheorem{exercise}{Exercise}",
            r"",
            r"\newtheoremstyle{solstyle}",
            r"  {8pt}{8pt}{\normalfont}{0pt}",
            r"  {\bfseries\color{OliveGreen}}{.}{.5em}{}",
            r"\theoremstyle{solstyle}",
            r"\newtheorem*{solution}{Solution}",
            r"",
            r"% ── Frame styles ─────────────────────────────────────────────",
            r"\mdfdefinestyle{exbox}{%",
            r"  linecolor=blue!40, backgroundcolor=blue!4,",
            r"  linewidth=0.6pt, roundcorner=4pt,",
            r"  skipabove=8pt, skipbelow=4pt,",
            r"  innerleftmargin=8pt, innerrightmargin=8pt,",
            r"  innertopmargin=6pt, innerbottommargin=6pt}",
            r"\mdfdefinestyle{solbox}{%",
            r"  linecolor=OliveGreen!70, backgroundcolor=OliveGreen!5,",
            r"  linewidth=0.6pt, roundcorner=4pt,",
            r"  skipabove=4pt, skipbelow=8pt,",
            r"  innerleftmargin=8pt, innerrightmargin=8pt,",
            r"  innertopmargin=6pt, innerbottommargin=6pt}",
            r"",
            r"\title{\bfseries " + self._esc(title) + r"}",
            r"\date{}",
            r"\author{}",
            r"",
            r"\begin{document}",
            r"\maketitle",
            r"\thispagestyle{empty}",
        ]

        if use_toc:
            L += [r"\tableofcontents", r"\newpage"]
        else:
            L.append(r"")

        # ── Body ──────────────────────────────────────────────────────────
        if interleaved:
            L += self._body_interleaved(exercises, use_tree)
        else:
            L += self._body_grouped(exercises, use_tree)

        L += [r"", r"\end{document}", ""]
        return "\n".join(L)

    # ── Body strategies ───────────────────────────────────────────────────

    def _body_interleaved(self, exercises, use_tree):
        """Exercise 1 + Solution 1, Exercise 2 + Solution 2, …"""
        L = []
        last_path = []
        for i, ex in enumerate(exercises, 1):
            if use_tree:
                hdrs, last_path = self._section_hdrs(ex['path'], last_path)
                L += hdrs
            L += self._ex_block(ex, i)
            if ex['solution'].strip():
                L += self._sol_block(ex, i)
        return L

    def _body_grouped(self, exercises, use_tree):
        """All exercises first, then all solutions."""
        L = [r"", r"% ═══════════════════════════════════════════════════════════",
             r"\section*{Exercises}"]
        last_path = []
        for i, ex in enumerate(exercises, 1):
            if use_tree:
                hdrs, last_path = self._section_hdrs(ex['path'], last_path, base=1)
                L += hdrs
            L += self._ex_block(ex, i)

        # Solutions half
        sol_exercises = [ex for ex in exercises if ex['solution'].strip()]
        if sol_exercises:
            L += [r"", r"\newpage",
                  r"% ═══════════════════════════════════════════════════════════",
                  r"\section*{Solutions}"]
            last_path = []
            for i, ex in enumerate(exercises, 1):   # keep original numbering
                if not ex['solution'].strip():
                    continue
                if use_tree:
                    hdrs, last_path = self._section_hdrs(ex['path'], last_path, base=1)
                    L += hdrs
                L += self._sol_block(ex, i)
        return L

    # ── Section headers ───────────────────────────────────────────────────

    def _section_hdrs(self, path, last_path, base=0):
        """Emit \\section / \\subsection / \\subsubsection where the path diverges."""
        cmds = [r"\section", r"\subsection", r"\subsubsection", r"\paragraph"]
        L = []
        n   = max(len(path), len(last_path))
        p1  = (path       + [None] * n)[:n]
        p2  = (last_path  + [None] * n)[:n]
        for depth, (new, old) in enumerate(zip(p1, p2)):
            if new is None:
                break
            if new != old:
                idx = min(base + depth, len(cmds) - 1)
                L.append(f"\n{cmds[idx]}{{{self._esc(new)}}}\n")
        return L, list(path)

    # ── Block builders ────────────────────────────────────────────────────

    @staticmethod
    def _kc_label(keycode):
        """Convert a keycode to a safe LaTeX label fragment (no dots)."""
        return keycode.replace('.', '-')

    def _ex_block(self, ex, number):
        name      = self._esc(ex['name'])
        kc        = ex['keycode']
        kc_safe   = self._kc_label(kc)
        ex_label  = "ex:"  + kc_safe
        sol_label = "sol:" + kc_safe
        has_sol   = bool(ex['solution'].strip())

        # ── Footer line (last line of the exercise box) ───────────────────
        # Layout:  {\footnotesize\texttt{KEYCODE}}  \hfill  [Level]  [Solution]
        footer_kc  = rf"{{\footnotesize\texttt{{{kc}}}}}"
        footer_lvl = (rf"\quad{{\small\textit{{{self._esc(ex['level'])}}}}}"
                      if ex.get('level') else "")
        footer_sol = (rf"\quad\hyperref[{sol_label}]{{\small\textcolor{{OliveGreen}}{{[Solution]}}}}"
                      if has_sol else "")
        footer = (
            r"\par\medskip"
            r"\noindent{\color{blue!25}\rule{\linewidth}{0.4pt}}\\[-4pt]"
            "\n"
            rf"\noindent{footer_kc}\hfill{footer_lvl}{footer_sol}"
        )

        return [
            "",
            r"\begin{mdframed}[style=exbox]",
            rf"\begin{{exercise}}[{name}]",
            rf"\label{{{ex_label}}}",
            self._clean_latex(ex['latex']),
            footer,
            r"\end{exercise}",
            r"\end{mdframed}",
        ]

    def _sol_block(self, ex, number):
        name      = self._esc(ex['name'])
        sol_label = "sol:" + self._kc_label(ex['keycode'])
        # Back-link to the exercise box
        ex_label  = "ex:"  + self._kc_label(ex['keycode'])
        backref   = (rf"\hfill{{\footnotesize"
                     rf"\hyperref[{ex_label}]{{\textcolor{{blue!60!black}}{{↑ Exercise {number}}}}}"
                     rf"}}")
        return [
            "",
            r"\begin{mdframed}[style=solbox]",
            rf"\begin{{solution}}[Exercise~{number}: {name}]",
            rf"\label{{{sol_label}}}%",   # label on its own line; % hides the newline
            self._clean_latex(ex['solution']),
            backref,
            r"\end{solution}",
            r"\end{mdframed}",
        ]

    # ── Utilities ─────────────────────────────────────────────────────────

    @staticmethod
    def _apply_corrections(text):
        """
        Apply every entry in LATEX_CORRECTIONS to *text* in order.
        Called on exercise and solution bodies before writing the .tex file.
        """
        for pattern, replacement, is_regex in LATEX_CORRECTIONS:
            if is_regex:
                text = re.sub(pattern, replacement, text, flags=re.MULTILINE)
            else:
                text = text.replace(pattern, replacement)
        return text

    # Display-math environments that must NEVER appear inside $ or $$
    _DISPLAY_ENVS = (
        r'align\*?', r'equation\*?', r'gather\*?', r'multline\*?',
        r'flalign\*?', r'alignat(?:\{[^}]*\})?\*?', r'eqnarray\*?',
        r'cases', r'split', r'subequations',
    )

    @classmethod
    def _clean_latex(cls, text):
        """
        Strip $ or $$ that incorrectly wrap display-math environments, then
        apply all entries from LATEX_CORRECTIONS.

        Examples fixed:
          $\\begin{align*} … \\end{align*}$   →  \\begin{align*} … \\end{align*}
          $$\\begin{equation} … \\end{equation}$$  →  \\begin{equation} … \\end{equation}
        """
        env_pat = '|'.join(cls._DISPLAY_ENVS)
        # Remove leading $ / $$ before \begin{display-env}
        text = re.sub(
            rf'\${{1,2}}\s*(\\begin{{(?:{env_pat})}})',
            r'\1',
            text,
            flags=re.DOTALL,
        )
        # Remove trailing $ / $$ after \end{display-env}
        text = re.sub(
            rf'(\\end{{(?:{env_pat})}})\s*\${{1,2}}',
            r'\1',
            text,
            flags=re.DOTALL,
        )
        # Apply user-defined corrections dictionary
        text = cls._apply_corrections(text)
        return text

    @staticmethod
    def _esc(text):
        """Escape LaTeX-special chars in plain text strings (titles, names, levels)."""
        if not text:
            return ""
        # Process backslash first to avoid double-escaping
        for old, new in [
            ("\\", r"\textbackslash{}"),
            ("&",  r"\&"),
            ("%",  r"\%"),
            ("$",  r"\$"),
            ("#",  r"\#"),
            ("_",  r"\_"),
            ("{",  r"\{"),
            ("}",  r"\}"),
            ("~",  r"\textasciitilde{}"),
            ("^",  r"\textasciicircum{}"),
        ]:
            text = text.replace(old, new)
        return text