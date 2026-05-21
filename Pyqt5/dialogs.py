"""
dialogs.py: Dialog windows for adding, editing, and searching exercises.
"""
import os
from pathlib import Path

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QTextEdit, QComboBox, QPushButton, QGroupBox,
    QLabel, QMessageBox, QDialogButtonBox, QTreeWidget,
    QTreeWidgetItem, QListWidget, QListWidgetItem, QSplitter,
    QRadioButton, QFileDialog
)
from PyQt5.QtCore import Qt
from translations import translations

class SearchDialog(QDialog):
    """Dialog for searching exercises with filters."""
    
    def __init__(self, parent, db):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.db = db
        self.selected_exercise_id = None
        self.parent = parent
        
        # Get current language and translations
        self.current_language = getattr(parent, 'current_language', 'en')
        self.trans = translations.get(self.current_language, translations['en'])
        
        self.setWindowTitle(self.trans.get("search_exercises", "Search Exercises"))
        self.setMinimumWidth(900)
        self.setMinimumHeight(600)
        
        self.setup_ui()
        self.load_filters()
        self.search_exercises()
    
    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel(f"<h2>{self.trans.get('search_exercises', 'Search Exercises')}</h2>")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Add root topic creation button
        topic_management_layout = QHBoxLayout()
        
        add_root_topic_btn = QPushButton(self.trans.get("add_root_topic", "Add Root Topic"))
        add_root_topic_btn.clicked.connect(self.add_root_topic)
        topic_management_layout.addWidget(add_root_topic_btn)
        
        topic_management_layout.addStretch()
        layout.addLayout(topic_management_layout)
        
        # Search controls
        search_layout = QHBoxLayout()
        
        search_layout.addWidget(QLabel(self.trans.get("search", "Search") + ":"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(self.trans.get("search_placeholder", "Search by name, keycode, content, or keywords..."))
        self.search_edit.textChanged.connect(self.search_exercises)
        search_layout.addWidget(self.search_edit, 3)
        
        search_layout.addWidget(QLabel(self.trans.get("level", "Level") + ":"))
        self.level_filter = QComboBox()
        self.level_filter.currentIndexChanged.connect(self.search_exercises)
        search_layout.addWidget(self.level_filter, 1)
        
        layout.addLayout(search_layout)
        
        # Topic selection
        topic_layout = QHBoxLayout()
        topic_layout.addWidget(QLabel(self.trans.get("filter_by_topic", "Filter by Topic") + ":"))
        
        self.topic_tree = QTreeWidget()
        self.topic_tree.setHeaderLabel(self.trans.get("topics_select_filter", "Topics (select to filter)"))
        self.topic_tree.setMaximumHeight(150)
        self.topic_tree.itemClicked.connect(self.on_topic_filter_changed)
        topic_layout.addWidget(self.topic_tree)
        
        clear_topic_btn = QPushButton(self.trans.get("clear_topic_filter", "Clear Topic Filter"))
        clear_topic_btn.clicked.connect(self.clear_topic_filter)
        topic_layout.addWidget(clear_topic_btn)
        
        layout.addLayout(topic_layout)
        
        # Results list
        layout.addWidget(QLabel(self.trans.get("search_results", "Search Results") + ":"))
        self.results_list = QListWidget()
        self.results_list.itemDoubleClicked.connect(self.accept)
        layout.addWidget(self.results_list)
        
        # Status label
        self.status_label = QLabel(self.trans.get("ready", "Ready"))
        layout.addWidget(self.status_label)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        # Translate button texts
        button_box.button(QDialogButtonBox.Ok).setText(self.trans.get("ok", "OK"))
        button_box.button(QDialogButtonBox.Cancel).setText(self.trans.get("cancel", "Cancel"))
        
        layout.addWidget(button_box)
        
    def add_root_topic(self):
        """Add a new root topic."""
        from PyQt5.QtWidgets import QInputDialog
        
        topic_name, ok = QInputDialog.getText(
            self, 
            self.trans.get("add_root_topic", "Add Root Topic"), 
            self.trans.get("enter_root_topic_name", "Enter name for new root topic:")
        )
        
        if ok and topic_name.strip():
            try:
                self.db.add_topic(topic_name.strip(), None)
                self.load_filters()
                QMessageBox.information(self, 
                    self.trans.get("success", "Success"), 
                    self.trans.get("root_topic_added", "Root topic added successfully!"))
            except Exception as e:
                QMessageBox.critical(self, 
                    self.trans.get("error", "Error"), 
                    f"{self.trans.get('failed_to_add_topic', 'Failed to add topic:')}\n{str(e)}")
    
    def load_filters(self):
        """Load filter options."""
        # Load levels - clear and rebuild with current language
        self.level_filter.clear()
        self.level_filter.addItem(self.trans.get("all_levels", "All Levels"), None)
        
        # Map of level identifiers to translations
        level_map = {
            'basic': self.trans.get("basic_level", "Basic"),
            'intermediate': self.trans.get("intermediate_level", "Intermediate"),
            'advanced': self.trans.get("advanced_level", "Advanced")
        }
        
        # Add standard levels in current language
        for level_id, level_name in level_map.items():
            self.level_filter.addItem(level_name, level_id)
        
        # Get existing levels from database and handle language mixing
        existing_levels = self.db.get_all_levels()
        
        # Map known level names in different languages to their identifiers
        known_levels = {
            # English
            'Basic': 'basic', 'Intermediate': 'intermediate', 'Advanced': 'advanced',
            # French
            'Débutant': 'basic', 'Intermédiaire': 'intermediate', 'Avancé': 'advanced',
            # Arabic
            'مبتدئ': 'basic', 'متوسط': 'intermediate', 'متقدم': 'advanced'
        }
        
        added_levels = set()
        
        for level in existing_levels:
            if level in known_levels:
                # This is a known level in another language - skip to avoid duplicates
                continue
            elif level not in level_map.values() and level not in added_levels:
                # This is a custom level - add it
                self.level_filter.addItem(level, level)
                added_levels.add(level)
                
        # ✅ CRITICAL: Load the topic tree (was missing!)
        self.load_topic_tree()
    
    def load_topic_tree(self):
        """Load topic tree for filtering."""
        self.topic_tree.clear()
        tree_data = self.db.get_topic_tree()
        self.selected_topic_ids = []
        
        def add_tree_items(parent_item, topics):
            for topic in topics:
                # Add exercise count like in the old version
                count_text = f" [{topic['exercise_count']}]" if topic.get('exercise_count', 0) > 0 else ""
                item = QTreeWidgetItem([f"{topic['name']}{count_text}"])
                item.setData(0, Qt.UserRole, topic['id'])
                
                if parent_item:
                    parent_item.addChild(item)
                else:
                    self.topic_tree.addTopLevelItem(item)
                
                if topic['children']:
                    add_tree_items(item, topic['children'])
        
        add_tree_items(None, tree_data)
        self.topic_tree.expandAll()
    
    def on_topic_filter_changed(self, item, column):
        """Handle topic selection for filtering."""
        topic_id = item.data(0, Qt.UserRole)
        if topic_id:
            self.selected_topic_ids = [topic_id]
            self.search_exercises()
    
    def clear_topic_filter(self):
        """Clear topic filter."""
        self.selected_topic_ids = []
        self.topic_tree.clearSelection()
        self.search_exercises()
    
    def search_exercises(self):
        """Perform search and update results."""
        query = self.search_edit.text()
        level = self.level_filter.currentData()
        topic_ids = self.selected_topic_ids if hasattr(self, 'selected_topic_ids') else None
        
        results = self.db.search_exercises(query, level, topic_ids)
        
        # Update results list
        self.results_list.clear()
        for ex_id, keycode, name, ex_level, date in results:
            display_text = f"{keycode} - {name}"
            if ex_level:
                display_text += f" [{ex_level}]"
            
            item = QListWidgetItem(display_text)
            item.setData(Qt.UserRole, ex_id)
            self.results_list.addItem(item)
        
        # Update status
        count = len(results)
        if count == 1:
            status_text = self.trans.get("found_one_exercise", "Found 1 exercise")
        else:
            status_text = self.trans.get("found_exercises", "Found {} exercises").format(count)
        self.status_label.setText(status_text)
    
    def get_selected_exercise_id(self):
        """Get the selected exercise ID."""
        current_item = self.results_list.currentItem()
        if current_item:
            return current_item.data(Qt.UserRole)
        return None
    
    def accept(self):
        """Accept dialog if an exercise is selected."""
        if not self.get_selected_exercise_id():
            QMessageBox.warning(self, 
                self.trans.get("no_selection", "No Selection"), 
                self.trans.get("please_select_exercise", "Please select an exercise."))
            return
        super().accept()

class AddEditExerciseDialog(QDialog):
    """Dialog for adding or editing an exercise."""
    
    def __init__(self, parent=None, exercise_data=None, all_levels=None, topic_tree=None):
        """
        Initialize the dialog.
        
        Args:
            parent: Parent widget
            exercise_data: Tuple of (id, keycode, name, latex, solution, date, level, keywords, topic_ids) for editing
            all_levels: List of existing levels for autocomplete
            topic_tree: Topic tree data structure
        """
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.exercise_data = exercise_data
        self.is_edit_mode = exercise_data is not None
        self.topic_tree_data = topic_tree or []
        self.parent = parent
        
        # Get current language and translations
        self.current_language = getattr(parent, 'current_language', 'en')
        self.trans = translations.get(self.current_language, translations['en'])
        
        window_title = self.trans.get("edit_exercise", "Edit Exercise") if self.is_edit_mode else self.trans.get("add_new_exercise", "Add New Exercise")
        self.setWindowTitle(window_title)
        self.setMinimumWidth(800)
        self.setMinimumHeight(650)
        self.setMaximumHeight(750)
        
        self.setup_ui(all_levels or [])
        
        if self.is_edit_mode:
            self.load_exercise_data()
    
    def setup_ui(self, all_levels):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        
        # Form layout for metadata
        form_layout = QFormLayout()
        
        # Name field
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText(self.trans.get("exercise_name_placeholder", "e.g., Quadratic Formula"))
        form_layout.addRow(self.trans.get("exercise_name", "Exercise Name") + ":", self.name_edit)
        
        # Keycode display (read-only in edit mode)
        if self.is_edit_mode:
            self.keycode_label = QLabel(self.exercise_data[1] if self.exercise_data else "")
            form_layout.addRow(self.trans.get("keycode", "Keycode") + ":", self.keycode_label)
        
        # Level combo box (editable for new values)
        self.level_combo = QComboBox()
        self.level_combo.setEditable(True)
        
        # Add translated level options
        level_options = [
            self.trans.get("basic_level", "Basic"),
            self.trans.get("intermediate_level", "Intermediate"), 
            self.trans.get("advanced_level", "Advanced")
        ]
        self.level_combo.addItems([""] + level_options)
        
        if all_levels:
            for level in all_levels:
                if level not in level_options:
                    self.level_combo.addItem(level)
        form_layout.addRow(self.trans.get("level", "Level") + ":", self.level_combo)
        
        # Keywords field
        self.keywords_edit = QLineEdit()
        self.keywords_edit.setPlaceholderText(self.trans.get("keywords_placeholder", "Comma-separated keywords (e.g., equation, roots, polynomial)"))
        form_layout.addRow(self.trans.get("keywords", "Keywords") + ":", self.keywords_edit)
        
        layout.addLayout(form_layout)
        
        # Topic selection
        topic_label = QLabel(self.trans.get("topics_select_multiple", "Topics (select one or more):"))
        layout.addWidget(topic_label)
        
        self.topic_tree = QTreeWidget()
        self.topic_tree.setHeaderLabel(self.trans.get("select_topics", "Select Topics"))
        self.topic_tree.setSelectionMode(QTreeWidget.MultiSelection)
        self.topic_tree.setMaximumHeight(200)
        self.load_topic_tree()
        layout.addWidget(self.topic_tree)
        
        # Exercise LaTeX content
        layout.addWidget(QLabel(self.trans.get("exercise_content", "Exercise Content (LaTeX):")))
        self.exercise_edit = QTextEdit()
        self.exercise_edit.setPlaceholderText(
            self.trans.get("exercise_content_placeholder", 
                "Enter LaTeX content here...\n\n"
                "Example:\n"
                "Find the roots of the equation:\n"
                "\\[ x^2 + 5x + 6 = 0 \\]")
        )
        layout.addWidget(self.exercise_edit)
        
        # Solution LaTeX content
        layout.addWidget(QLabel(self.trans.get("solution", "Solution (LaTeX):")))
        self.solution_edit = QTextEdit()
        self.solution_edit.setPlaceholderText(
            self.trans.get("solution_placeholder",
                "Enter solution here (optional)...\n\n"
                "Example:\n"
                "Using the quadratic formula:\n"
                "\\[ x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a} \\]")
        )
        layout.addWidget(self.solution_edit)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        # Translate button texts
        button_box.button(QDialogButtonBox.Ok).setText(self.trans.get("ok", "OK"))
        button_box.button(QDialogButtonBox.Cancel).setText(self.trans.get("cancel", "Cancel"))
        
        layout.addWidget(button_box)
    
    def load_topic_tree(self):
        """Load topic tree for selection."""
        self.topic_tree.clear()
        
        def add_tree_items(parent_item, topics):
            for topic in topics:
                item = QTreeWidgetItem([topic['name']])
                item.setData(0, Qt.UserRole, topic['id'])
                
                if parent_item:
                    parent_item.addChild(item)
                else:
                    self.topic_tree.addTopLevelItem(item)
                
                if topic['children']:
                    add_tree_items(item, topic['children'])
        
        add_tree_items(None, self.topic_tree_data)
        self.topic_tree.expandAll()
    
    def load_exercise_data(self):
        """Load existing exercise data into the form."""
        if not self.exercise_data:
            return
        
        ex_id, keycode, name, latex, solution, date, level, keywords, topic_ids = self.exercise_data
        
        self.name_edit.setText(name or "")
        self.exercise_edit.setPlainText(latex or "")
        self.solution_edit.setPlainText(solution or "")
        
        if level:
            self.level_combo.setCurrentText(level)
        if keywords:
            self.keywords_edit.setText(", ".join(keywords))
        
        # Select topics in tree
        if topic_ids:
            self.select_topics_in_tree(topic_ids)
    
    def select_topics_in_tree(self, topic_ids):
        """Select topics in the tree widget."""
        def select_recursive(item):
            topic_id = item.data(0, Qt.UserRole)
            if topic_id in topic_ids:
                item.setSelected(True)
            for i in range(item.childCount()):
                select_recursive(item.child(i))
        
        for i in range(self.topic_tree.topLevelItemCount()):
            select_recursive(self.topic_tree.topLevelItem(i))
    
    def get_selected_topic_ids(self):
        """Get selected topic IDs from tree."""
        selected_ids = []
        
        def get_selected_recursive(item):
            if item.isSelected():
                topic_id = item.data(0, Qt.UserRole)
                if topic_id:
                    selected_ids.append(topic_id)
            for i in range(item.childCount()):
                get_selected_recursive(item.child(i))
        
        for i in range(self.topic_tree.topLevelItemCount()):
            get_selected_recursive(self.topic_tree.topLevelItem(i))
        
        return selected_ids
    
    def get_data(self):
        """
        Get the entered data from the dialog.
        
        Returns:
            Dictionary with exercise data
        """
        keywords_text = self.keywords_edit.text().strip()
        keywords = [k.strip() for k in keywords_text.split(",")] if keywords_text else []
        
        return {
            'name': self.name_edit.text().strip(),
            'latex': self.exercise_edit.toPlainText().strip(),
            'solution': self.solution_edit.toPlainText().strip(),
            'level': self.level_combo.currentText().strip() or None,
            'topic_ids': self.get_selected_topic_ids(),
            'keywords': keywords
        }
    
    def accept(self):
        """Validate and accept the dialog."""
        data = self.get_data()
        
        if not data['name']:
            QMessageBox.warning(self, 
                self.trans.get("validation_error", "Validation Error"), 
                self.trans.get("please_enter_exercise_name", "Please enter an exercise name."))
            return
        
        if not data['latex']:
            QMessageBox.warning(self, 
                self.trans.get("validation_error", "Validation Error"), 
                self.trans.get("please_enter_exercise_content", "Please enter exercise content."))
            return
        
        if not data['topic_ids']:
            QMessageBox.warning(self, 
                self.trans.get("validation_error", "Validation Error"), 
                self.trans.get("please_select_at_least_one_topic", "Please select at least one topic."))
            return
        
        super().accept()


class StatisticsDialog(QDialog):
    """Dialog to show database statistics."""
    
    def __init__(self, parent, stats):
        """
        Initialize the statistics dialog.
        
        Args:
            parent: Parent widget
            stats: Dictionary with statistics data
        """
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.stats = stats
        
        # Get current language and translations
        self.current_language = getattr(parent, 'current_language', 'en')
        self.trans = translations.get(self.current_language, translations['en'])
        
        self.setWindowTitle(self.trans.get("database_statistics", "Database Statistics"))
        self.setMinimumWidth(450)
        
        self.setup_ui()

    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)

        # Title
        title = QLabel(f"<h2>{self.trans.get('database_statistics', 'Database Statistics')}</h2>")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # 🧩 Prepare levels text separately
        if self.stats['levels']:
            levels_text = ', '.join(self.stats['levels'])
        else:
            levels_text = self.trans.get('none', 'None')

        # Statistics content (HTML)
        stats_text = f"""
        <table style="width:100%; font-size:14px;">
        <tr><td><b>{self.trans.get('total_exercises', 'Total Exercises')}:</b></td><td>{self.stats['total_exercises']}</td></tr>
        <tr><td><b>{self.trans.get('with_solutions', 'With Solutions')}:</b></td><td>{self.stats['with_solutions']}</td></tr>
        <tr><td><b>{self.trans.get('without_solutions', 'Without Solutions')}:</b></td><td>{self.stats['without_solutions']}</td></tr>
        <tr><td><b>{self.trans.get('main_topics', 'Main Topics')}:</b></td><td>{self.stats['main_topics']}</td></tr>
        <tr><td><b>{self.trans.get('total_topics', 'Total Topics')}:</b></td><td>{self.stats['total_topics']}</td></tr>
        <tr><td><b>{self.trans.get('number_of_levels', 'Number of Levels')}:</b></td><td>{len(self.stats['levels'])}</td></tr>
        </table>

        <h3>{self.trans.get('levels', 'Levels')}:</h3>
        <p>{levels_text}</p>
        """

        content = QLabel(stats_text)
        content.setWordWrap(True)
        content.setTextFormat(Qt.RichText)
        layout.addWidget(content)

        # Close button
        close_btn = QPushButton(self.trans.get("close", "Close"))
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)



class SettingsDialog(QDialog):
    """Dialog for application settings including language and discipline."""
    
    def __init__(self, parent=None, current_language="en", current_discipline="mathematics",
                 custom_discipline="", db_path="exercises.db"):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.parent = parent
        self.current_language = current_language
        self.current_discipline = current_discipline
        self.custom_discipline = custom_discipline
        self._db_path = db_path          # current database path passed in from main window
        
        # Get translations
        self.trans = translations.get(current_language, translations['en'])
        
        self.setWindowTitle(self.trans.get("settings_title", "Settings"))
        self.setMinimumWidth(500)
        
        self.setup_ui()
        
    
    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        
        # Title
        title = QLabel(f"<h2>{self.trans.get('settings_title', 'Settings')}</h2>")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Language settings
        lang_group = QGroupBox(self.trans.get("language_settings", "Language Settings"))
        lang_layout = QVBoxLayout(lang_group)
        
        lang_layout.addWidget(QLabel(self.trans.get("select_language", "Select Language") + ":"))
        self.language_combo = QComboBox()
        self.language_combo.addItem("العربية (Arabic)", "ar")
        self.language_combo.addItem("English", "en")
        self.language_combo.addItem("Français (French)", "fr")
        
        # Set current language
        index = self.language_combo.findData(self.current_language)
        if index >= 0:
            self.language_combo.setCurrentIndex(index)
            
        lang_layout.addWidget(self.language_combo)
        layout.addWidget(lang_group)
        
        # Discipline settings
        disc_group = QGroupBox(self.trans.get("discipline_settings", "Discipline Settings"))
        disc_layout = QVBoxLayout(disc_group)
        
        disc_layout.addWidget(QLabel(self.trans.get("select_discipline", "Select Discipline") + ":"))
        self.discipline_combo = QComboBox()
        
        # Add disciplines
        disciplines = [
            ("mathematics", self.trans.get("mathematics", "Mathematics")),
            ("physics", self.trans.get("physics", "Physics")),
            ("chemistry", self.trans.get("chemistry", "Chemistry")),
            ("biology", self.trans.get("biology", "Biology")),
            ("economics", self.trans.get("economics", "Economics")),
            ("computer_science", self.trans.get("computer_science", "Computer Science")),
            ("engineering", self.trans.get("engineering", "Engineering")),
            ("statistics", self.trans.get("statistics", "Statistics")),
            ("data_science", self.trans.get("data_science", "Data Science")),
            ("finance", self.trans.get("finance", "Finance")),
            ("architecture", self.trans.get("architecture", "Architecture")),
            ("medicine", self.trans.get("medicine", "Medicine")),
            ("astronomy", self.trans.get("astronomy", "Astronomy")),
            ("geography", self.trans.get("geography", "Geography")),
            ("environmental_science", self.trans.get("environmental_science", "Environmental Science")),
            ("psychology", self.trans.get("psychology", "Psychology")),
            ("sociology", self.trans.get("sociology", "Sociology")),
            ("linguistics", self.trans.get("linguistics", "Linguistics")),
            ("cryptography", self.trans.get("cryptography", "Cryptography")),
            ("artificial_intelligence", self.trans.get("artificial_intelligence", "Artificial Intelligence")),
            ("robotics", self.trans.get("robotics", "Robotics")),
            ("custom", self.trans.get("custom", "Custom Discipline"))
        ]
        
        for disc_id, disc_name in disciplines:
            self.discipline_combo.addItem(disc_name, disc_id)
        
        # Set current discipline
        if self.current_discipline in [d[0] for d in disciplines]:
            disc_index = self.discipline_combo.findData(self.current_discipline)
            if disc_index >= 0:
                self.discipline_combo.setCurrentIndex(disc_index)
        else:
            # If current discipline is custom, select "custom" option
            self.discipline_combo.setCurrentIndex(self.discipline_combo.findData("custom"))
            
        disc_layout.addWidget(self.discipline_combo)
        
        # Custom discipline input
        self.custom_layout = QHBoxLayout()
        self.custom_layout.addWidget(QLabel(self.trans.get("custom_discipline", "Custom Discipline") + ":"))
        self.custom_discipline_edit = QLineEdit()
        self.custom_discipline_edit.setPlaceholderText(self.trans.get("custom_discipline_placeholder", "Enter a custom discipline..."))
        
        # If current discipline is custom, show the custom text
        if self.current_discipline not in [d[0] for d in disciplines]:
            self.custom_discipline_edit.setText(self.current_discipline)
        else:
            self.custom_discipline_edit.setText(self.custom_discipline)
            
        self.custom_layout.addWidget(self.custom_discipline_edit)
        disc_layout.addLayout(self.custom_layout)
        
        # Show/hide custom discipline based on selection
        self.discipline_combo.currentIndexChanged.connect(self.on_discipline_changed)
        self.on_discipline_changed()  # Initial state
        
        layout.addWidget(disc_group)

        # ── Database Settings ─────────────────────────────────────────────────
        def _resolve_db(p):
            """Return the absolute path DatabaseManager would use for p."""
            if os.path.isabs(p):
                return p
            appdata = os.getenv('APPDATA', '')
            if appdata:
                return str(Path(appdata) / "YasmeenTex" / p)
            return p

        default_filename = "exercises.db"
        default_abs = _resolve_db(default_filename)
        is_default = (self._db_path == default_filename or
                      _resolve_db(self._db_path) == default_abs)

        db_group = QGroupBox("Database Settings")
        db_vlayout = QVBoxLayout(db_group)
        db_vlayout.setSpacing(8)

        self.rb_default_db = QRadioButton(f"Use default database  ({default_abs})")
        self.rb_custom_db  = QRadioButton("Use a custom database file:")
        self.rb_default_db.setChecked(is_default)
        self.rb_custom_db.setChecked(not is_default)
        db_vlayout.addWidget(self.rb_default_db)
        db_vlayout.addWidget(self.rb_custom_db)

        path_row = QHBoxLayout()
        self.db_path_edit = QLineEdit()
        self.db_path_edit.setPlaceholderText("Full path to .db file …")
        self.db_path_edit.setText(
            _resolve_db(self._db_path) if not is_default else _resolve_db(default_filename)
        )
        self.db_path_edit.setEnabled(not is_default)

        self.db_browse_btn = QPushButton("Browse …")
        self.db_browse_btn.setEnabled(not is_default)
        self.db_browse_btn.setFixedWidth(90)

        path_row.addWidget(self.db_path_edit)
        path_row.addWidget(self.db_browse_btn)
        db_vlayout.addLayout(path_row)

        db_note = QLabel(
            "<i>Changing the database takes effect immediately after clicking OK.<br>"
            "The app will switch to the selected file — no data is copied between databases.</i>"
        )
        db_note.setWordWrap(True)
        db_vlayout.addWidget(db_note)

        layout.addWidget(db_group)

        def _on_radio_toggled():
            custom = self.rb_custom_db.isChecked()
            self.db_path_edit.setEnabled(custom)
            self.db_browse_btn.setEnabled(custom)
            if not custom:
                self.db_path_edit.setText(_resolve_db(default_filename))

        self.rb_default_db.toggled.connect(_on_radio_toggled)
        self.rb_custom_db.toggled.connect(_on_radio_toggled)

        def _on_browse():
            appdata = os.getenv('APPDATA', '')
            start_dir = str(Path(appdata) / "YasmeenTex") if appdata else ""
            Path(start_dir).mkdir(parents=True, exist_ok=True)
            path, _ = QFileDialog.getOpenFileName(
                self,
                "Select Database File",
                start_dir,
                "SQLite Database (*.db *.sqlite *.sqlite3);;All files (*)"
            )
            if path:
                self.db_path_edit.setText(path)

        self.db_browse_btn.clicked.connect(_on_browse)
        # ─────────────────────────────────────────────────────────────────────

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        # Translate button texts
        button_box.button(QDialogButtonBox.Ok).setText(self.trans.get("ok", "OK"))
        button_box.button(QDialogButtonBox.Cancel).setText(self.trans.get("cancel", "Cancel"))
        
        layout.addWidget(button_box)
        
        
    
    def on_discipline_changed(self):
        """Show/hide custom discipline field based on selection."""
        current_disc = self.discipline_combo.currentData()
        is_custom = current_disc == "custom"
        
        # Show/hide the entire custom discipline layout
        for i in range(self.custom_layout.count()):
            widget = self.custom_layout.itemAt(i).widget()
            if widget:
                widget.setVisible(is_custom)
    
    def get_settings(self):
        """Get the selected settings."""
        language = self.language_combo.currentData()
        discipline = self.discipline_combo.currentData()
        custom_discipline = self.custom_discipline_edit.text().strip()
        
        if discipline == "custom":
            if custom_discipline:
                final_discipline = custom_discipline
            else:
                # If custom is selected but no text entered, keep the current custom discipline
                final_discipline = self.current_discipline if self.current_discipline not in [
                    "mathematics", "physics", "chemistry", "biology", "economics", 
                    "computer_science", "engineering", "statistics", "data_science", 
                    "finance", "architecture", "medicine", "astronomy", "geography",
                    "environmental_science", "psychology", "sociology", "linguistics",
                    "cryptography", "artificial_intelligence", "robotics"
                ] else "mathematics"
        else:
            final_discipline = discipline
            
        return {
            'language': language,
            'discipline': final_discipline,
            'custom_discipline': custom_discipline if discipline == "custom" else "",
            'db_path': (
                'exercises.db'
                if self.rb_default_db.isChecked()
                else (self.db_path_edit.text().strip() or 'exercises.db')
            )
        }