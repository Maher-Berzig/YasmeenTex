"""
main_window.py: Main window for LaTeX Exercise Viewer with hierarchical topic tree.
"""
# Add these imports
import re
import json
import requests
import sys
import base64
import os

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLineEdit, QPushButton, QLabel, QListWidget, QSizePolicy,
    QTabWidget, QGroupBox,  QTextBrowser, QDialog, QFileDialog, QScrollArea, 
    QSplitter, QMessageBox, QComboBox, QAction, QListWidgetItem,
    QMenu, QTreeWidget, QTreeWidgetItem, QInputDialog, QShortcut
)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings, QWebEnginePage
from PyQt5.QtCore import QUrl, Qt, QTimer, QDateTime, QMimeData, QByteArray, QBuffer, QEvent
from PyQt5.QtGui import QFont, QKeySequence, QPixmap, QImage

from database import DatabaseManager
from latex_renderer import KaTeXRenderer
from dialogs import AddEditExerciseDialog, StatisticsDialog, SearchDialog, SettingsDialog  # Make sure SettingsDialog is imported
from export_dialog import ExportExercisesDialog
from ai_config_dialog import AIConfigDialog
from katex_loader import build_chat_html_with_katex 
from topic_tree import TopicTreeWidget
from ai_assistant_tab import AIAssistantTab

# Add this import
from translations import translations

class MainWindow(QMainWindow):
    """Main application window for viewing LaTeX exercises."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("YasmeenTeX")
        self.setGeometry(100, 100, 1200, 700)
        self.setMinimumSize(800, 600)  # Fix geometry warnings
        

        # Initialize settings
        self.current_language = 'en'
        self.current_discipline = 'mathematics'
        self.custom_discipline = ''
        
        # Load settings
        self.load_settings()

    
        # Initialize database (db_path loaded by load_settings above)
        self.db = DatabaseManager(self.db_path)
        
        # AI configuration - MUST BE BEFORE AI Assistant tab
        self.ai_config = self.load_ai_config()
        
        # Initialize topic tree early
        self.topic_tree = TopicTreeWidget(self)
        
        # Initialize AI Assistant tab early
        self.ai_assistant_tab = AIAssistantTab(self, self.ai_config, self.db)       
        
        
        # Ensure AI Assistant tab gets the current language immediately
        if hasattr(self, 'ai_assistant_tab'):
            self.ai_assistant_tab.current_language = self.current_language
        
        # Current exercise data
        self.current_exercise_id = None
        self.current_exercise_data = None
        self.current_ai_exercise = None
        self.current_ai_metadata = None
        self.partial_solution = None
        self.solution_visible = False
        self.has_solution = False
        self.tree_visible = False  
        
       
        # Setup UI
        self.setup_menubar()
        self.setup_ui()
        
        
        # Load initial data
        self.topic_tree.load_topic_tree()
        
        # Force UI update with the loaded language
        self.force_ui_language_update()
        
        
        
    def setup_menubar(self):
        """Create the menu bar with increased height and font size."""
        menubar = self.menuBar()
        
        # ✅ REMOVE fixed height - it causes issues
        # menubar.setFixedHeight(35)  # DELETE THIS LINE
        
        # ✅ INCREASE MENU FONT SIZE (more conservative)
        menu_font = QFont()
        menu_font.setPointSize(10)  # Slightly increased from default
        menubar.setFont(menu_font)
        
        # ✅ SIMPLIFIED STYLING - remove problematic styles
        menubar.setStyleSheet("""
            QMenuBar {
                background-color: #f8f9fa;
                border-bottom: 1px solid #dee2e6;
                spacing: 8px;
                padding: 6px 0px;
            }
            QMenuBar::item {
                padding: 6px 12px;
                border-radius: 4px;
            }
            QMenuBar::item:selected {
                background-color: #0078d4;
                color: white;
            }
        """)
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        # ✅ INCREASE MENU ITEM FONT SIZE
        menu_item_font = QFont()
        menu_item_font.setPointSize(10)
        
        add_action = QAction("&Add Exercise", self)
        add_action.setShortcut("Ctrl+N")
        add_action.triggered.connect(self.add_exercise)
        add_action.setFont(menu_item_font)
        file_menu.addAction(add_action)
        
        search_action = QAction("&Search Exercises", self)
        search_action.setShortcut("Ctrl+F")
        search_action.triggered.connect(self.open_search_dialog)
        search_action.setFont(menu_item_font)
        file_menu.addAction(search_action)
        
        file_menu.addSeparator()
        
        add_root_topic_action = QAction("Add &Root Topic", self)
        add_root_topic_action.triggered.connect(self.topic_tree.add_root_topic)
        add_root_topic_action.setFont(menu_item_font)
        file_menu.addAction(add_root_topic_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        exit_action.setFont(menu_item_font)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("&Edit")
        
        edit_action = QAction("&Edit Exercise", self)
        edit_action.setShortcut("Ctrl+E")
        edit_action.triggered.connect(self.edit_exercise)
        edit_action.setFont(menu_item_font)
        edit_menu.addAction(edit_action)
        
        delete_action = QAction("&Delete Exercise", self)
        delete_action.setShortcut("Delete")
        delete_action.triggered.connect(self.delete_exercise)
        delete_action.setFont(menu_item_font)
        edit_menu.addAction(delete_action)

        edit_menu.addSeparator()

        export_action = QAction("E&xport Exercises to LaTeX…", self)
        export_action.setShortcut("Ctrl+X")
        export_action.triggered.connect(self.open_export_dialog)
        export_action.setFont(menu_item_font)
        edit_menu.addAction(export_action)

        edit_menu.addSeparator()
        
        refresh_action = QAction("&Refresh", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.refresh_all)
        refresh_action.setFont(menu_item_font)
        edit_menu.addAction(refresh_action)
        
        # View menu
        view_menu = menubar.addMenu("&View")
        
        stats_action = QAction("&Statistics", self)
        stats_action.triggered.connect(self.show_statistics)
        stats_action.setFont(menu_item_font)
        view_menu.addAction(stats_action)

        # Show/Hide Solution menu item
        self.toggle_solution_action = QAction("Show Solution", self)               
        self.toggle_solution_action.setCheckable(True)
        self.toggle_solution_action.setChecked(self.solution_visible)
        self.toggle_solution_action.triggered.connect(self.toggle_solution_panel)
        self.toggle_solution_action.setFont(menu_item_font)
        view_menu.addAction(self.toggle_solution_action)
        
        # Show/Hide Tree menu item
        self.toggle_tree_action = QAction("Show Tree", self)
        self.toggle_tree_action.setCheckable(True)
        self.toggle_tree_action.setChecked(self.tree_visible)
        self.toggle_tree_action.triggered.connect(self.toggle_tree_panel)
        self.toggle_tree_action.setFont(menu_item_font)
        view_menu.addAction(self.toggle_tree_action)
        
        # Tools menu
        tools_menu = menubar.addMenu("&Tools")
        
        ai_config_action = QAction("AI &Configuration", self)
        ai_config_action.triggered.connect(self.show_ai_config_dialog)
        ai_config_action.setFont(menu_item_font)
        tools_menu.addAction(ai_config_action)
        
        # Options menu
        options_menu = menubar.addMenu("&Options")
        
        settings_action = QAction("&Settings", self)
        settings_action.triggered.connect(self.show_settings_dialog)
        settings_action.setFont(menu_item_font)
        options_menu.addAction(settings_action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        about_action.setFont(menu_item_font)
        help_menu.addAction(about_action)
        
        # ✅ Apply styling to dropdown menus
        self.apply_menu_styling()

    def apply_menu_styling(self):
        """Apply styling to dropdown menus."""
        menu_style = """
            QMenu {
                background-color: white;
                border: 1px solid #dee2e6;
                border-radius: 4px;
            }
            QMenu::item {
                padding: 8px 25px 8px 20px;
                font-size: 10pt;
                min-height: 20px;
            }
            QMenu::item:selected {
                background-color: #0078d4;
                color: white;
            }
            QMenu::separator {
                height: 1px;
                background-color: #dee2e6;
                margin: 4px 8px;
            }
        """
        
        # Apply to all menus after they're created
        QTimer.singleShot(100, lambda: self._style_menus(menu_style))

    def _style_menus(self, style):
        """Style all menus with delay to ensure they exist."""
        for menu in self.findChildren(QMenu):
            menu.setStyleSheet(style)
        
    
    def setup_ui(self):
        """Setup the main user interface with tabs."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        
        # Create tab widget
        self.tab_widget = QTabWidget()
        
        # Connect tab change signal
        self.tab_widget.currentChanged.connect(self.on_tab_changed)

        
        # Create and add tabs
        self.create_exercises_tab()
        self.create_ai_assistant_tab()
        
        main_layout.addWidget(self.tab_widget)
        
        # Status bar
        self.statusBar().showMessage(self.tr("ready_message"))
        
    def on_tab_changed(self, index=None):
        """Handle tab change to update status bar message."""
        # If no index provided, get current tab
        if index is None:
            if hasattr(self, 'tab_widget') and self.tab_widget:
                index = self.tab_widget.currentIndex()
            else:
                index = 0  # Default to exercises tab
        
        if index == 0:  # Exercises tab
            self.statusBar().showMessage(self.tr("ready_message"))
        elif index == 1:  # AI Assistant tab
            self.statusBar().showMessage(self.tr("ai_assistant_ready"))
        

    def force_ui_language_update(self):
        """Force update all UI elements with current language, ensuring everything is translated."""
        #print(f"Force updating UI to language: {self.current_language}")
        
        # Update menu bar
        self.update_menu_language()
        
        
        # Update main window title
        self.setWindowTitle("YasmeenTeX")
        
        # Update tab names
        if hasattr(self, 'tab_widget') and self.tab_widget:
            self.tab_widget.setTabText(0, self.tr("exercises_tab"))
            self.tab_widget.setTabText(1, self.tr("ai_assistant_tab"))
        
        # Update exercises tab
        self.update_exercises_tab_language()
        self.update_tree_ui()
        self.update_dynamic_menu_items()
        # Update status bar for current tab
        QTimer.singleShot(100, self.on_tab_changed)               
        
        # Update AI assistant tab
        if hasattr(self, 'ai_assistant_tab'):
            self.ai_assistant_tab.update_language()
            
        
        # Update topic tree
        if hasattr(self, 'topic_tree'):
            self.topic_tree.update_language()
        
        # Update status bar - use direct translation lookup instead of tr()
        trans = translations.get(self.current_language, translations['en'])
        status_message = trans.get("ready_message", "Ready - Click 'Search Exercises' or 'Show Maths Tree' to browse")
        self.statusBar().showMessage(status_message)
        
        #print("UI language update completed")
    
    
    def handle_move_up_shortcut(self):
        """Handle Ctrl+Up shortcut."""
        current_item = self.topic_tree.currentItem()
        if current_item and current_item.data(0, Qt.UserRole):
            topic_id = current_item.data(0, Qt.UserRole)
            self.topic_tree.move_topic_up(topic_id)

    def handle_move_down_shortcut(self):
        """Handle Ctrl+Down shortcut."""
        current_item = self.topic_tree.currentItem()
        if current_item and current_item.data(0, Qt.UserRole):
            topic_id = current_item.data(0, Qt.UserRole)
            self.topic_tree.move_topic_down(topic_id)

    def handle_promote_shortcut(self):
        """Handle Ctrl+Left shortcut."""
        current_item = self.topic_tree.currentItem()
        if current_item and current_item.data(0, Qt.UserRole):
            topic_id = current_item.data(0, Qt.UserRole)
            self.topic_tree.promote_topic(topic_id, current_item)

    def handle_demote_shortcut(self):
        """Handle Ctrl+Right shortcut."""
        current_item = self.topic_tree.currentItem()
        if current_item and current_item.data(0, Qt.UserRole):
            topic_id = current_item.data(0, Qt.UserRole)
            self.topic_tree.demote_topic(topic_id, current_item)        

    def create_ai_assistant_tab(self):
        """Create AI Assistant tab using the pre-initialized class."""
        self.tab_widget.addTab(self.ai_assistant_tab, "AI Assistant")

    def create_exercises_tab(self):
        """Create the main exercises tab."""
        exercises_tab = QWidget()
        layout = QVBoxLayout(exercises_tab)
        layout.setContentsMargins(5, 5, 5, 5)  
        layout.setSpacing(5)
        
        # Top bar with search and buttons
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)
        top_bar.setSpacing(10)
        
        button_width = 220
        
        # ✅ FORCE EQUAL WIDTHS WITH CSS
        button_style = f"""
            QPushButton {{
                min-width: {button_width}px;
                max-width: {button_width}px;
                width: {button_width}px;
            }}
        """
        
        # Search button
        search_btn = QPushButton("🔍 Search Exercises")
        search_btn.clicked.connect(self.open_search_dialog)
        search_btn.setStyleSheet(button_style)  # ✅ APPLY CSS
        top_bar.addWidget(search_btn)
        
        # Toggle tree button
        self.toggle_tree_btn = QPushButton("Show Tree")
        self.toggle_tree_btn.setCheckable(True)
        self.toggle_tree_btn.setChecked(self.tree_visible)
        self.toggle_tree_btn.setStyleSheet(button_style)  # ✅ APPLY CSS
        self.toggle_tree_btn.clicked.connect(self.toggle_tree_panel)
        top_bar.addWidget(self.toggle_tree_btn)
        
        top_bar.addStretch()
        
        # Add exercise button
        add_btn = QPushButton("+ Add Exercise")
        add_btn.clicked.connect(self.add_exercise)
        add_btn.setStyleSheet(button_style)  # ✅ APPLY CSS
        top_bar.addWidget(add_btn)

        # Show/Hide Solution button
        self.toggle_solution_btn = QPushButton("Show Solution")
        self.toggle_solution_btn.setCheckable(True)
        self.toggle_solution_btn.setChecked(self.solution_visible)
        self.toggle_solution_btn.setEnabled(False)
        self.toggle_solution_btn.setStyleSheet(button_style)  # ✅ APPLY CSS
        self.toggle_solution_btn.clicked.connect(self.toggle_solution_panel)
        top_bar.addWidget(self.toggle_solution_btn)

        # Print / PDF button (enabled only when an exercise is loaded)
        self.print_btn = QPushButton("🖨  Print / PDF")
        self.print_btn.setEnabled(False)
        self.print_btn.setStyleSheet(button_style)
        print_menu = QMenu(self)
        printer_action = print_menu.addAction("🖨  Print to printer…")
        pdf_action     = print_menu.addAction("📄  Save as PDF…")
        printer_action.triggered.connect(self._print_to_printer)
        pdf_action.triggered.connect(self._save_as_pdf)
        self.print_btn.setMenu(print_menu)
        top_bar.addWidget(self.print_btn)
        
        # Create a widget for the top bar to contain it properly
        top_bar_widget = QWidget()
        top_bar_widget.setLayout(top_bar)
        top_bar_widget.setMaximumHeight(50)  # Constrain height
        top_bar_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(top_bar_widget)
        
    # ... rest of your code remains exactly the same ...            
        # Main splitter (tree, exercise, solution)
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setChildrenCollapsible(False)  # Prevent panels from collapsing completely
        
        # Left panel: Topic tree (hidden by default)
        self.tree_widget_container = QWidget()
        self.tree_widget_container.setMinimumWidth(200)  # Set minimum width
        self.tree_widget_container.setMaximumWidth(400)  # Set maximum width
        tree_layout = QVBoxLayout(self.tree_widget_container)
        tree_layout.setContentsMargins(0, 0, 0, 0)
        tree_layout.setSpacing(5)
        
        # Tree header with title and add button
        tree_header = QHBoxLayout()
        tree_header.setContentsMargins(5, 5, 5, 5)
        tree_label = QLabel("Tree")
        tree_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        tree_header.addWidget(tree_label)
        
        tree_header.addStretch()
        
        # Add main topic button
        self.add_main_topic_btn = QPushButton("+ Add Main Topic")
        self.add_main_topic_btn.clicked.connect(self.topic_tree.add_root_topic)
        self.add_main_topic_btn.setFixedWidth(120)
        tree_header.addWidget(self.add_main_topic_btn)
        
        tree_layout.addLayout(tree_header)
        
        # Use the custom tree widget that was created in __init__
        self.topic_tree.setHeaderLabel("Topics")
        self.topic_tree.itemClicked.connect(self.topic_tree.on_topic_selected)
        
        # Enable drag & drop
        self.topic_tree.setDragEnabled(True)
        self.topic_tree.setAcceptDrops(True)
        self.topic_tree.setDropIndicatorShown(True)
        self.topic_tree.setDragDropMode(QTreeWidget.InternalMove)
        self.topic_tree.setSelectionMode(QTreeWidget.SingleSelection)
        
        tree_layout.addWidget(self.topic_tree)
        
        self.tree_widget_container.setVisible(False)
        self.splitter.addWidget(self.tree_widget_container)
        
        # Middle panel: Exercise content
        exercise_widget = QWidget()
        exercise_widget.setMinimumWidth(300)  # Set minimum width
        exercise_layout = QVBoxLayout(exercise_widget)
        exercise_layout.setContentsMargins(5, 0, 5, 0)
        exercise_layout.setSpacing(5)
        
        ex_label = QLabel("Exercise")
        ex_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        exercise_layout.addWidget(ex_label)
        
        self.exercise_view = QWebEngineView()
        self.exercise_view.setMinimumWidth(300)  # Set minimum width
        
        # Configure settings
        settings = self.exercise_view.settings()
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)
        
        exercise_layout.addWidget(self.exercise_view, 1)
        
        # Additional settings
        self.exercise_view.settings().setAttribute(
            QWebEngineSettings.LocalContentCanAccessFileUrls, True
        )
        
        self.splitter.addWidget(exercise_widget)
        
        # Right panel: Solution content
        self.solution_widget = QWidget()
        self.solution_widget.setMinimumWidth(300)  # Set minimum width
        solution_layout = QVBoxLayout(self.solution_widget)
        solution_layout.setContentsMargins(5, 0, 0, 0)
        solution_layout.setSpacing(5)
        
        sol_label = QLabel("Solution")
        sol_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        solution_layout.addWidget(sol_label)
        
        self.solution_view = QWebEngineView()
        self.solution_view.setMinimumWidth(300)  # Set minimum width
        solution_layout.addWidget(self.solution_view, 1)
        
        # Configure settings
        solution_settings = self.solution_view.settings()
        solution_settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        solution_settings.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)
        
        self.splitter.addWidget(self.solution_widget)
        
        # Initially hide solution panel
        self.solution_widget.setVisible(False)
        
        # Set initial splitter sizes
        self._two_panel_sizes = [0, 1, 0]  # Tree hidden, exercise visible, solution hidden
        self._three_panel_sizes = [0, 1, 1]  # Tree hidden, exercise & solution visible
        self._tree_two_panel_sizes = [1, 2, 0]  # Tree visible, exercise visible, solution hidden
        self._tree_three_panel_sizes = [1, 1, 1]  # All visible
        
        # Use proportional sizes instead of fixed pixel sizes
        self.splitter.setSizes(self._two_panel_sizes)
        
        layout.addWidget(self.splitter, 1)  # Give the splitter stretch factor
        
        self.tab_widget.addTab(exercises_tab, "Exercises")
    
    def show_ai_config_dialog(self):
        """Show AI configuration dialog."""
        dialog = AIConfigDialog(self, self.ai_config)
        if dialog.exec_() == QDialog.Accepted:
            new_config = dialog.get_config()
            self.ai_config.update(new_config)
            self.save_ai_config()
            self.ai_assistant_tab.update_ai_status()

            

    def eventFilter(self, obj, event):
        """Handle paste events and keyboard shortcuts."""
        if obj == self.ai_assistant_tab.chat_input and event.type() == QEvent.KeyPress:
            try:
                # Ctrl+V pour coller des images
                if event.key() == Qt.Key_V and (event.modifiers() & Qt.ControlModifier):
                    clipboard = QApplication.clipboard()
                    mime_data = clipboard.mimeData()
                    
                    if mime_data.hasImage():
                        image = clipboard.image()
                        if not image.isNull():
                            self.process_pasted_image(image)
                            return True  # Event handled
                    
                    elif mime_data.hasUrls():
                        urls = mime_data.urls()
                        for url in urls:
                            if url.isLocalFile():
                                file_path = url.toLocalFile()
                                if self.is_image_file(file_path):
                                    self.process_image_file(file_path)
                                    return True  # Event handled
                
                # Ctrl+Enter pour envoyer le message (gère Return et Enter)
                elif (event.key() in (Qt.Key_Return, Qt.Key_Enter)) and (event.modifiers() & Qt.ControlModifier):
                    self.send_chat_message()
                    return True  # Event handled
                
                # Enter seul (sans Ctrl) - comportement normal (nouvelle ligne)
                elif (event.key() in (Qt.Key_Return, Qt.Key_Enter)) and (event.modifiers() == Qt.NoModifier):
                    return False  # laisser le QTextEdit insérer la nouvelle ligne
                
            except Exception as e:
                print(f"Error in event filter: {e}")
                return False
        
        return super().eventFilter(obj, event)
    

    def dragEnterEvent(self, event):
        """Accept drag events containing images or image files."""
        if event.mimeData().hasImage() or event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        """Handle dropped images."""
        mime_data = event.mimeData()
        
        if mime_data.hasImage():
            # Handle dropped image data
            image = mime_data.imageData()
            if image:
                self.process_pasted_image(image)
                event.acceptProposedAction()
                
        elif mime_data.hasUrls():
            # Handle dropped image files
            urls = mime_data.urls()
            for url in urls:
                if url.isLocalFile():
                    file_path = url.toLocalFile()
                    if self.is_image_file(file_path):
                        self.process_image_file(file_path)
                        event.acceptProposedAction()
                        break  # Process only first image
                    


    def build_chat_html(self):
           return build_chat_html_with_katex(self.chat_history)


    def get_conversation_as_latex(self):
        """
        Extract the conversation history as LaTeX text.
        Formats all messages from the chat history into a single LaTeX document.
        """
        if not self.chat_history:
            return ""
        
        latex_parts = []
        
        for msg in self.chat_history:
            sender = msg['sender']
            message = msg['message']
            timestamp = msg['timestamp']
            
            # Format each message
            if sender == "You":
                latex_parts.append(f"\\textbf{{Question [{timestamp}]:}}\n\n{message}\n")
            elif sender == "AI":
                latex_parts.append(f"\\textbf{{AI Response [{timestamp}]:}}\n\n{message}\n")
            elif sender == "System":
                latex_parts.append(f"\\textit{{[{timestamp}] {message}}}\n")
        
        return "\n".join(latex_parts)
               
    def get_last_ai_exercise(self):
        """
        Extract only the last AI-generated exercise from conversation.
        Useful if you want to save just the exercise, not the whole chat.
        """
        for msg in reversed(self.chat_history):
            if msg['sender'] == 'AI':
                message = msg['message']
                # Check if it contains an exercise (has math delimiters)
                if '$' in message or '\\[' in message or '\\(' in message:
                    # Try to extract just the exercise part, removing "Here's a generated exercise:" etc.
                    lines = message.split('\n')
                    exercise_lines = []
                    started = False
                    for line in lines:
                        # Skip introduction lines
                        if not started and ('here' in line.lower() or 'generated' in line.lower()):
                            continue
                        started = True
                        exercise_lines.append(line)
                    return '\n'.join(exercise_lines).strip()
        return None


    def get_last_ai_solution(self):
        """
        Extract only the last AI-generated solution from conversation.
        """
        for msg in reversed(self.chat_history):
            if msg['sender'] == 'AI':
                message = msg['message']
                # Check if it contains solution keywords
                if any(word in message.lower() for word in ['solution', 'step', 'solve', 'answer']):
                    # Try to extract just the solution part
                    lines = message.split('\n')
                    solution_lines = []
                    started = False
                    for line in lines:
                        if not started and ('here' in line.lower() or 'solution' in line.lower()):
                            continue
                        started = True
                        solution_lines.append(line)
                    return '\n'.join(solution_lines).strip()
        return None



    @staticmethod
    def _app_dir():
        """Return (and create if needed) the %APPDATA%\\YasmeenTex folder."""
        from pathlib import Path
        appdata = os.getenv('APPDATA', '')
        if appdata:
            folder = Path(appdata) / 'YasmeenTex'
        else:
            # Fallback: use the directory that contains main_window.py
            folder = Path(__file__).parent
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def load_ai_config(self):
        """Load AI configuration from file."""
        try:
            path = self._app_dir() / 'ai_config.json'
            with open(path, 'r') as f:
                return json.load(f)
        except:
            # Default configuration
            return {
                'mode': 'offline',
                'provider': 'groq',
                'api_key': '',
                'model': 'llama3-8b-8192',
                'enabled': False
            }

    def save_ai_config(self):
        """Save AI configuration to file."""
        try:
            path = self._app_dir() / 'ai_config.json'
            with open(path, 'w') as f:
                json.dump(self.ai_config, f, indent=2)
        except Exception as e:
            print(f"Failed to save AI config: {e}")        
    
    
    def toggle_tree_panel(self):
        """Show or hide the topic tree panel."""
        self.tree_visible = not self.tree_visible
        
        if self.tree_visible:
            self.tree_widget_container.show()
            if self.solution_visible:
                QTimer.singleShot(10, lambda: self.splitter.setSizes(self._tree_three_panel_sizes))
            else:
                QTimer.singleShot(10, lambda: self.splitter.setSizes(self._tree_two_panel_sizes))
        else:
            self.tree_widget_container.hide()
            if self.solution_visible:
                QTimer.singleShot(10, lambda: self.splitter.setSizes(self._three_panel_sizes))
            else:
                QTimer.singleShot(10, lambda: self.splitter.setSizes(self._two_panel_sizes))
        
        self.update_tree_ui()
    
    def update_tree_ui(self):
        """Update tree button and menu text based on visibility state."""
        if self.tree_visible:
            self.toggle_tree_btn.setText(self.tr("hide_maths_tree"))
            self.toggle_tree_btn.setChecked(True)
            self.toggle_tree_action.setText(self.tr("hide"))
            self.toggle_tree_action.setChecked(True)
        else:
            self.toggle_tree_btn.setText(self.tr("show_maths_tree"))
            self.toggle_tree_btn.setChecked(False)
            self.toggle_tree_action.setText(self.tr("show_maths_tree"))
            self.toggle_tree_action.setChecked(False)
    
    def toggle_solution_panel(self):
        """Show or hide the solution panel with proper size management."""
        if not self.has_solution:
            return
            
        self.solution_visible = not self.solution_visible
        
        if self.solution_visible:
            self.solution_widget.show()
            if self.tree_visible:
                QTimer.singleShot(10, lambda: self.splitter.setSizes(self._tree_three_panel_sizes))
            else:
                QTimer.singleShot(10, lambda: self.splitter.setSizes(self._three_panel_sizes))
        else:
            self.solution_widget.hide()
            if self.tree_visible:
                QTimer.singleShot(10, lambda: self.splitter.setSizes(self._tree_two_panel_sizes))
            else:
                QTimer.singleShot(10, lambda: self.splitter.setSizes(self._two_panel_sizes))
        
        self.update_solution_ui()
    
    def update_solution_ui(self):
        """Update solution button and menu text based on visibility state."""
        # Get translations for current language
        trans = translations.get(self.current_language, translations['en'])
        
        if self.solution_visible:
            solution_text = trans.get("hide_solution", "Hide Solution")
            self.toggle_solution_btn.setText(solution_text)
            self.toggle_solution_btn.setChecked(True)
            self.toggle_solution_action.setText(solution_text)
            self.toggle_solution_action.setChecked(True)
        else:
            solution_text = trans.get("show_solution", "Show Solution")
            self.toggle_solution_btn.setText(solution_text)
            self.toggle_solution_btn.setChecked(False)
            self.toggle_solution_action.setText(solution_text)
            self.toggle_solution_action.setChecked(False)
        
        self.toggle_solution_btn.setEnabled(self.has_solution)
        self.toggle_solution_action.setEnabled(self.has_solution)
    

    def on_topic_selected(self, item, column):
        """Handle topic selection from tree - delegate to tree widget."""
        self.topic_tree.on_topic_selected(item, column)    
        
    def load_exercise(self, exercise_id: int):
        """Load and display an exercise."""
        self.current_exercise_id = exercise_id
        exercise_data = self.db.get_exercise(exercise_id)
        
        if not exercise_data:
            return
        
        ex_id, keycode, name, latex, solution, date, level = exercise_data
        keywords = self.db.get_keywords(exercise_id)
        topic_ids = self.db.get_exercise_topics(exercise_id)
        
        self.current_exercise_data = (ex_id, keycode, name, latex, solution, 
                                     date, level, keywords, topic_ids)
        
        # Check if solution exists
        self.has_solution = bool(solution and solution.strip())
        
        # Render exercise with current language
        KaTeXRenderer.render(self.exercise_view, latex, name, self.current_language)
        
        # Render solution if exists
        if self.has_solution:
            KaTeXRenderer.render(self.solution_view, solution, "Solution", self.current_language)
        else:
            KaTeXRenderer.render(self.solution_view, "", "No solution available", self.current_language)
            if self.solution_visible:
                self.solution_visible = False
                self.solution_widget.hide()
                if self.tree_visible:
                    QTimer.singleShot(10, lambda: self.splitter.setSizes(
                        self._tree_two_panel_sizes))
                else:
                    QTimer.singleShot(10, lambda: self.splitter.setSizes(
                        self._two_panel_sizes))
        
        self.update_solution_ui()
        
        # Enable print button now that an exercise is loaded
        if hasattr(self, 'print_btn'):
            self.print_btn.setEnabled(True)
        
        # Update status bar
        status_parts = [f"Exercise: {name}", f"Keycode: {keycode}"]
        if level:
            status_parts.append(f"Level: {level}")
        if keywords:
            status_parts.append(f"Keywords: {', '.join(keywords)}")
        if self.has_solution:
            status_parts.append("✓ Has solution")
        
        self.statusBar().showMessage(" | ".join(status_parts))
    
    def clear_views(self):
        """Clear the exercise and solution views."""
        KaTeXRenderer.render(self.exercise_view, "", "")
        KaTeXRenderer.render(self.solution_view, "", "")
        self.current_exercise_id = None
        self.current_exercise_data = None
        self.has_solution = False
        self.update_solution_ui()
        if hasattr(self, 'print_btn'):
            self.print_btn.setEnabled(False)
    
    def open_search_dialog(self):
        """Open the search dialog."""
        dialog = SearchDialog(self, self.db)
        
        if dialog.exec_() == SearchDialog.Accepted:
            selected_exercise_id = dialog.get_selected_exercise_id()
            if selected_exercise_id:
                self.load_exercise(selected_exercise_id)
    
    def add_exercise(self):
        """Open dialog to add a new exercise."""
        dialog = AddEditExerciseDialog(
            self,
            None,
            self.db.get_all_levels(),
            self.db.get_topic_tree()
        )
        
        if dialog.exec_() == AddEditExerciseDialog.Accepted:
            data = dialog.get_data()
            
            try:
                ex_id, keycode = self.db.add_exercise(
                    name=data['name'],
                    latex=data['latex'],
                    solution=data['solution'],
                    level=data['level'],
                    topic_ids=data['topic_ids'],
                    keywords=data['keywords']
                )
                
                QMessageBox.information(
                    self, 
                    "Success", 
                    f"Exercise added successfully!\nKeycode: {keycode}"
                )
                self.refresh_all()
                self.load_exercise(ex_id)
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to add exercise:\n{str(e)}")
    
    def edit_exercise(self):
        """Open dialog to edit the current exercise."""
        if not self.current_exercise_data:
            QMessageBox.warning(self, "No Selection", self.tr("please_select_exercise_to_edit"))
            return
        
        dialog = AddEditExerciseDialog(
            self,
            self.current_exercise_data,
            self.db.get_all_levels(),
            self.db.get_topic_tree()
        )
        
        if dialog.exec_() == AddEditExerciseDialog.Accepted:
            data = dialog.get_data()
            
            try:
                self.db.update_exercise(
                    exercise_id=self.current_exercise_id,
                    name=data['name'],
                    latex=data['latex'],
                    solution=data['solution'],
                    level=data['level'],
                    topic_ids=data['topic_ids'],
                    keywords=data['keywords']
                )
                
                QMessageBox.information(self, "Success", "Exercise updated successfully!")
                self.refresh_all()
                self.load_exercise(self.current_exercise_id)
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to update exercise:\n{str(e)}")
    
    def delete_exercise(self):
        """Delete the current exercise after confirmation."""
        if not self.current_exercise_id:
            QMessageBox.warning(self, "No Selection", self.tr("please_select_exercise_to_delete"))
            return
        
        reply = QMessageBox.question(
            self,
            "Confirm Deletion",
            f"Are you sure you want to delete the exercise:\n'{self.current_exercise_data[2]}'?\nKeycode: {self.current_exercise_data[1]}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                self.db.delete_exercise(self.current_exercise_id)
                QMessageBox.information(self, "Success", "Exercise deleted successfully!")
                self.clear_views()
                self.refresh_all()
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete exercise:\n{str(e)}")
    
    def refresh_all(self):
        """Refresh tree and current exercise."""
        self.topic_tree.load_topic_tree()
        if self.current_exercise_id:
            self.load_exercise(self.current_exercise_id)
    
    def show_statistics(self):
        """Show database statistics dialog."""
        stats = self.db.get_statistics()
        dialog = StatisticsDialog(self, stats)
        dialog.exec_()

    def show_help(self):
        """Show help dialog with multilingual content."""
        dialog = QDialog(self)
        dialog.setWindowTitle(self.tr("help_content"))
        dialog.setMinimumWidth(800)
        dialog.setMinimumHeight(500)
        dialog.setMaximumHeight(900)
        
        layout = QVBoxLayout(dialog)
        
        # Create scroll area for the help content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Content widget
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(15)
        
        # Get translations for current language
        trans = translations.get(self.current_language, translations['en'])
        
        # Title
        title = QLabel(f"<h1>{trans.get('help_title', 'YasmeenTeX Help Guide')}</h1>")
        title.setAlignment(Qt.AlignCenter)
        content_layout.addWidget(title)
        
        # Introduction
        intro = QLabel(trans.get("help_intro", "Welcome to YasmeenTeX! This application helps you manage and view LaTeX exercises with AI assistance."))
        intro.setWordWrap(True)
        intro.setStyleSheet("font-size: 14px; margin: 10px 0;")
        content_layout.addWidget(intro)
        
        # Features section
        features_title = QLabel(f"<h2>{trans.get('help_features', 'Main Features:')}</h2>")
        content_layout.addWidget(features_title)
        
        # Exercises
        exercises_title = QLabel(f"<h3>{trans.get('help_exercises', 'Exercises Tab:')}</h3>")
        content_layout.addWidget(exercises_title)
        
        exercises_desc = QLabel(trans.get("help_exercises_desc", ""))
        exercises_desc.setWordWrap(True)
        exercises_desc.setStyleSheet("margin-left: 20px;")
        content_layout.addWidget(exercises_desc)
        
        # AI Assistant
        ai_title = QLabel(f"<h3>{trans.get('help_ai_assistant', 'AI Assistant Tab:')}</h3>")
        content_layout.addWidget(ai_title)
        
        ai_desc = QLabel(trans.get("help_ai_assistant_desc", ""))
        ai_desc.setWordWrap(True)
        ai_desc.setStyleSheet("margin-left: 20px;")
        content_layout.addWidget(ai_desc)
        
        # Search
        search_title = QLabel(f"<h3>{trans.get('help_search', 'Search Function:')}</h3>")
        content_layout.addWidget(search_title)
        
        search_desc = QLabel(trans.get("help_search_desc", ""))
        search_desc.setWordWrap(True)
        search_desc.setStyleSheet("margin-left: 20px;")
        content_layout.addWidget(search_desc)
        
        # Topics
        topics_title = QLabel(f"<h3>{trans.get('help_topics', 'Topic Management:')}</h3>")
        content_layout.addWidget(topics_title)
        
        topics_desc = QLabel(trans.get("help_topics_desc", ""))
        topics_desc.setWordWrap(True)
        topics_desc.setStyleSheet("margin-left: 20px;")
        content_layout.addWidget(topics_desc)
        
        # AI Configuration
        ai_config_title = QLabel(f"<h3>{trans.get('help_ai_config', 'AI Configuration:')}</h3>")
        content_layout.addWidget(ai_config_title)
        
        ai_config_desc = QLabel(trans.get("help_ai_config_desc", ""))
        ai_config_desc.setWordWrap(True)
        ai_config_desc.setStyleSheet("margin-left: 20px;")
        content_layout.addWidget(ai_config_desc)
        
        # Keyboard Shortcuts
        shortcuts_title = QLabel(f"<h3>{trans.get('help_shortcuts', 'Keyboard Shortcuts:')}</h3>")
        content_layout.addWidget(shortcuts_title)
        
        shortcuts_desc = QLabel(trans.get("help_shortcuts_desc", ""))
        shortcuts_desc.setWordWrap(True)
        shortcuts_desc.setStyleSheet("margin-left: 20px; font-family: 'Courier New', monospace;")
        content_layout.addWidget(shortcuts_desc)
        
        # Tips
        tips_title = QLabel(f"<h3>{trans.get('help_tips', 'Tips:')}</h3>")
        content_layout.addWidget(tips_title)
        
        tips_desc = QLabel(trans.get("help_tips_desc", ""))
        tips_desc.setWordWrap(True)
        tips_desc.setStyleSheet("margin-left: 20px; font-style: italic;")
        content_layout.addWidget(tips_desc)
        
        # Add stretch to push content to top
        content_layout.addStretch()
        
        # Set the scroll area content
        scroll_area.setWidget(content_widget)
        layout.addWidget(scroll_area)
        
        # Close button
        close_btn = QPushButton(trans.get("help_close", "Close"))
        close_btn.clicked.connect(dialog.accept)
        close_btn.setFixedWidth(100)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(close_btn)
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        
        dialog.exec_()
    
    def show_about(self):
        """Show about dialog with increased width, adapted to current language."""
        # Create custom message box
        msg_box = QMessageBox(self)
        msg_box.setMinimumWidth(800)
        msg_box.setMinimumHeight(500)
        msg_box.setMaximumHeight(900)

        # Get translations for current language
        lang = self.current_language
        trans = translations.get(lang, translations['en'])
        
        # Set window title
        msg_box.setWindowTitle(trans.get("about", "About") + " YasmeenTeX 2.0")
        
        # Content based on language
        if lang == 'fr':
            text = (
                "<h2>YasmeenTeX 2.0</h2>"
                "<p>Application de gestion et de visualisation d'exercices LaTeX avec assistance IA.</p>"
                "<p><b>Fonctionnalités :</b></p>"
                "<ul>"
                "<li>Organisation hiérarchique par arbre thématique</li>"
                "<li>Système de codes uniques (EX-YYYYMMDD.HHMMSS.F)</li>"
                "<li>Support multi-thèmes par exercice</li>"
                "<li>Recherche avancée avec filtrage</li>"
                "<li>Génération d'exercices et création de solutions par IA</li>"
                "<li>Assistant conversationnel IA pour questions mathématiques</li>"
                "<li>Peuplement automatique de la base avec exercices générés par IA</li>"
                "<li>Copie des réponses IA individuelles avec contenu LaTeX</li>"
                "<li>Visualisation des exercices et solutions rendus avec KaTeX</li>"
                "<li>Affichage/masquage des solutions et de l'arbre</li>"
                "<li>Support amélioré du rendu LaTeX</li>"
                "<li>Gestion des thèmes (ajouter, renommer, supprimer)</li>"
                "<li>Réorganisation par glisser-déposer</li>"
                "<li>Raccourcis clavier pour le déplacement des thèmes</li>"
                "</ul>"
                "<p><b>Technologies :</b></p>"
                "<ul>"
                "<li><b>KaTeX</b> - Composition mathématique rapide pour le web (Licence MIT)</li>"
                "<li><b>Fournisseurs IA</b> - OpenAI, Anthropic Claude, Google Gemini, Groq</li>"
                "<li><b>PyQt5</b> - Bindings Python Qt pour l'interface graphique</li>"
                "<li><b>SQLite</b> - Base de données embarquée</li>"
                "</ul>"
                "<p><b>Informations de licence :</b></p>"
                "<p>YasmeenTeX est sous licence GPLv3</p>"
                "<p>KaTeX est sous licence MIT<br>"
                "Copyright (c) 2013-2020 Khan Academy et autres contributeurs<br>"
                "https://github.com/KaTeX/KaTeX</p>"
                "<p><b>Développeur :</b>Maher Berzig</p>"
            )
        elif lang == 'ar':
            text = (
                "<h2>YasmeenTeX 2.0</h2>"
                "<p>تطبيق لإدارة وعرض تمارين LaTeX مع مساعدة الذكاء الاصطناعي.</p>"
                "<p><b>المميزات:</b></p>"
                "<ul>"
                "<li>تنظيم هرمي باستخدام شجرة المواضيع</li>"
                "<li>نظام رموز فريد (EX-YYYYMMDD.HHMMSS.F)</li>"
                "<li>دعم تعدد المواضيع في التمرين الواحد</li>"
                "<li>بحث متقدم مع التصفية</li>"
                "<li>إنشاء تمارين وحلول بواسطة الذكاء الاصطناعي</li>"
                "<li>مساعد محادثة بالذكاء الاصطناعي للأسئلة الرياضية</li>"
                "<li>ملء قاعدة البيانات تلقائياً بتمارين من إنشاء الذكاء الاصطناعي</li>"
                "<li>نسخ ردود الذكاء الاصطناعي الفردية بمحتوى LaTeX</li>"
                "<li>عرض التمارين والحلول مُمثلة باستخدام KaTeX</li>"
                "<li>إظهار/إخفاء الحلول والشجرة</li>"
                "<li>دعم محسن لتمثيل LaTeX</li>"
                "<li>إدارة المواضيع (إضافة، إعادة تسمية، حذف)</li>"
                "<li>إعادة التنظيم بالسحب والإفلات</li>"
                "<li>اختصارات لوحة المفاتيح لتحريك المواضيع</li>"
                "</ul>"
                "<p><b>التقنيات:</b></p>"
                "<ul>"
                "<li><b>KaTeX</b> - تنضيد رياضي سريع للويب (رخصة MIT)</li>"
                "<li><b>مزودو الذكاء الاصطناعي</b> - OpenAI, Anthropic Claude, Google Gemini, Groq</li>"
                "<li><b>PyQt5</b> - روابط Python Qt للواجهة الرسومية</li>"
                "<li><b>SQLite</b> - قاعدة بيانات مدمجة</li>"
                "</ul>"
                "<p><b>معلومات الترخيص:</b></p>"
                "<p>YasmeenTeX مرخص بموجب رخصة GPLv3</p>"
                "<p>KaTeX مرخص بموجب رخصة MIT<br>"
                "حقوق النشر (c) 2013-2020 Khan Academy ومساهمون آخرون<br>"
                "https://github.com/KaTeX/KaTeX</p>"
                "<p><b>المطور:</b> ماهر برزيق</p>"
            )
        else:  # English (default)
            text = (
                "<h2>YasmeenTeX 2.0</h2>"
                "<p>Application for managing and viewing LaTeX exercises with AI assistance.</p>"
                "<p><b>Features:</b></p>"
                "<ul>"
                "<li>Hierarchical topic tree organization</li>"
                "<li>Unique keycode system (EX-YYYYMMDD.HHMMSS.F)</li>"
                "<li>Multi-topic exercise support</li>"
                "<li>Advanced search with filtering</li>"
                "<li>AI-powered exercise generation and solution creation</li>"
                "<li>AI chat assistant for mathematical questions</li>"
                "<li>Automatic database population with AI-generated exercises</li>"
                "<li>Copy individual AI responses with LaTeX content</li>"
                "<li>View exercises and solutions rendered with KaTeX</li>"
                "<li>Toggle solution and tree visibility</li>"
                "<li>Enhanced LaTeX rendering support</li>"
                "<li>Topic management (add, rename, delete topics)</li>"
                "<li>Drag & drop topic reorganization</li>"
                "<li>Keyboard shortcuts for topic movement</li>"
                "</ul>"
                "<p><b>Technologies:</b></p>"
                "<ul>"
                "<li><b>KaTeX</b> - Fast math typesetting for the web (MIT License)</li>"
                "<li><b>AI Providers</b> - OpenAI, Anthropic Claude, Google Gemini, Groq</li>"
                "<li><b>PyQt5</b> - Python Qt bindings for GUI</li>"
                "<li><b>SQLite</b> - Embedded database</li>"
                "</ul>"
                "<p><b>License Information:</b></p>"
                "<p>YasmeenTeX is licensed under the GPLv3 License</p>"
                "<p>KaTeX is licensed under the MIT License<br>"
                "Copyright (c) 2013-2020 Khan Academy and other contributors<br>"
                "https://github.com/KaTeX/KaTeX</p>"
                "<p><b>Developer:</b> (ɔ) Maher Berzig</p>"
            )
        
        msg_box.setText(text)
        msg_box.setTextFormat(Qt.RichText)

        # ✅ ADD THIS: Replace the standard OK button with translated version
        # Remove the standard button and add custom translated button
        msg_box.setStandardButtons(QMessageBox.Ok)
        ok_button = msg_box.button(QMessageBox.Ok)
        ok_button.setText(self.tr("ok"))  # This will use "OK", "موافق", or "OK" based on language

        # Increase width by adjusting the internal label
        for button in msg_box.buttons():
            button.setMinimumWidth(100)  # optional: make buttons wider too

        # Force the message box to be wider
        msg_box.setStyleSheet("QLabel{min-width: 600px;}")
        msg_box.exec_()
    
    
    def resizeEvent(self, event):
        """Handle window resize to maintain proper splitter proportions."""
        super().resizeEvent(event)
        sizes = self.splitter.sizes()
        
        if self.tree_visible and self.solution_visible and len(sizes) >= 3:
            self._tree_three_panel_sizes = sizes
        elif self.tree_visible and not self.solution_visible and len(sizes) >= 2:
            self._tree_two_panel_sizes = [sizes[0], sizes[1], 0]
        elif not self.tree_visible and self.solution_visible and len(sizes) >= 2:
            self._three_panel_sizes = [0, sizes[1], sizes[2]]
        elif not self.tree_visible and not self.solution_visible:
            self._two_panel_sizes = [0, sizes[1], 0]
            
            
    # def show_settings_dialog(self):
        # """Show settings dialog for language and discipline."""
        # dialog = SettingsDialog(
            # self, 
            # self.current_language,
            # self.current_discipline,
            # self.custom_discipline
        # )
        
        # if dialog.exec_() == QDialog.Accepted:
            # settings = dialog.get_settings()
            # self.current_language = settings['language']
            # self.current_discipline = settings['discipline']
            # self.custom_discipline = settings.get('custom_discipline', '')
            
            # # Save settings to config file
            # self.save_settings()
            
            # # Force update the entire UI with the new language
            # self.force_ui_language_update()
            
            # # Specifically update AI Assistant tab language
            # if hasattr(self, 'ai_assistant_tab'):
                # self.ai_assistant_tab.update_language()

            # self.update_solution_ui()

            # # ✅ Translated message box with custom OK text
            # msg = QMessageBox(self)
            # msg.setIcon(QMessageBox.Information)
            # msg.setWindowTitle(self.tr("settings"))
            # msg.setText(self.tr("settings_saved_successfully"))
            # msg.addButton(self.tr("ok"), QMessageBox.AcceptRole)
            # msg.exec_()

    def show_settings_dialog(self):
        """Show settings dialog for language and discipline."""
        try:
            dialog = SettingsDialog(
                self, 
                self.current_language,
                self.current_discipline,
                self.custom_discipline,
                self.db_path          # ← new: current database path
            )
            
            if dialog.exec_() == QDialog.Accepted:
                settings = dialog.get_settings()
                self.current_language = settings['language']
                self.current_discipline = settings['discipline']
                self.custom_discipline = settings.get('custom_discipline', '')

                # ── Database path change ──────────────────────────────────
                new_db_path = settings.get('db_path', self.db_path)
                if new_db_path != self.db_path:
                    self.db_path = new_db_path
                    # Close the current connection and open the new database
                    try:
                        self.db.close()
                        self.db = DatabaseManager(self.db_path)
                        # Propagate the new DatabaseManager to dependent widgets
                        if hasattr(self, 'topic_tree'):
                            self.topic_tree.db = self.db
                            self.topic_tree.main_window = self
                        if hasattr(self, 'ai_assistant_tab'):
                            self.ai_assistant_tab.db = self.db
                        # Clear the exercise view since the DB has changed
                        self.clear_views()
                    except Exception as e:
                        QMessageBox.critical(
                            self, "Database Error",
                            f"Could not open database:\n{self.db_path}\n\n{str(e)}"
                        )
                        return
                # ─────────────────────────────────────────────────────────

                # Save settings to config file
                self.save_settings()
                
                # Force update the entire UI with the new language - WITH ERROR HANDLING
                try:
                    self.force_ui_language_update()
                except Exception as e:
                    print(f"Error in force_ui_language_update: {e}")
                    # Fallback: try individual updates
                    self.update_menu_language()
                    self.update_exercises_tab_language()
                
                # Specifically update AI Assistant tab language - WITH ERROR HANDLING
                if hasattr(self, 'ai_assistant_tab') and self.ai_assistant_tab:
                    try:
                        self.ai_assistant_tab.update_language()
                    except Exception as e:
                        print(f"Error updating AI assistant tab: {e}")

                # Update solution UI
                try:
                    self.update_solution_ui()
                except Exception as e:
                    print(f"Error updating solution UI: {e}")

                # Reload topic tree after any DB change
                try:
                    self.topic_tree.load_topic_tree()
                except Exception as e:
                    print(f"Error reloading topic tree: {e}")

                # ✅ Translated message box with custom OK text
                try:
                    msg = QMessageBox(self)
                    msg.setIcon(QMessageBox.Information)
                    msg.setWindowTitle(self.tr("settings"))
                    msg.setText(self.tr("settings_saved_successfully"))
                    msg.addButton(self.tr("ok"), QMessageBox.AcceptRole)
                    msg.exec_()
                except Exception as e:
                    print(f"Error showing confirmation message: {e}")
                    
        except Exception as e:
            print(f"Critical error in show_settings_dialog: {e}")
            QMessageBox.critical(self, "Error", f"Failed to change settings: {str(e)}")
                
            
    def update_ui_language(self):
        """Update all UI elements with current language immediately."""
        try:
            # Update menu bar
            if hasattr(self, 'menuBar') and self.menuBar():
                self.update_menu_language()
            
            # Update main window title
            self.setWindowTitle("YasmeenTeX")
            
            # Update tab names if tab_widget exists
            if hasattr(self, 'tab_widget') and self.tab_widget:
                self.tab_widget.setTabText(0, self.tr("exercises_tab"))
                self.tab_widget.setTabText(1, self.tr("ai_assistant_tab"))
            
            # Update buttons and labels in exercises tab
            self.update_exercises_tab_language()
            
            # Update AI assistant tab if it exists
            if hasattr(self, 'ai_assistant_tab'):
                self.ai_assistant_tab.update_language()
                
            
            # Update topic tree if it exists
            if hasattr(self, 'topic_tree'):
                self.topic_tree.update_language()
            
            # Refresh current exercise to apply language direction if we have one
            if hasattr(self, 'current_exercise_id') and self.current_exercise_id:
                self.load_exercise(self.current_exercise_id)
                
        except Exception as e:
            print(f"Warning: Error updating UI language: {e}")
        
    def update_menu_language(self):
        """Update all menu texts using the translations dictionary."""
        #print(f"Updating menu language to: {self.current_language}")
        menubar = self.menuBar()
        lang = self.current_language
        
        # Get translations for current language
        trans = translations.get(lang, translations['en'])
        
        # Clear and rebuild menus to ensure complete translation
        menubar.clear()
        
        # Helper function to add mnemonics with proper RTL support
        def add_mnemonic(text, mnemonic_letter):
            if lang == 'ar':
                # For Arabic: use Zero Width Non-Joiner after ampersand to preserve text shaping
                return f"\u200C{text}"
            else:
                # For other languages: standard mnemonic format
                return f"&{text}"
        
        # File menu with mnemonic - F
        file_text = trans.get("file", "File")
        file_menu = menubar.addMenu(add_mnemonic(file_text, "F"))
        
        add_action = QAction(trans.get("add_exercise", "Add Exercise"), self)
        add_action.setShortcut("Ctrl+N")
        add_action.triggered.connect(self.add_exercise)
        file_menu.addAction(add_action)
        
        search_action = QAction(trans.get("search_exercises", "Search Exercises"), self)
        search_action.setShortcut("Ctrl+F")
        search_action.triggered.connect(self.open_search_dialog)
        file_menu.addAction(search_action)
        
        file_menu.addSeparator()
        
        add_root_topic_action = QAction(trans.get("add_root_topic", "Add Root Topic"), self)
        add_root_topic_action.triggered.connect(self.topic_tree.add_root_topic)
        file_menu.addAction(add_root_topic_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction(trans.get("exit", "Exit"), self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu with mnemonic - E
        edit_text = trans.get("edit", "Edit")
        edit_menu = menubar.addMenu(add_mnemonic(edit_text, "E"))
        
        edit_action = QAction(trans.get("edit_exercise", "Edit Exercise"), self)
        edit_action.setShortcut("Ctrl+E")
        edit_action.triggered.connect(self.edit_exercise)
        edit_menu.addAction(edit_action)
        
        delete_action = QAction(trans.get("delete_exercise", "Delete Exercise"), self)
        delete_action.setShortcut("Delete")
        delete_action.triggered.connect(self.delete_exercise)
        edit_menu.addAction(delete_action)

        edit_menu.addSeparator()

        export_action = QAction(trans.get("export_exercises", "Export Exercises to LaTeX…"), self)
        export_action.setShortcut("Ctrl+X")
        export_action.triggered.connect(self.open_export_dialog)
        edit_menu.addAction(export_action)

        edit_menu.addSeparator()
        
        refresh_action = QAction(trans.get("refresh", "Refresh"), self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.refresh_all)
        edit_menu.addAction(refresh_action)
        
        # View menu with mnemonic - V
        view_text = trans.get("view", "View")
        view_menu = menubar.addMenu(add_mnemonic(view_text, "V"))
        
        stats_action = QAction(trans.get("statistics", "Statistics"), self)
        stats_action.triggered.connect(self.show_statistics)
        view_menu.addAction(stats_action)

        # Show/Hide Solution menu item
        self.toggle_solution_action = QAction("", self)  # Text will be set below
        self.toggle_solution_action.setCheckable(True)
        self.toggle_solution_action.setChecked(self.solution_visible)
        self.toggle_solution_action.triggered.connect(self.toggle_solution_panel)
        view_menu.addAction(self.toggle_solution_action)
        
        # Show/Hide Tree menu item
        self.toggle_tree_action = QAction("", self)  # Text will be set below
        self.toggle_tree_action.setCheckable(True)
        self.toggle_tree_action.setChecked(self.tree_visible)
        self.toggle_tree_action.triggered.connect(self.toggle_tree_panel)
        view_menu.addAction(self.toggle_tree_action)
        
        # Tools menu with mnemonic - T
        tools_text = trans.get("tools", "Tools")
        tools_menu = menubar.addMenu(add_mnemonic(tools_text, "T"))
        
        ai_config_action = QAction(trans.get("ai_configuration", "AI Configuration"), self)
        ai_config_action.triggered.connect(self.show_ai_config_dialog)
        tools_menu.addAction(ai_config_action)
        
        # Options menu with mnemonic - O
        options_text = trans.get("options", "Options")
        options_menu = menubar.addMenu(add_mnemonic(options_text, "O"))
        
        settings_action = QAction(trans.get("settings", "Settings"), self)
        settings_action.triggered.connect(self.show_settings_dialog)
        options_menu.addAction(settings_action)
        
        # Help menu with mnemonic - H
        help_text = trans.get("help", "Help")
        help_menu = menubar.addMenu(add_mnemonic(help_text, "H"))

        # Add Help action before About
        help_action = QAction(trans.get("help_content", "Help"), self)
        help_action.triggered.connect(self.show_help)
        help_menu.addAction(help_action)

        help_menu.addSeparator()

        about_action = QAction(trans.get("about", "About"), self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
        # Update dynamic menu items (solution and tree visibility)
        self.update_dynamic_menu_items()
    
    def update_dynamic_menu_items(self):
        """Update menu items that change based on state (solution/tree visibility)."""
        trans = translations.get(self.current_language, translations['en'])
        
        if self.solution_visible:
            self.toggle_solution_action.setText(trans.get("hide_solution", "Hide Solution"))
        else:
            self.toggle_solution_action.setText(trans.get("show_solution", "Show Solution"))
        
        if self.tree_visible:
            self.toggle_tree_action.setText(trans.get("hide_maths_tree", "Hide Maths Tree"))
        else:
            self.toggle_tree_action.setText(trans.get("show_maths_tree", "Show Maths Tree"))
        

    def update_exercises_tab_language(self):
        """Update exercises tab UI elements."""
        lang = self.current_language
        trans = translations.get(lang, translations['en'])
        
        BUTTON_WIDTH = 220
        
         # Update solution button - FIXED VERSION
        if hasattr(self, 'toggle_solution_btn'):
            if self.solution_visible:
                new_text = trans.get("hide_solution_btn", "Hide Solution")
            else:
                new_text = trans.get("show_solution_btn", "Show Solution")
            self.toggle_solution_btn.setText(new_text)
        
        # Update search button
        for child in self.findChildren(QPushButton):
            text = child.text()
            if "Search Exercises" in text or "Rechercher" in text or "بحث" in text:
                new_text = trans.get("search_exercises_btn", "🔍 Search Exercises")
                child.setText(new_text)
                
                # Set fixed width that works for all languages
                child.setFixedWidth(BUTTON_WIDTH)  # Wide enough for French "Rechercher des exercices"
                break
        
        # Update tree button
        if hasattr(self, 'toggle_tree_btn'):
            if self.tree_visible:
                new_text = trans.get("hide_maths_tree_btn", "Hide Tree")
                self.toggle_tree_btn.setText(new_text)
            else:
                new_text = trans.get("show_maths_tree_btn", "Show Tree")
                self.toggle_tree_btn.setText(new_text)
            
            # Set fixed width that works for all languages
            self.toggle_tree_btn.setFixedWidth(BUTTON_WIDTH)
        
        # Update add exercise button
        for child in self.findChildren(QPushButton):
            text = child.text()
            if "Add Exercise" in text or "Ajouter" in text or "إضافة" in text and "+" in text:
                new_text = trans.get("add_exercise_btn", "+ Add Exercise")
                child.setText(new_text)
                
                # Set fixed width that works for all languages
                child.setFixedWidth(BUTTON_WIDTH)
                break
        
        # Update solution button
        if hasattr(self, 'toggle_solution_btn') and self.has_solution:
            if self.solution_visible:
                new_text = trans.get("hide_solution_btn", "Hide Solution")
                self.toggle_solution_btn.setText(new_text)
            else:
                new_text = trans.get("show_solution_btn", "Show Solution")
                self.toggle_solution_btn.setText(new_text)
            
            # Set fixed width that works for all languages
            self.toggle_solution_btn.setFixedWidth(BUTTON_WIDTH)
        
        # Update tree header
        for child in self.findChildren(QLabel):
            text = child.text()
            if "Tree" in text or "Arbre" in text or "شجرة" in text:
                child.setText(trans.get("maths_tree", "Tree"))
                break
        
        # Update add main topic button
        if hasattr(self, 'add_main_topic_btn'):
            new_text = trans.get("add_main_topic", "+ Add Main Topic")
            self.add_main_topic_btn.setText(new_text)
            
            # Set fixed width that works for all languages
            self.add_main_topic_btn.setFixedWidth(BUTTON_WIDTH)
        
        # Update exercise and solution labels
        for child in self.findChildren(QLabel):
            text = child.text()
            if text in ["Exercise", "Exercice", "تمرين"]:
                child.setText(trans.get("exercise", "Exercise"))
            elif text in ["Solution", "Solution", "حل"]:
                child.setText(trans.get("solution", "Solution"))
            
    def tr(self, text):
        """Get translation for text using the translations dictionary."""
        lang = getattr(self, 'current_language', 'en')
        return translations.get(lang, {}).get(text, translations['en'].get(text, text))
    
    def load_settings(self):
        """Load application settings."""
        try:
            path = self._app_dir() / 'app_settings.json'
            if path.exists():
                with open(path, 'r') as f:
                    settings = json.load(f)
                    
                # Validate settings
                self.current_language = settings.get('language', 'en')
                self.current_discipline = settings.get('discipline', 'mathematics')
                self.custom_discipline = settings.get('custom_discipline', '')
                self.db_path = settings.get('db_path', 'exercises.db')
                
                # Validate language value
                if self.current_language not in ['en', 'fr', 'ar']:
                    self.current_language = 'en'
                    
                #print(f"Settings loaded: language={self.current_language}")
            else:
                # Default settings if file doesn't exist
                self.current_language = 'en'
                self.current_discipline = 'mathematics'
                self.custom_discipline = ''
                self.db_path = 'exercises.db'
                # Save default settings
                self.save_settings()
                #print("Default settings created")
                
        except Exception as e:
            print(f"Error loading settings: {e}")
            # Fallback to defaults
            self.current_language = 'en'
            self.current_discipline = 'mathematics'
            self.custom_discipline = ''
            self.db_path = 'exercises.db'
        
            
    def save_settings(self):
        """Save application settings."""
        settings = {
            'language': self.current_language,
            'discipline': self.current_discipline,
            'custom_discipline': self.custom_discipline,
            'db_path': self.db_path
        }
        try:
            path = self._app_dir() / 'app_settings.json'
            with open(path, 'w') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            print(f"Failed to save settings: {e}")
        
     
    
    # ──────────────────────────────────────────────────────────────────────
    # EXPORT EXERCISES TO LaTeX
    # ──────────────────────────────────────────────────────────────────────

    def open_export_dialog(self):
        """Open the Export Exercises to LaTeX dialog."""
        dialog = ExportExercisesDialog(self, self.db)
        dialog.exec_()

    # ──────────────────────────────────────────────────────────────────────
    # PRINT / PDF
    # ──────────────────────────────────────────────────────────────────────

    def _print_to_printer(self):
        """Print the current exercise (+ solution if visible) to a printer."""
        if not self.current_exercise_id:
            return
        try:
            from PyQt5.QtPrintSupport import QPrinter, QPrintDialog
            printer = QPrinter(QPrinter.HighResolution)
            printer.setPageSize(QPrinter.A4)
            dialog = QPrintDialog(printer, self)
            dialog.setWindowTitle("Print Exercise")
            if dialog.exec_() != QPrintDialog.Accepted:
                return

            if self.solution_visible and self.has_solution:
                # Print exercise first; when done, print solution on next page(s)
                self._pending_printer = printer
                self.exercise_view.page().print_(
                    printer, self._print_solution_after
                )
            else:
                self.exercise_view.page().print_(printer, self._on_print_done)

        except ImportError:
            QMessageBox.warning(
                self, "Print Not Available",
                "PyQt5.QtPrintSupport is not installed.\n"
                "Install it with: pip install PyQt5"
            )
        except Exception as exc:
            QMessageBox.warning(self, "Print Error",
                                f"Could not print:\n{str(exc)}")

    def _print_solution_after(self, success):
        """Callback: after exercise is printed, print the solution page."""
        if success and hasattr(self, '_pending_printer'):
            self.solution_view.page().print_(
                self._pending_printer, self._on_print_done
            )

    def _on_print_done(self, success):
        if not success:
            QMessageBox.warning(self, "Print Error",
                                "The print job did not complete successfully.")

    def _save_as_pdf(self):
        """Save the current exercise (+ solution if visible) as PDF file(s)."""
        if not self.current_exercise_id:
            return
        try:
            # Build a default file name from the exercise name
            ex_name = (self.current_exercise_data[2]
                       if self.current_exercise_data else "exercise")
            safe = "".join(
                c if c.isalnum() or c in " _-" else "_" for c in ex_name
            ).replace(" ", "_")[:50]

            if self.solution_visible and self.has_solution:
                # Save exercise and solution as two separate PDFs
                path, _ = QFileDialog.getSaveFileName(
                    self, "Save Exercise as PDF",
                    safe + "_exercise.pdf",
                    "PDF files (*.pdf);;All files (*)"
                )
                if not path:
                    return
                base = path[:-4] if path.endswith(".pdf") else path
                ex_path  = base + "_exercise.pdf"
                sol_path = base + "_solution.pdf"
                self.exercise_view.page().printToPdf(ex_path)
                self.solution_view.page().printToPdf(sol_path)
                QMessageBox.information(
                    self, "PDF Saved",
                    f"Exercise saved as:\n{ex_path}\n\n"
                    f"Solution saved as:\n{sol_path}"
                )
            else:
                path, _ = QFileDialog.getSaveFileName(
                    self, "Save Exercise as PDF",
                    safe + ".pdf",
                    "PDF files (*.pdf);;All files (*)"
                )
                if not path:
                    return
                self.exercise_view.page().printToPdf(path)
                QMessageBox.information(self, "PDF Saved",
                                        f"Exercise saved as:\n{path}")

        except Exception as exc:
            QMessageBox.warning(self, "PDF Error",
                                f"Could not save PDF:\n{str(exc)}")

    def closeEvent(self, event):
        """Handle application close event."""
        self.db.close()
        event.accept()