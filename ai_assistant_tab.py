"""
ai_assistant_tab.py: AI Assistant tab for LaTeX Exercise Viewer.
"""
import re
import json
import base64
import os
import tempfile
import time
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton, QShortcut, QDialog,
    QLabel, QGroupBox, QSplitter, QMessageBox, QFileDialog, QApplication, QSizePolicy
)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings, QWebEnginePage
from PyQt5.QtCore import Qt, QTimer, QDateTime, QEvent
from PyQt5.QtGui import QFont, QKeySequence, QImage
from PyQt5.QtCore import QUrl
from online_ai_provider import OnlineAIProvider
from katex_loader import build_chat_html_with_katex 
# Add this import
from translations import translations

#ai_assistant_tab.py
class AIAssistantTab(QWidget):
    """AI Assistant tab with chat interface and LaTeX rendering."""
    def __init__(self, parent=None, ai_config=None, db=None):
        super().__init__(parent)
        self.main_window = parent
        self.ai_config = ai_config or {}
        self.db = db
        self.chat_history = []
        self.current_ai_exercise = None
        self.current_ai_metadata = None
        self.partial_solution = None
        self.last_image_data = None
        self.setup_ui()                
       
        # Configurer les settings
        settings = self.chat_display.settings()
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.ErrorPageEnabled, True)       
       
        # Message de bienvenue avec formule test adapté aux trois langues
        current_language = getattr(self, 'current_language', 'en')
        self.current_language = current_language                
    
        welcome_text = self.get_welcome_message(self.current_language)
        self.add_chat_message("AI", welcome_text)
        self.update_ai_status()

    def setup_ui(self):
        """Setup the AI Assistant tab UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)
        # Create horizontal splitter for side-by-side layout
        splitter = QSplitter(Qt.Horizontal)
        # Left side: Input and controls
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 5, 0)
        left_layout.setAlignment(Qt.AlignTop)
        # Input group
        input_group = QGroupBox(self.tr("your_question"))
        self.input_group = input_group
        input_group_layout = QVBoxLayout(input_group)
        self.chat_input = QTextEdit()
        self.chat_input.setMinimumHeight(150)
        self.chat_input.setPlaceholderText("Tapez votre question... (Ctrl+Enter pour envoyer, Ctrl+V pour coller une image)")
        self.chat_input.setAcceptDrops(True)
        self.chat_input.setStyleSheet("""
            QTextEdit {
                border: 2px solid #dee2e6;
                border-radius: 8px;
                padding: 12px;
                font-family: 'Segoe UI', Arial, sans-serif;
                font-size: 14px;
                background-color: white;
            }
            QTextEdit:focus {
                border: 2px solid #0078d4;
            }
        """)
        # Override drag & drop events
        self.chat_input.dragEnterEvent = self.dragEnterEvent
        self.chat_input.dropEvent = self.dropEvent
        # Install event filter for Ctrl+V and Ctrl+Enter
        self.chat_input.installEventFilter(self)
        # Keyboard shortcuts for sending message
        shortcut_ctrl_enter = QShortcut(QKeySequence("Ctrl+Enter"), self.chat_input)
        shortcut_ctrl_enter.activated.connect(self.send_chat_message)
        shortcut_ctrl_return = QShortcut(QKeySequence("Ctrl+Return"), self.chat_input)
        shortcut_ctrl_return.activated.connect(self.send_chat_message)
        input_group_layout.addWidget(self.chat_input)
        # Add image button
        image_btn_layout = QHBoxLayout()
        attach_image_btn = QPushButton("📎 Joindre Image")
        attach_image_btn.setObjectName("attach_image_btn")      
        attach_image_btn.clicked.connect(self.attach_image_to_chat)
        attach_image_btn.setStyleSheet("""
            QPushButton {
                background-color: #17a2b8;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #138496;
            }
        """)
        image_btn_layout.addWidget(attach_image_btn)
        image_btn_layout.addStretch()
        input_group_layout.addLayout(image_btn_layout)
        left_layout.addWidget(input_group)
        # Action buttons
        button_layout = QVBoxLayout()
        button_layout.setSpacing(10)
        # Send button (prominent)
        send_btn = QPushButton("📤 Send Message")
        self.send_btn = send_btn
        send_btn.setObjectName("send_message_btn")
        send_btn.clicked.connect(self.send_chat_message)
        send_btn.setMinimumHeight(45)
        send_btn.setToolTip(self.tr("send_message"))
        send_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px;
                font-size: 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
        """)
        button_layout.addWidget(send_btn)
        # Quick action buttons
        quick_actions_label = QLabel("Quick Actions:")
        quick_actions_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        quick_actions_label.setStyleSheet("color: #666; margin-top: 10px;")
        button_layout.addWidget(quick_actions_label)
        generate_exercise_btn = QPushButton(self.tr("generate_exercise"))        
        generate_exercise_btn.setObjectName("generate_exercise_btn")
        generate_exercise_btn.setToolTip(self.tr("ask_ai_to_generate_a_new_exercise"))
        self.generate_exercise_btn = generate_exercise_btn
        generate_exercise_btn.clicked.connect(self.generate_exercise)
        generate_exercise_btn.setMinimumHeight(40)
        generate_exercise_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        button_layout.addWidget(generate_exercise_btn)
        generate_solution_btn = QPushButton("🧠 Generate Solution")
        generate_solution_btn.setObjectName("generate_solution_btn")
        generate_solution_btn.setToolTip(self.tr("ask_ai_to_generate_the_solution"))
        self.generate_solution_btn = generate_solution_btn
        generate_solution_btn.clicked.connect(self.generate_solution)
        generate_solution_btn.setMinimumHeight(40)
        generate_solution_btn.setStyleSheet("""
            QPushButton {
                background-color: #17a2b8;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #138496;
            }
        """)
        button_layout.addWidget(generate_solution_btn)
        continue_solution_btn = QPushButton("➕ Continuer la Solution")
        continue_solution_btn.setObjectName("continue_solution_btn")
        continue_solution_btn.setToolTip(self.tr("solution_truncated"))
        self.continue_solution_btn = continue_solution_btn
        continue_solution_btn.clicked.connect(self.continue_solution)
        continue_solution_btn.setMinimumHeight(40)
        continue_solution_btn.setStyleSheet("""
            QPushButton {
                background-color: #fd7e14;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #e8590c;
            }
        """)
        button_layout.addWidget(continue_solution_btn)
        # Unified Save button
        save_label = QLabel("Detects and save the exercise and the solution to database:")  
        self.save_label = save_label
        save_label.setFont(QFont("Segoe UI", 10, QFont.Bold))
        save_label.setStyleSheet("color: #666; margin-top: 10px;")
        button_layout.addWidget(save_label)
        save_unified_btn = QPushButton("💾 Save")
        self.save_unified_btn = save_unified_btn
        #save_unified_btn.setObjectName("save_btn")
        save_unified_btn.setToolTip(self.tr("save_to_database"))
        
        save_unified_btn.clicked.connect(self.save_conversation_unified)
        save_unified_btn.setMinimumHeight(45)
        save_unified_btn.setStyleSheet("""
            QPushButton {
                background-color: #6f42c1;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5a32a3;
            }
        """)
        button_layout.addWidget(save_unified_btn)
        clear_chat_btn = QPushButton("🗑️ Clear Chat")
        clear_chat_btn.setObjectName("clear_chat_btn")
        clear_chat_btn.setToolTip(self.tr("clear_chat"))
        self.clear_chat_btn = clear_chat_btn
        clear_chat_btn.clicked.connect(self.clear_chat)
        clear_chat_btn.setMinimumHeight(40)
        clear_chat_btn.setStyleSheet("""
            QPushButton {{
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #c82333;
            }}
        """)
        button_layout.addWidget(clear_chat_btn)
        button_layout.addStretch()
        left_layout.addLayout(button_layout)
        splitter.addWidget(left_widget)
        # Right side: LaTeX-rendered conversation with title
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(5, 0, 0, 0)
        right_layout.setSpacing(10)
        
        
        # # # Title and status for the right side only
        # title_container = QHBoxLayout()
        # title_container.setContentsMargins(0, 0, 0, 0)
        # title_container.addStretch()        
        # # Title
        # title = QLabel("AI Assistant")
        # self.title_label = title
        # title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        # title.setFixedHeight(40)                    # This fixes the height
        # title.setAlignment(Qt.AlignVCenter)
        # title_container.addWidget(title)
        
        
        
        
        # # Status label
        # self.ai_status_label = QLabel("AI Assistant: Ready")
        # self.ai_status_label.setStyleSheet("""
            # color: #28a745; 
            # padding: 8px; 
            # font-size: 13px;
            # font-weight: bold;
            # background-color: #d4edda;
            # border-radius: 5px;
            # margin-left: 10px;
        # """)
        # title_container.addWidget(self.ai_status_label)
        # Title and status for the right side only
# Title and status for the right side only
        title_container = QHBoxLayout()
        title_container.setContentsMargins(0, 0, 0, 0)
        title_container.setSpacing(0)  # Reduced spacing between widgets
        title_container.addStretch()

        # Title
        title = QLabel("AI Assistant")
        self.title_label = title
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setFixedHeight(70)
        title.setAlignment(Qt.AlignVCenter)
        title_container.addWidget(title)

        # Status label 
        self.ai_status_label = QLabel("AI Assistant:")
        self.ai_status_label.setFont(QFont("Segoe UI", 10, QFont.Bold))  # Slightly smaller font
        self.ai_status_label.setFixedHeight(28)  # Fixed height for consistent appearance
        self.ai_status_label.setStyleSheet("""
            QLabel {
                color: #6c757d;                /* gray text */
                background-color: #e9ecef;     /* light gray background */
                padding: 4px 8px;
                font-size: 11px;
                font-weight: bold;
                border-radius: 5px;
                margin-left: 8px;
            }
        """)
        self.ai_status_label.setAlignment(Qt.AlignCenter)
        self.ai_status_label.setMinimumWidth(120)  # Ensure proper width

        title_container.addWidget(self.ai_status_label)
        title_container.addStretch()
        right_layout.addLayout(title_container)

#########        
        # Use QWebEngineView for LaTeX rendering
        self.chat_display = QWebEngineView()
        self.chat_display.setMinimumWidth(400)
        self.chat_display.setStyleSheet("""
            QWebEngineView {
                border: 2px solid #dee2e6;
                border-radius: 8px;
                background-color: white;
            }
        """)
        right_layout.addWidget(self.chat_display)
        splitter.addWidget(right_widget)
        # Set splitter proportions (30% left, 70% right)
        splitter.setSizes([300, 700])
        layout.addWidget(splitter)
        
    def get_welcome_message(self, language):
        messages = {
            'en': "Hello! I am your mathematics assistant.\n\nTest: $E=mc^2$ and $$\\int_0^\\infty e^{-x^2} dx = \\frac{\\sqrt{\\pi}}{2}$$",
            'fr': "Bonjour ! Je suis votre assistant en mathématiques.\n\nTest: $E=mc^2$ et $$\\int_0^\\infty e^{-x^2} dx = \\frac{\\sqrt{\\pi}}{2}$$",
            'ar': "مرحباً! أنا مساعدك في الرياضيات.\n\nاختبار: $E=mc^2$ و $$\\int_0^\\infty e^{-x^2} dx = \\frac{\\sqrt{\\pi}}{2}$$"
        }
        return messages.get(language, messages['en'])
    
    def update_ai_status(self):
        """Update AI status label."""
        if self.ai_config.get('mode') == 'offline':
            self.ai_status_label.setText(" Offline Mode")
            self.ai_status_label.setStyleSheet("""
                QLabel {
                    color: #6c757d;                /* gray text */
                    background-color: #e9ecef;     /* light gray background */
                    padding: 4px 8px;
                    font-size: 11px;
                    font-weight: bold;
                    border-radius: 5px;
                    margin-left: 8px;
                }
            """)
        else:
            provider = self.ai_config.get('provider', 'Unknown')
            self.ai_status_label.setText(f" Online ({provider})")
            self.ai_status_label.setStyleSheet("""
                QLabel {
                    color: #155724;                /* dark green text */
                    background-color: #d4edda;     /* light green background */
                    padding: 4px 8px;
                    font-size: 11px;
                    font-weight: bold;
                    border-radius: 5px;
                    margin-left: 8px;
                }
            """)


    def add_chat_message(self, sender, message):
        """Add a message to the chat display with LaTeX rendering."""
        timestamp = QDateTime.currentDateTime().toString("hh:mm:ss")
        
        # Store in history
        self.chat_history.append({
            'sender': sender,
            'message': message,
            'timestamp': timestamp
        })
        
        
        try:
            # Build HTML for all messages
            chat_html = build_chat_html_with_katex(self.chat_history)            
           
            # Render
            self.chat_display.setHtml(chat_html, QUrl("about:blank"))
                       
            # Scroll
            QTimer.singleShot(500, self.scroll_chat_to_bottom)
            
        except Exception as e:
            print(f"❌ Erreur: {e}")
            import traceback
            traceback.print_exc()
    

    def scroll_chat_to_bottom(self):
        """Safely scroll chat to bottom."""
        try:
            scroll_script = """
            (function() {{
                try {{
                    if (document.body) {{
                        window.scrollTo(0, document.body.scrollHeight);
                    }}
                }} catch(e) {{
                    console.log('Scroll error: ' + e);
                }}
            }})();
            """
            self.chat_display.page().runJavaScript(scroll_script)
        except Exception as e:
            print(f"Scroll error: {e}")
    
    
    def eventFilter(self, obj, event):
        """Handle paste events and keyboard shortcuts."""
        if obj == self.chat_input and event.type() == QEvent.KeyPress:
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
                # Ctrl+Enter pour envoyer le message
                elif (event.key() in (Qt.Key_Return, Qt.Key_Enter)) and (event.modifiers() & Qt.ControlModifier):
                    self.send_chat_message()
                    return True  # Event handled
                # Enter seul (sans Ctrl) - comportement normal
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
    # Image processing methods
    def is_image_file(self, file_path):
        """Check if file is an image based on extension."""
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp', '.tiff'}
        file_ext = os.path.splitext(file_path)[1].lower()
        return file_ext in image_extensions
    def attach_image_to_chat(self):
        """Open file dialog to attach an image."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Sélectionner une image",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp *.svg *.pdf);;All Files (*.*)"
        )
        if file_path:
            self.process_image_file(file_path)
    def process_image_file(self, file_path):
        """Process image file and send to AI without pre-analysis."""
        import os
        file_name = os.path.basename(file_path)
        file_ext = os.path.splitext(file_name)[1].lower()
        # Display image in chat
        self.add_chat_message("You", f"📷 Image jointe: {file_name}")
        # Check if online AI is configured
        if self.ai_config.get('mode') == 'offline':
            self.add_chat_message(
                "System",
                "❌ L'envoi d'images nécessite l'IA en ligne. Configurez dans Outils → Configuration IA."
            )
            return
        # Store image data for later use
        try:
            with open(file_path, 'rb') as img_file:
                image_data = img_file.read()
                base64_image = base64.b64encode(image_data).decode('utf-8')
            # Determine mime type
            mime_types = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.bmp': 'image/bmp',
                '.gif': 'image/gif',
                '.webp': 'image/webp'
            }
            mime_type = mime_types.get(file_ext, 'image/jpeg')
            # Store image data for the next AI query
            self.last_image_data = {
                'base64_image': base64_image,
                'mime_type': mime_type,
                'file_name': file_name
            }
            self.add_chat_message("System", "✅ Image prête à être envoyée. Tapez votre question maintenant.")
        except Exception as e:
            self.add_chat_message("System", f"❌ Erreur lecture image: {str(e)}")
    def process_pasted_image(self, image):
        """Process pasted image from clipboard and send to AI."""
        import tempfile
        # Save to temporary file
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, "pasted_image.png")
        image.save(temp_path, "PNG")
        # Display in chat
        self.add_chat_message("You", "📷 Image collée depuis le presse-papiers")
        # Process with AI
        self.process_image_file(temp_path)
    # Chat message handling
    def send_chat_message(self):
        """Send user message to AI, with image if available."""
        message = self.chat_input.toPlainText().strip()
        # Check if we have an image to send
        has_image = hasattr(self, 'last_image_data') and self.last_image_data
        if not message and not has_image:
            return
        if has_image:
            self.add_chat_message("You", f"📷 {self.last_image_data['file_name']}\n{message if message else 'Résous cet exercice'}")
        else:
            self.add_chat_message("You", message)
        self.chat_input.clear()
        # Process message with image if available
        if has_image:
            self.process_ai_message_with_image(message, self.last_image_data)
            # Clear the stored image after sending
            del self.last_image_data
        else:
            self.process_ai_message(message)
            
    def query_with_retry(self, provider, prompt, max_tokens, temperature, max_retries=3):
        """
        Effectue une requête avec retry automatique en cas d'erreurs.
        """
        for attempt in range(max_retries):
            try:
                response, error = provider.query(prompt, max_tokens, temperature)
                
                if not error:
                    return response, None
                
                # Si c'est une erreur de rate limit
                if "rate_limit" in error.lower() or "429" in error or "quota" in error.lower():
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 10  # 10s, 20s, 30s
                        current_language = getattr(self.main_window, 'current_language', 'en')
                        if current_language == 'ar':
                            self.add_chat_message("System", f"⏳ تم الوصول إلى الحد، إعادة المحاولة خلال {wait_time} ثانية...")
                        elif current_language == 'fr':
                            self.add_chat_message("System", f"⏳ Limite atteinte, nouvelle tentative dans {wait_time}s...")
                        else:
                            self.add_chat_message("System", f"⏳ Rate limit reached, retrying in {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                
                # Autre erreur ou dernier essai
                return None, error
                
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(5)  # Wait 5 seconds before retry
                    continue
                return None, f"Exception: {str(e)}"
        
        return None, "Échec après plusieurs tentatives"
    
    def process_ai_message(self, message):
        """Process user message and generate AI response based on content."""
        # Get current discipline and language
        discipline_name = self.get_discipline_name(getattr(self.main_window, 'current_discipline', 'mathematics'))
        current_language = getattr(self.main_window, 'current_language', 'en')
        
        # Determine response language based on settings
        if current_language == 'ar':
            response_language = "Arabic"
            language_instruction = "الرد باللغة العربية"
            generating_msg = "🔄 جاري إنشاء التمرين... يرجى الانتظار..."
        elif current_language == 'fr':
            response_language = "French"
            language_instruction = "Réponds en français"
            generating_msg = "🔄 Génération d'un exercice... veuillez patienter..."
        else:
            response_language = "English"
            language_instruction = "Respond in English"
            generating_msg = "🔄 Generating exercise... please wait..."

        if self.ai_config.get('mode') == 'offline':
            # Offline mode - simple responses
            if any(word in message.lower() for word in ["génère", "generate", "crée", "create", "exercice", "exercise"]):
                response = "Pour générer un exercice, je dois utiliser l'IA en ligne. Veuillez configurer l'IA dans Outils → Configuration IA."
            else:
                response = "Mode hors ligne activé. Pour une interaction complète, configurez l'IA en ligne dans Outils → Configuration IA."
            self.add_chat_message("AI", response)
            return
        
        # Online mode - process with AI
        try:
            # Initialize provider with better error handling
            provider = OnlineAIProvider()
            
            # Validate AI configuration before proceeding
            if not self.validate_ai_config():
                if current_language == 'ar':
                    self.add_chat_message("AI", "❌ خطأ: إعدادات الذكاء الاصطناعي غير صالحة. يرجى التحقق من الإعدادات.")
                elif current_language == 'fr':
                    self.add_chat_message("AI", "❌ Erreur: Configuration IA invalide. Veuillez vérifier les paramètres.")
                else:
                    self.add_chat_message("AI", "❌ Error: Invalid AI configuration. Please check settings.")
                return
            
            success = provider.set_provider(
                self.ai_config.get('provider'),
                self.ai_config.get('api_key'),
                self.ai_config.get('model')
            )
            
            if not success:
                if current_language == 'ar':
                    self.add_chat_message("AI", "❌ خطأ: تعذر تكوين مزود الذكاء الاصطناعي.")
                elif current_language == 'fr':
                    self.add_chat_message("AI", "❌ Erreur: Impossible de configurer le fournisseur IA.")
                else:
                    self.add_chat_message("AI", "❌ Error: Could not configure AI provider.")
                return
                
            # Check if user wants to generate an exercise
            is_exercise_request = any(word in message.lower() for word in [
                "génère", "generate", "crée", "create", "exercice", "exercise",                
                "problème", "problem", "question", "أنشئ", "إنشاء", "تمرين"
            ])
            
            if is_exercise_request:
                # Generate exercise based on user's topic request
                self.add_chat_message("System", generating_msg)
                QApplication.processEvents()
                
                # Build prompt based on language
                if current_language == 'ar':
                    prompt = f"""أنت أستاذ جامعي في {discipline_name}. يطلب منك طالب:
    "{message}"
    أنشئ تمريناً في {discipline_name} حسب هذا الطلب.

    لغة الرد: العربية
    {language_instruction}

    التنسيق المطلوب:
    العنوان: [عنوان قصير للتمرين]
    المستوى: [مبتدئ/متوسط/متقدم]
    الكلمات المفتاحية: [كلمة1, كلمة2, كلمة3]
    \\begin{{exercise}}
    [نص التمرين هنا مع الصيغ الرياضية بلاتيكس]
    \\end{{exercise}}

    هام:
    - مستوى جامعي
    - استخدم $ للرياضيات المضمنة، $$ أو \\[ \\] للرياضيات المنفصلة
    - لا تدرج \\documentclass، \\usepackage، \\begin{{document}}
    - دائماً ضع التمرين داخل \\begin{{exercise}}...\\end{{exercise}}

    مثال:
    العنوان: مشتقة دالة كثيرة الحدود
    المستوى: مبتدئ
    الكلمات المفتاحية: مشتقة, كثيرة الحدود, حساب
    \\begin{{exercise}}
    احسب مشتقة الدالة $f(x) = 3x^3 + 2x^2 - 5x + 7$.
    \\end{{exercise}}

    الآن أنشئ التمرين:"""
                elif current_language == 'fr':
                    prompt = f"""Tu es un professeur de {discipline_name} universitaire. Un étudiant te demande:
    "{message}"
    Génère un exercice de {discipline_name} selon cette demande.

    LANGUE DE RÉPONSE: Français
    {language_instruction}

    FORMAT OBLIGATOIRE:
    TITRE: [Un titre court pour l'exercice]
    NIVEAU: [Basique/Intermédiaire/Avancé]
    MOTS-CLÉS: [mot1, mot2, mot3]
    \\begin{{exercise}}
    [L'énoncé de l'exercice ici avec les formules LaTeX]
    \\end{{exercise}}

    IMPORTANT:
    - Niveau universitaire
    - Utilise $ pour inline, $$ ou \\[ \\] pour display
    - NE PAS inclure \\documentclass, \\usepackage, \\begin{{document}}
    - TOUJOURS encapsuler l'exercice dans \\begin{{exercise}}...\\end{{exercise}}

    Exemple:
    TITRE: Dérivée d'une fonction polynomiale
    NIVEAU: Basique
    MOTS-CLÉS: dérivée, polynôme, calcul
    \\begin{{exercise}}
    Calculer la dérivée de la fonction $f(x) = 3x^3 + 2x^2 - 5x + 7$.
    \\end{{exercise}}

    Maintenant génère l'exercice:"""
                else:
                    prompt = f"""You are a university {discipline_name} professor. A student asks:
    "{message}"
    Generate a {discipline_name} exercise according to this request.

    RESPONSE LANGUAGE: English
    {language_instruction}

    REQUIRED FORMAT:
    TITLE: [A short title for the exercise]
    LEVEL: [Basic/Intermediate/Advanced]
    KEYWORDS: [keyword1, keyword2, keyword3]
    \\begin{{exercise}}
    [The exercise statement here with LaTeX formulas]
    \\end{{exercise}}

    IMPORTANT:
    - University level
    - Use $ for inline math, $$ or \\[ \\] for display math
    - Do NOT include \\documentclass, \\usepackage, \\begin{{document}}
    - ALWAYS encapsulate the exercise in \\begin{{exercise}}...\\end{{exercise}}

    Example:
    TITLE: Derivative of a Polynomial Function
    LEVEL: Basic
    KEYWORDS: derivative, polynomial, calculus
    \\begin{{exercise}}
    Calculate the derivative of the function $f(x) = 3x^3 + 2x^2 - 5x + 7$.
    \\end{{exercise}}

    Now generate the exercise:"""
                
                # Use retry logic for the query
                response, error = self.query_with_retry(provider, prompt, max_tokens=800, temperature=0.8)
                
                if error:
                    if "no such group" in error.lower():
                        # This is a specific provider error, try to recover
                        if current_language == 'ar':
                            self.add_chat_message("AI", "❌ خطأ في الاتصال بمزود الذكاء الاصطناعي. يرجى المحاولة مرة أخرى.")
                        elif current_language == 'fr':
                            self.add_chat_message("AI", "❌ Erreur de connexion au fournisseur IA. Veuillez réessayer.")
                        else:
                            self.add_chat_message("AI", "❌ Connection error with AI provider. Please try again.")
                    else:
                        self.add_chat_message("AI", f"❌ {error}")
                    return
                
                # Clean response
                cleaned = self.clean_latex_response(response)
                
                # Parse the response to extract metadata
                metadata = self.parse_exercise_metadata(cleaned)
                # Store for later use
                self.current_ai_exercise = metadata['exercise']
                self.current_ai_metadata = metadata
                # Display the exercise
                self.add_chat_message("AI", metadata['exercise'])
                
            else:
                # General question - just answer
                if current_language == 'ar':
                    self.add_chat_message("System", "🔄 جاري التفكير...")
                elif current_language == 'fr':
                    self.add_chat_message("System", "🔄 Réflexion en cours...")
                else:
                    self.add_chat_message("System", "🔄 Thinking...")
                    
                QApplication.processEvents()
                
                if current_language == 'ar':
                    prompt = f"""أنت مساعد في {discipline_name} باللغة العربية. أجب على هذا السؤال:
        "{message}"
        أجب باللغة العربية بشكل واضح وموجز. استخدم LaTeX للصيغ الرياضية مع $ أو $$.
        أجب على السؤال فقط، دون إضافة مقدمات LaTeX."""
                elif current_language == 'fr':
                    prompt = f"""Tu es un assistant en {discipline_name} en français. Réponds à cette question:
        "{message}"
        Réponds en français de manière claire et concise. Utilise LaTeX pour les formules mathématiques avec $ ou $$.
        Ne réponds QUE à la question, sans ajouter de préambule LaTeX."""
                else:
                    prompt = f"""You are a {discipline_name} assistant in English. Answer this question:
        "{message}"
        Answer in English clearly and concisely. Use LaTeX for mathematical formulas with $ or $$.
        Answer ONLY the question, without adding LaTeX preamble."""
                
                response, error = self.query_with_retry(provider, prompt, max_tokens=600, temperature=0.7)
                if error:
                    self.add_chat_message("AI", f"❌ {error}")
                else:
                    cleaned = self.clean_latex_response(response)
                    self.add_chat_message("AI", cleaned)
                    
        except Exception as e:
            error_msg = str(e)
            if "no such group" in error_msg.lower():
                if current_language == 'ar':
                    self.add_chat_message("AI", "❌ خطأ في اتصال الذكاء الاصطناعي. يرجى التحقق من الإعدادات والمحاولة مرة أخرى.")
                elif current_language == 'fr':
                    self.add_chat_message("AI", "❌ Erreur de connexion IA. Veuillez vérifier les paramètres et réessayer.")
                else:
                    self.add_chat_message("AI", "❌ AI connection error. Please check settings and try again.")
            else:
                if current_language == 'ar':
                    self.add_chat_message("AI", f"❌ خطأ في الاتصال: {error_msg}")
                elif current_language == 'fr':
                    self.add_chat_message("AI", f"❌ Erreur de connexion: {error_msg}")
                else:
                    self.add_chat_message("AI", f"❌ Connection error: {error_msg}")
                    
    def validate_ai_config(self):
        """Validate AI configuration before making requests."""
        if self.ai_config.get('mode') == 'offline':
            return True
        
        provider = self.ai_config.get('provider')
        api_key = self.ai_config.get('api_key')
        model = self.ai_config.get('model')
        
        if not provider or not api_key:
            return False
        
        # Basic validation for different providers
        if provider == 'openai' and not api_key.startswith('sk-'):
            return False
        elif provider == 'anthropic' and not api_key.startswith('sk-'):
            return False
        elif provider == 'gemini' and len(api_key) < 10:  # Gemini keys are typically longer
            return False
        
        return True
    


    def update_language(self):
        """Update AI assistant tab language using object names."""
        # Get the current language from main window
        if hasattr(self, 'main_window') and hasattr(self.main_window, 'current_language'):
            self.current_language = self.main_window.current_language
        else:
            self.current_language = 'en'  # fallback
            
        if hasattr(self, 'main_window'):
            self.send_btn.setToolTip(self.tr("send_message"))
            self.generate_solution_btn.setToolTip(self.tr("ask_ai_to_generate_the_solution"))
            self.generate_exercise_btn.setToolTip(self.tr("ask_ai_to_generate_a_new_exercise"))  
            self.continue_solution_btn.setToolTip(self.tr("solution_truncated"))               
            self.save_unified_btn.setToolTip(self.tr("save_to_database"))  
            self.save_unified_btn.setText(self.tr("save_btn"))
            self.save_label.setText(self.tr("save_to_database"))
            self.clear_chat_btn.setToolTip(self.tr("clear_chat"))           
            
        else:
            self.send_btn.setToolTip("Send message (Ctrl+Enter)")  
            self.generate_solution_btn.setToolTip("Ask AI to generate solution for current exercise")
            self.generate_exercise_btn.setToolTip("Ask AI to generate a new exercise")     
            self.continue_solution_btn.setToolTip("⚠️ Solution appears truncated. Use the '➕ Continue Solution' button to complete it.")
            self.continue_solution_btn.setToolTip("Detects and saves exercise and/or solution to database") 
            self.save_unified_btn.setToolTip("Detects and save the exercise and the solution to database:")  
            self.clear_chat_btn.setToolTip("Clear chat history")
            self.save_label.setText("Detects and save the exercise and the solution to database:")
            self.save_unified_btn.setText("💾 Save")
            
        
        # Update UI elements first
        if hasattr(self, 'input_group'):
            translated_title = self.tr("your_question")
            self.input_group.setTitle(translated_title)
        
        if hasattr(self, 'chat_input'):
            self.chat_input.setPlaceholderText(self.tr("type_your_question"))
        
        if hasattr(self, 'title_label'):
            translated_title = self.tr("ai_math_assistant")
            self.title_label.setText(translated_title)
            
        if hasattr(self, 'input_group'):
            translated_title = self.tr("your_question")
            self.input_group.setTitle(translated_title)
            
        # Update status label
        if hasattr(self, 'ai_status_label'):
            current_text = self.ai_status_label.text()
            status_parts = current_text.split(": ")
            if len(status_parts) > 1:
                status_type = status_parts[0]
                status_value = status_parts[1]
                translated_status = f"{self.tr('ai_math_assistant')}: {status_value}"
                self.ai_status_label.setText(translated_status)
        
        # Update button texts using object names
        button_translations = {
            "send_message_btn": "send_message",
            "generate_exercise_btn": "generate_exercise", 
            "generate_solution_btn": "generate_solution",
            "continue_solution_btn": "continue_solution",
            "save_btn": "save",
            "clear_chat_btn": "clear_chat",
            "attach_image_btn": "attach_image"
        }
        
        for obj_name, translation_key in button_translations.items():
            button = self.findChild(QPushButton, obj_name)
            if button:
                translated_text = self.tr(translation_key)
                button.setText(translated_text)
        
        # Update labels using object names
        label_translations = {
            "quick_actions_label": "quick_actions",
            "save_label": "save_to_database", 
        }
        
        for obj_name, translation_key in label_translations.items():
            label = self.findChild(QLabel, obj_name)
            if label:
                translated_text = self.tr(translation_key)
                label.setText(translated_text)
        
        # Fallback for labels without object names
        for child in self.findChildren(QLabel):
            if not child.objectName():
                text = child.text()
                if "Quick Actions" in text or "Actions rapides" in text or "إجراءات سريعة" in text:
                    child.setText(self.tr("quick_actions"))
                elif "Save to Database" in text or "Enregistrer" in text or "حفظ في قاعدة البيانات" in text:
                    child.setText(self.tr("save_to_database"))
        
        # Update the welcome message in chat history without adding a new one
        self.update_welcome_message()
    
                
    def tr(self, text):
        """Get translation for text."""
        try:
            # Always get the current language from main window
            if hasattr(self, 'main_window') and hasattr(self.main_window, 'current_language'):
                current_language = self.main_window.current_language
            else:
                current_language = getattr(self, 'current_language', 'en')
            
            # Fallback direct translation lookup
            trans = translations.get(current_language, translations.get('en', {}))
            return trans.get(text, text)
        except (NameError, KeyError):
            # Return original text if translations aren't available
            return text
        
    def update_welcome_message(self):
        """Update the welcome message in chat history when language changes."""
        # Ensure we have the current language
        if hasattr(self, 'main_window') and hasattr(self.main_window, 'current_language'):
            current_lang = self.main_window.current_language
        else:
            current_lang = getattr(self, 'current_language', 'en')
        
        welcome_text = self.get_welcome_message(current_lang)
        
        # Find and replace the first AI message (which should be the welcome message)
        if self.chat_history and len(self.chat_history) > 0:
            # Look for the first AI message that contains welcome/test content
            for i, msg in enumerate(self.chat_history):
                if msg['sender'] == 'AI' and any(keyword in msg['message'].lower() for keyword in ['hello', 'bonjour', 'مرحباً', 'test:', 'test', 'e=mc']):
                    # Update the existing welcome message
                    self.chat_history[i]['message'] = welcome_text
                    break
            else:
                # If no suitable AI message found, replace the first AI message
                for i, msg in enumerate(self.chat_history):
                    if msg['sender'] == 'AI':
                        self.chat_history[i]['message'] = welcome_text
                        break
                else:
                    # If no AI messages at all, add the welcome message
                    self.chat_history.insert(0, {
                        'sender': 'AI',
                        'message': welcome_text,
                        'timestamp': QDateTime.currentDateTime().toString("hh:mm:ss")
                    })
        else:
            # If chat history is empty, add the welcome message
            self.chat_history.append({
                'sender': 'AI',
                'message': welcome_text,
                'timestamp': QDateTime.currentDateTime().toString("hh:mm:ss")
            })
        
        # Refresh the chat display
        try:
            chat_html = build_chat_html_with_katex(self.chat_history)
            self.chat_display.setHtml(chat_html, QUrl("about:blank"))
            QTimer.singleShot(500, self.scroll_chat_to_bottom)
        except Exception as e:
            print(f"Error updating chat display: {e}")
        
        
    def get_discipline_prompt(self):
        """Get the current discipline for AI prompts."""
        if hasattr(self, 'main_window'):
            discipline = self.main_window.current_discipline
            discipline_name = self.main_window.tr(discipline)
            return discipline_name
        return "Mathematics"
    






    
    def analyze_image_with_openai(self, image_data, prompt):
        """Analyze image with OpenAI GPT-4 Vision."""
        import requests
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.ai_config.get('api_key')}"
        }
        payload = {
            "model": "gpt-4o",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{image_data['mime_type']};base64,{image_data['base64_image']}"
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 3000,
            "temperature": 0.5
        }
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            if response.status_code == 200:
                result = response.json()
                return result['choices'][0]['message']['content']
            else:
                error_msg = response.json().get('error', {}).get('message', 'Erreur inconnue')
                return f"❌ Erreur OpenAI: {error_msg}"
        except Exception as e:
            return f"❌ Erreur connexion: {str(e)}"
    def analyze_image_with_claude(self, image_data, prompt):
        """Analyze image with Claude 3.5 Vision."""
        import requests
        url = "https://api.anthropic.com/v1/messages"
        headers = {
            "x-api-key": self.ai_config.get('api_key'),
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        payload = {
            "model": "claude-3-5-sonnet-20241022",
            "max_tokens": 3000,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": image_data['mime_type'],
                                "data": image_data['base64_image']
                            }
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ]
                }
            ]
        }
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=60)
            if response.status_code == 200:
                result = response.json()
                return result['content'][0]['text']
            else:
                error_msg = response.json().get('error', {}).get('message', 'Erreur inconnue')
                return f"❌ Erreur Claude: {error_msg}"
        except Exception as e:
            return f"❌ Erreur connexion: {str(e)}"
    def analyze_image_with_gemini(self, image_data, prompt):
        """Analyze image with Gemini Vision."""
        import requests
        model = "gemini-1.5-flash"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.ai_config.get('api_key')}"
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": prompt
                        },
                        {
                            "inline_data": {
                                "mime_type": image_data['mime_type'],
                                "data": image_data['base64_image']
                            }
                        }
                    ]
                }
            ],
            "generationConfig": {
                "maxOutputTokens": 3000,
                "temperature": 0.5
            }
        }
        try:
            response = requests.post(url, json=payload, timeout=60)
            if response.status_code == 200:
                result = response.json()
                return result['candidates'][0]['content']['parts'][0]['text']
            else:
                error_msg = response.json().get('error', {}).get('message', 'Erreur inconnue')
                return f"❌ Erreur Gemini: {error_msg}"
        except Exception as e:
            return f"❌ Erreur connexion: {str(e)}"
    
    def generate_exercise(self):
        """Generate an exercise using AI with language and discipline adaptation."""
        # Get current language and discipline
        current_language = getattr(self.main_window, 'current_language', 'en')
        discipline = getattr(self.main_window, 'current_discipline', 'mathematics')
        discipline_name = self.get_discipline_name(discipline)
        
        if self.ai_config.get('mode') == 'offline':
            exercise = self.generate_offline_exercise()
            self.current_ai_exercise = exercise
            
            # Set metadata based on language
            if current_language == 'fr':
                self.current_ai_metadata = {
                    'title': 'Exercice hors ligne',
                    'level': 'Intermédiaire',
                    'keywords': [discipline_name.lower()],
                    'exercise': exercise
                }
                self.add_chat_message("AI", f"Exercice généré (mode hors ligne):\n\n{exercise}")
            elif current_language == 'ar':
                self.current_ai_metadata = {
                    'title': 'تمرين بدون اتصال',
                    'level': 'متوسط',
                    'keywords': [discipline_name],
                    'exercise': exercise
                }
                arabic_message = "تم إنشاء التمرين (وضع عدم الاتصال):\n\n{}".format(exercise)
                self.add_chat_message("AI", arabic_message)
            else:
                self.current_ai_metadata = {
                    'title': 'Offline Exercise',
                    'level': 'Intermediate',
                    'keywords': [discipline_name.lower()],
                    'exercise': exercise
                }
                self.add_chat_message("AI", f"Exercise generated (offline mode):\n\n{exercise}")
        else:
            if not self.ai_config.get('api_key') and self.ai_config.get('provider') != 'huggingface':
                # Show warning in current language
                if current_language == 'fr':
                    QMessageBox.warning(
                        self, 
                        "Clé API manquante", 
                        "Veuillez configurer votre clé API dans Outils → Configuration IA"
                    )
                elif current_language == 'ar':
                    QMessageBox.warning(
                        self,
                        "مفتاح API مفقود",
                        "يرجى تكوين مفتاح API الخاص بك في أدوات → تكوين الذكاء الاصطناعي"
                    )
                else:
                    QMessageBox.warning(
                        self, 
                        "Missing API Key", 
                        "Please configure your API key in Tools → AI Configuration"
                    )
                return
            
            # Generate user message based on language and discipline
            if current_language == 'fr':
                user_message = f"Génère un exercice de {discipline_name} universitaire intéressant"
            elif current_language == 'ar':
                user_message = f"أنشئ تمريناً في {discipline_name} على المستوى الجامعي يكون مثيراً للاهتمام"
            else:
                user_message = f"Generate an interesting university-level {discipline_name} exercise"
            
            # Add the message and process it
            self.add_chat_message("You", user_message)
            self.process_ai_message(user_message)
        
    def get_discipline_name(self, discipline_key):
        """Get the translated discipline name."""
        current_language = getattr(self.main_window, 'current_language', 'en')
        
        try:
            # Get translations for current language, fallback to English
            trans = translations.get(current_language, translations.get('en', {}))
        except (NameError, KeyError):
            # Fallback if translations aren't available
            trans = {}
        
        # Map discipline keys to translation keys
        discipline_map = {
            'mathematics': 'mathematics',
            'physics': 'physics',
            'chemistry': 'chemistry',
            'biology': 'biology',
            'economics': 'economics',
            'computer_science': 'computer_science',
            'engineering': 'engineering',
            'statistics': 'statistics',
            'data_science': 'data_science',
            'finance': 'finance',
            'architecture': 'architecture',
            'medicine': 'medicine',
            'astronomy': 'astronomy',
            'geography': 'geography',
            'environmental_science': 'environmental_science',
            'psychology': 'psychology',
            'sociology': 'sociology',
            'linguistics': 'linguistics',
            'cryptography': 'cryptography',
            'artificial_intelligence': 'artificial_intelligence',
            'robotics': 'robotics'
        }
        
        # If it's a custom discipline, return it as is
        if discipline_key not in discipline_map:
            return discipline_key
        
        # Get the translated name with fallback
        translation_key = discipline_map[discipline_key]
        return trans.get(translation_key, discipline_key)
    
    def generate_offline_exercise(self):
        """Generate exercise using offline rule-based system with discipline adaptation."""
        import random
        current_language = getattr(self.main_window, 'current_language', 'en')
        discipline = getattr(self.main_window, 'current_discipline', 'mathematics')
        
        # Discipline-specific exercises in different languages
        exercises_by_discipline = {
            'mathematics': {
                'en': [
                    "Find the derivative of $f(x) = x^3 + 2x^2 - 5x + 1$.",
                    "Solve the equation: $x^2 - 4x + 4 = 0$.",
                    "Calculate the integral: $\\int (3x^2 + 2x - 1) dx$.",
                    "Find the limit: $\\lim_{x \\to 0} \\frac{\\sin(x)}{x}$.",
                    "Solve the system: $\\begin{cases} 2x + 3y = 7 \\\\ x - y = 1 \\end{cases}$"
                ],
                'fr': [
                    "Trouvez la dérivée de $f(x) = x^3 + 2x^2 - 5x + 1$.",
                    "Résolvez l'équation : $x^2 - 4x + 4 = 0$.",
                    "Calculez l'intégrale : $\\int (3x^2 + 2x - 1) dx$.",
                    "Trouvez la limite : $\\lim_{x \\to 0} \\frac{\\sin(x)}{x}$.",
                    "Résolvez le système : $\\begin{cases} 2x + 3y = 7 \\\\ x - y = 1 \\end{cases}$"
                ],
                'ar': [
                    "أوجد مشتقة الدالة $f(x) = x^3 + 2x^2 - 5x + 1$.",
                    "حل المعادلة: $x^2 - 4x + 4 = 0$.",
                    "احسب التكامل: $\\int (3x^2 + 2x - 1) dx$.",
                    "أوجد النهاية: $\\lim_{x \\to 0} \\frac{\\sin(x)}{x}$.",
                    "حل النظام: $\\begin{cases} 2x + 3y = 7 \\\\ x - y = 1 \\end{cases}$"
                ]
            },
            'physics': {
                'en': [
                    "Calculate the work done by a force of 10N moving an object 5m.",
                    "A car accelerates from 0 to 60 km/h in 10 seconds. What is its acceleration?",
                    "Calculate the kinetic energy of a 2kg object moving at 5m/s."
                ],
                'fr': [
                    "Calculez le travail effectué par une force de 10N déplaçant un objet de 5m.",
                    "Une voiture accélère de 0 à 60 km/h en 10 secondes. Quelle est son accélération?",
                    "Calculez l'énergie cinétique d'un objet de 2kg se déplaçant à 5m/s."
                ],
                'ar': [
                    "احسب الشغل المبذول بقوة 10 نيوتن تتحرك جسمًا مسافة 5 أمتار.",
                    "تسرع سيارة من 0 إلى 60 كم/ساعة في 10 ثوانٍ. ما هو تسارعها؟",
                    "احسب الطاقة الحركية لجسم كتلته 2 كجم يتحرك بسرعة 5 م/ث."
                ]
            },
            'chemistry': {
                'en': [
                    "Balance the chemical equation: H₂ + O₂ → H₂O",
                    "Calculate the molar mass of H₂SO₄.",
                    "What is the pH of a 0.01M HCl solution?"
                ],
                'fr': [
                    "Équilibrez l'équation chimique : H₂ + O₂ → H₂O",
                    "Calculez la masse molaire de H₂SO₄.",
                    "Quel est le pH d'une solution de HCl 0.01M?"
                ],
                'ar': [
                    "وازن المعادلة الكيميائية: H₂ + O₂ → H₂O",
                    "احسب الكتلة المولية لـ H₂SO₄.",
                    "ما هو الرقم الهيدروجيني لمحلول HCl بتركيز 0.01 مولاري؟"
                ]
            }
        }
        
        # Get exercises for the current discipline and language, fallback to mathematics
        discipline_exercises = exercises_by_discipline.get(discipline, exercises_by_discipline['mathematics'])
        exercises = discipline_exercises.get(current_language, discipline_exercises['en'])
        
        return random.choice(exercises)
    
    def generate_solution(self):
        """Generate solution with increased token limit, adapted to language."""
        current_language = getattr(self.main_window, 'current_language', 'en')
        
        if not self.current_ai_exercise:
            if current_language == 'fr':
                self.add_chat_message("AI", "⚠️ Veuillez d'abord générer un exercice!")
            elif current_language == 'ar':
                self.add_chat_message("AI", "⚠️ يرجى إنشاء تمرين أولاً!")
            else:
                self.add_chat_message("AI", "⚠️ Please generate an exercise first!")
            return
            
        if self.ai_config.get('mode') == 'offline':
            solution = self.generate_offline_solution()
            if current_language == 'fr':
                self.add_chat_message("AI", f"Solution (mode hors ligne):\n\n{solution}")
            elif current_language == 'ar':
                self.add_chat_message("AI", f"الحل (وضع عدم الاتصال):\n\n{solution}")
            else:
                self.add_chat_message("AI", f"Solution (offline mode):\n\n{solution}")
            return
            
        if not self.ai_config.get('api_key') and self.ai_config.get('provider') != 'huggingface':
            warning_title = self.tr("missing_api_key")
            warning_text = self.tr("configure_api_key")
            QMessageBox.warning(self, warning_title, warning_text)
            return
            
        try:
            provider = OnlineAIProvider()
            success = provider.set_provider(
                self.ai_config.get('provider'),
                self.ai_config.get('api_key'),
                self.ai_config.get('model')
            )
            if not success:
                if current_language == 'fr':
                    self.add_chat_message("AI", "Erreur: Configuration IA invalide.")
                elif current_language == 'ar':
                    self.add_chat_message("AI", "خطأ: تكوين الذكاء الاصطناعي غير صالح.")
                else:
                    self.add_chat_message("AI", "Error: Invalid AI configuration.")
                return
                
            # Show generating message in current language
            if current_language == 'fr':
                self.add_chat_message("System", "🔄 Génération de la solution... veuillez patienter...")
            elif current_language == 'ar':
                self.add_chat_message("System", "🔄 جاري إنشاء الحل... يرجى الانتظار...")
            else:
                self.add_chat_message("System", "🔄 Generating solution... please wait...")
                
            self.scroll_chat_to_bottom()
            QTimer.singleShot(1000, self._generate_solution_step2)
        except Exception as e:
            if current_language == 'fr':
                self.add_chat_message("AI", f"❌ Erreur: {str(e)}")
            elif current_language == 'ar':
                self.add_chat_message("AI", f"❌ خطأ: {str(e)}")
            else:
                self.add_chat_message("AI", f"❌ Error: {str(e)}")

    def _generate_solution_step2(self):
        """Actual solution generation logic, called after UI update."""
        current_language = getattr(self.main_window, 'current_language', 'en')
        
        if not self.current_ai_exercise:
            if current_language == 'fr':
                self.add_chat_message("AI", "⚠️ Veuillez d'abord générer un exercice!")
            elif current_language == 'ar':
                self.add_chat_message("AI", "⚠️ يرجى إنشاء تمرين أولاً!")
            else:
                self.add_chat_message("AI", "⚠️ Please generate an exercise first!")
            return

        if self.ai_config.get('mode') == 'offline':
            solution = self.generate_offline_solution()
            if current_language == 'fr':
                self.add_chat_message("AI", f"Solution (mode hors ligne):\n{solution}")
            elif current_language == 'ar':
                self.add_chat_message("AI", f"الحل (وضع عدم الاتصال):\n{solution}")
            else:
                self.add_chat_message("AI", f"Solution (offline mode):\n{solution}")
            return

        if not self.ai_config.get('api_key') and self.ai_config.get('provider') != 'huggingface':
            warning_title = self.tr("missing_api_key")
            warning_text = self.tr("configure_api_key")
            QMessageBox.warning(self, warning_title, warning_text)
            return

        try:
            provider = OnlineAIProvider()
            success = provider.set_provider(
                self.ai_config.get('provider'),
                self.ai_config.get('api_key'),
                self.ai_config.get('model')
            )
            if not success:
                if current_language == 'fr':
                    self.add_chat_message("AI", "Erreur: Configuration IA invalide.")
                elif current_language == 'ar':
                    self.add_chat_message("AI", "خطأ: تكوين الذكاء الاصطناعي غير صالح.")
                else:
                    self.add_chat_message("AI", "Error: Invalid AI configuration.")
                return

            # Build prompt based on language
            if current_language == 'fr':
                prompt = f"""Fournis une solution détaillée étape par étape en français pour cet exercice:
    EXERCICE:
    {self.current_ai_exercise}
    FORMAT OBLIGATOIRE:
    \\begin{{solution}}
    [Solution détaillée avec étapes]
    \\end{{solution}}
    IMPORTANT:
    - Solution COMPLÈTE et DÉTAILLÉE
    - Chaque étape bien expliquée
    - Formules mathématiques avec LaTeX
    - Si la solution est longue, inclus TOUT jusqu'à \\end{{solution}}
    - N'abrège RIEN, écris la solution entière
    Maintenant fournis la solution complète:"""
            elif current_language == 'ar':
                prompt = f"""قدم حلاً مفصلاً خطوة بخطوة باللغة العربية لهذا التمرين:
    التمرين:
    {self.current_ai_exercise}
    التنسيق المطلوب:
    \\begin{{solution}}
    [حل مفصل مع الخطوات]
    \\end{{solution}}
    هام:
    - حل كامل ومفصل
    - اشرح كل خطوة بوضوح
    - استخدم LaTeX للصيغ الرياضية
    - إذا كان الحل طويلاً، ضع كل شيء حتى \\end{{solution}}
    - لا تختصر شيئاً، اكتب الحل الكامل
    الآن قدم الحل الكامل:"""
            else:
                prompt = f"""Provide a detailed step-by-step solution in English for this exercise:
    EXERCISE:
    {self.current_ai_exercise}
    REQUIRED FORMAT:
    \\begin{{solution}}
    [Detailed solution with steps]
    \\end{{solution}}
    IMPORTANT:
    - COMPLETE and DETAILED solution
    - Each step well explained
    - Mathematical formulas with LaTeX
    - If the solution is long, include EVERYTHING until \\end{{solution}}
    - Do NOT abbreviate anything, write the entire solution
    Now provide the complete solution:"""

            response, error = provider.query(prompt, max_tokens=3000, temperature=0.7)
            if error:
                if current_language == 'fr':
                    self.add_chat_message("AI", f"❌ Erreur: {error}")
                elif current_language == 'ar':
                    self.add_chat_message("AI", f"❌ خطأ: {error}")
                else:
                    self.add_chat_message("AI", f"❌ Error: {error}")
            else:
                cleaned = self.clean_latex_response(response)
                if '\\begin{solution}' in cleaned and '\\end{solution}' not in cleaned:
                    self.add_chat_message("AI", cleaned)
                    # Show truncation warning in current language
                    if current_language == 'fr':
                        self.add_chat_message(
                            "System",
                            "⚠️ La solution semble tronquée. Utilisez le bouton '➕ Continuer la Solution' pour la compléter."
                        )
                    elif current_language == 'ar':
                        self.add_chat_message(
                            "System",
                            "⚠️ يبدو أن الحل مبتور. استخدم زر '➕ متابعة الحل' لإكماله."
                        )
                    else:
                        self.add_chat_message(
                            "System",
                            "⚠️ Solution appears truncated. Use the '➕ Continue Solution' button to complete it."
                        )
                    self.partial_solution = cleaned
                else:
                    self.add_chat_message("AI", cleaned)
                    self.partial_solution = None
        except Exception as e:
            if current_language == 'fr':
                self.add_chat_message("AI", f"❌ Erreur: {str(e)}")
            elif current_language == 'ar':
                self.add_chat_message("AI", f"❌ خطأ: {str(e)}")
            else:
                self.add_chat_message("AI", f"❌ Error: {str(e)}")

    def continue_solution(self):
        """Continue generating solution from where it was cut off, adapted to language."""
        current_language = getattr(self.main_window, 'current_language', 'en')
        
        if not hasattr(self, 'partial_solution') or not self.partial_solution:
            if current_language == 'fr':
                QMessageBox.information(
                    self,
                    "Aucune solution à continuer",
                    "Générez d'abord une solution avec le bouton '🧠 Generate Solution'."
                )
            elif current_language == 'ar':
                QMessageBox.information(
                    self,
                    "لا يوجد حل للمتابعة",
                    "قم بإنشاء حل أولاً باستخدام زر '🧠 إنشاء الحل'."
                )
            else:
                QMessageBox.information(
                    self,
                    "No Solution to Continue",
                    "Please generate a solution first using the '🧠 Generate Solution' button."
                )
            return
            
        try:
            provider = OnlineAIProvider()
            success = provider.set_provider(
                self.ai_config.get('provider'),
                self.ai_config.get('api_key'),
                self.ai_config.get('model')
            )
            if not success:
                if current_language == 'fr':
                    self.add_chat_message("AI", "Erreur: Configuration IA invalide.")
                elif current_language == 'ar':
                    self.add_chat_message("AI", "خطأ: تكوين الذكاء الاصطناعي غير صالح.")
                else:
                    self.add_chat_message("AI", "Error: Invalid AI configuration.")
                return
                
            # Show continuation message in current language
            if current_language == 'fr':
                self.add_chat_message("System", "🔄 Continuation de la solution...")
            elif current_language == 'ar':
                self.add_chat_message("System", "🔄 متابعة الحل...")
            else:
                self.add_chat_message("System", "🔄 Continuing solution...")
                
            QApplication.processEvents()
            
            # Build prompt based on language
            if current_language == 'fr':
                prompt = f"""Continue cette solution à partir d'où elle s'est arrêtée. 
    SOLUTION PARTIELLE ACTUELLE:
    {self.partial_solution}
    Continue directement là où ça s'est arrêté et termine avec \\end{{solution}}.
    N'ajoute PAS de nouveau \\begin{{solution}}, continue juste le contenu.
    Continue maintenant:"""
            elif current_language == 'ar':
                prompt = f"""تابع هذا الحل من حيث توقف.
    الحل الجزئي الحالي:
    {self.partial_solution}
    تابع مباشرة من حيث توقف وأنهِ بـ \\end{{solution}}.
    لا تضيف \\begin{{solution}} جديداً، فقط أكمل المحتوى.
    تابع الآن:"""
            else:
                prompt = f"""Continue this solution from where it stopped.
    CURRENT PARTIAL SOLUTION:
    {self.partial_solution}
    Continue directly from where it stopped and end with \\end{{solution}}.
    Do NOT add a new \\begin{{solution}}, just continue the content.
    Continue now:"""

            response, error = provider.query(prompt, max_tokens=3000, temperature=0.7)
            if error:
                if current_language == 'fr':
                    self.add_chat_message("AI", f"❌ Erreur: {error}")
                elif current_language == 'ar':
                    self.add_chat_message("AI", f"❌ خطأ: {error}")
                else:
                    self.add_chat_message("AI", f"❌ Error: {error}")
            else:
                cleaned = self.clean_latex_response(response)
                # Append to partial solution
                self.partial_solution += "\n\n" + cleaned
                
                # Show continuation header in current language
                if current_language == 'fr':
                    self.add_chat_message("AI", f"**[Suite]**\n\n{cleaned}")
                elif current_language == 'ar':
                    self.add_chat_message("AI", f"**[متابعة]**\n\n{cleaned}")
                else:
                    self.add_chat_message("AI", f"**[Continued]**\n\n{cleaned}")
                    
                # Check if now complete
                if '\\end{solution}' in self.partial_solution:
                    if current_language == 'fr':
                        self.add_chat_message("System", "✅ Solution complète!")
                    elif current_language == 'ar':
                        self.add_chat_message("System", "✅ الحل مكتمل!")
                    else:
                        self.add_chat_message("System", "✅ Solution complete!")
                    self.partial_solution = None
                else:
                    if current_language == 'fr':
                        self.add_chat_message(
                            "System",
                            "⚠️ Solution encore incomplète. Cliquez à nouveau sur 'Continuer' si nécessaire."
                        )
                    elif current_language == 'ar':
                        self.add_chat_message(
                            "System",
                            "⚠️ الحل لا يزال غير مكتمل. انقر مرة أخرى على 'متابعة' إذا لزم الأمر."
                        )
                    else:
                        self.add_chat_message(
                            "System",
                            "⚠️ Solution still incomplete. Click 'Continue' again if needed."
                        )
        except Exception as e:
            if current_language == 'fr':
                self.add_chat_message("AI", f"❌ Erreur: {str(e)}")
            elif current_language == 'ar':
                self.add_chat_message("AI", f"❌ خطأ: {str(e)}")
            else:
                self.add_chat_message("AI", f"❌ Error: {str(e)}")

    def generate_offline_solution(self):
        """Generate solution using offline rule-based system with language adaptation."""
        current_language = getattr(self.main_window, 'current_language', 'en')
        
        if current_language == 'fr':
            return "Ceci est une solution de démonstration. En mode en ligne, l'IA générerait la solution réelle."
        elif current_language == 'ar':
            return "هذا حل تجريبي. في الوضع المتصل، سيقوم الذكاء الاصطناعي بإنشاء الحل الفعلي."
        else:
            return "This is a placeholder solution. In online mode, AI would generate the actual solution."
        
    # Utility methods
    def parse_exercise_metadata(self, text):
        """
        Parse exercise metadata from AI response.
        Expected format:
        TITRE: ...
        NIVEAU: ...
        MOTS-CLÉS: ...
        ÉNONCÉ:
        ...
        """
        import re
        metadata = {
            'title': 'AI Generated Exercise',
            'level': 'Intermediate',
            'keywords': [],
            'exercise': text
        }
        
        # Try to extract title
        title_match = re.search(r'TITRE\s*:\s*(.+?)(?:\n|$)', text, re.IGNORECASE)
        if not title_match:
            title_match = re.search(r'TITLE\s*:\s*(.+?)(?:\n|$)', text, re.IGNORECASE)
        if not title_match:
            title_match = re.search(r'العنوان\s*:\s*(.+?)(?:\n|$)', text)
        
        if title_match:
            metadata['title'] = title_match.group(1).strip()
        
        # Try to extract level
        level_match = re.search(r'NIVEAU\s*:\s*(.+?)(?:\n|$)', text, re.IGNORECASE)
        if not level_match:
            level_match = re.search(r'LEVEL\s*:\s*(.+?)(?:\n|$)', text, re.IGNORECASE)
        if not level_match:
            level_match = re.search(r'المستوى\s*:\s*(.+?)(?:\n|$)', text)
        
        if level_match:
            level = level_match.group(1).strip()
            # Normalize level names
            if any(word in level.lower() for word in ['basic', 'basique', 'débutant', 'facile', 'مبتدئ']):
                metadata['level'] = 'Basic'
            elif any(word in level.lower() for word in ['inter', 'moyen', 'intermediate', 'intermédiaire', 'متوسط']):
                metadata['level'] = 'Intermediate'
            elif any(word in level.lower() for word in ['adv', 'avancé', 'difficile', 'expert', 'advanced', 'متقدم']):
                metadata['level'] = 'Advanced'
            else:
                metadata['level'] = level
        
        # Try to extract keywords - THIS IS CRITICAL
        keywords_match = re.search(r'MOTS[-\s]CL[ÉE]S\s*:\s*(.+?)(?:\n|$)', text, re.IGNORECASE)
        if not keywords_match:
            keywords_match = re.search(r'KEYWORDS\s*:\s*(.+?)(?:\n|$)', text, re.IGNORECASE)
        if not keywords_match:
            keywords_match = re.search(r'الكلمات المفتاحية\s*:\s*(.+?)(?:\n|$)', text)
        
        if keywords_match:
            keywords_text = keywords_match.group(1).strip()
            # Split by comma or semicolon and clean up
            keywords = [kw.strip() for kw in re.split(r'[,;]', keywords_text) if kw.strip()]
            metadata['keywords'] = keywords
        
        # Try to extract exercise statement (remove metadata from exercise content)
        exercise_match = re.search(r'[ÉE]NONC[ÉE]\s*:\s*(.+)', text, re.IGNORECASE | re.DOTALL)
        if not exercise_match:
            exercise_match = re.search(r'EXERCISE\s*:\s*(.+)', text, re.IGNORECASE | re.DOTALL)
        if not exercise_match:
            exercise_match = re.search(r'التمرين\s*:\s*(.+)', text, re.DOTALL)
        
        if exercise_match:
            metadata['exercise'] = exercise_match.group(1).strip()
        else:
            # If no exercise marker, try to extract content after metadata
            # Remove metadata lines
            exercise_text = text
            exercise_text = re.sub(r'TITRE\s*:.+?\n', '', exercise_text, flags=re.IGNORECASE)
            exercise_text = re.sub(r'TITLE\s*:.+?\n', '', exercise_text, flags=re.IGNORECASE)
            exercise_text = re.sub(r'العنوان\s*:.+?\n', '', exercise_text)
            exercise_text = re.sub(r'NIVEAU\s*:.+?\n', '', exercise_text, flags=re.IGNORECASE)
            exercise_text = re.sub(r'LEVEL\s*:.+?\n', '', exercise_text, flags=re.IGNORECASE)
            exercise_text = re.sub(r'المستوى\s*:.+?\n', '', exercise_text)
            exercise_text = re.sub(r'MOTS[-\s]CL[ÉE]S\s*:.+?\n', '', exercise_text, flags=re.IGNORECASE)
            exercise_text = re.sub(r'KEYWORDS\s*:.+?\n', '', exercise_text, flags=re.IGNORECASE)
            exercise_text = re.sub(r'الكلمات المفتاحية\s*:.+?\n', '', exercise_text)
            metadata['exercise'] = exercise_text.strip()
        
        return metadata        
    
    def clean_latex_response(self, response):
        """Clean LaTeX response from AI - avec transformation des délimiteurs."""
        import re
        
        if not response:
            return ""
        
        cleaned = response.strip()
        
        # Étape CRITIQUE: Transformer les délimiteurs mathématiques
        # \( ... \) -> $ ... $
        cleaned = re.sub(r'\\\(((?:[^\\]|\\[^)])*?)\\\)', r'$\1$', cleaned)
        
        # \[ ... \] -> $$ ... $$
        cleaned = re.sub(r'\\\[((?:[^\\]|\\[^\]])*?)\\\]', r'$$\1$$', cleaned)
        
        # Étape 1: Identifier si c'est une réponse d'IA problématique
        has_ia_problems = any(pattern in cleaned for pattern in [
            '\\{begin\\}', '\\{end\\}', '\\text{', '[V[', ']V]'
        ])
        
        # Si pas de problèmes détectés, retourner tel quel
        if not has_ia_problems:
            return cleaned
        
        #print("🔧 Nettoyage d'une réponse IA problématique détecté")
        
        # Étape 2: Corriger les patterns problématiques spécifiques à l'IA
        # Pattern: \text{ \{begin\}(matrix) -> \begin{matrix}
        cleaned = re.sub(r'\\text\s*\{\s*\\\{begin\\\}\s*\(\s*matrix\s*\)', r'\\begin{matrix}', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\\text\s*\{\s*\\\{end\\\}\s*\(\s*matrix\s*\)', r'\\end{matrix}', cleaned, flags=re.IGNORECASE)
        
        # Pattern: \text{ \{begin\}(pmatrix) -> \begin{pmatrix}
        cleaned = re.sub(r'\\text\s*\{\s*\\\{begin\\\}\s*\(\s*pmatrix\s*\)', r'\\begin{pmatrix}', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r'\\text\s*\{\s*\\\{end\\\}\s*\(\s*pmatrix\s*\)', r'\\end{pmatrix}', cleaned, flags=re.IGNORECASE)
        
        # Pattern: [V[ -> \[
        cleaned = re.sub(r'\[V\[', r'\\[', cleaned)
        cleaned = re.sub(r'\]V\]', r'\\]', cleaned)
        
        # Pattern: \text{ \command } -> \command
        cleaned = re.sub(r'\\text\s*\{\s*\\\{([^}]+)\\\}\s*\}', r'\\\1', cleaned)
        
        # Étape 3: Réparer les environnements matrix/pmatrix
        def fix_matrix_content(match):
            env_type = match.group(1)  # matrix, pmatrix, etc.
            content = match.group(2)
            # Nettoyer le contenu : réduire les \\ multiples et corriger les &
            content = re.sub(r'\\\\+', r'\\\\', content)
            content = content.replace('\\&', '&')
            return f'\\begin{{{env_type}}}{content}\\end{{{env_type}}}'
        
        # Appliquer à tous les environnements matrix-like
        for env in ['matrix', 'pmatrix', 'bmatrix', 'vmatrix', 'Bmatrix']:
            cleaned = re.sub(
                rf'\\begin\{{{env}\}}(.*?)\\end\{{{env}\}}', 
                fix_matrix_content, 
                cleaned, 
                flags=re.DOTALL
            )
        
        # Étape 4: Nettoyage final
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = re.sub(r'\\\s+', r'\\\\', cleaned)
        
        #print("✅ Nettoyage IA terminé")
        return cleaned.strip()
    
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
        
    # def save_conversation_unified(self):
        # """
        # Unified save that handles partial solutions and assembles them.
        # """
        # if not self.chat_history:
            # QMessageBox.warning(
                # self,
                # "Aucune conversation",
                # "Il n'y a pas de conversation à sauvegarder."
            # )
            # return

        # # Get full conversation
        # conversation_latex = self.get_conversation_as_latex()

        # # If we have a partial solution being built, use that instead
        # if hasattr(self, 'partial_solution') and self.partial_solution:
            # # Replace any incomplete solution in conversation with the assembled one
            # import re
            # conversation_latex = re.sub(
                # r'\\begin\{solution\}.*?(?=\\begin\{|$)',
                # self.partial_solution,
                # conversation_latex,
                # flags=re.DOTALL | re.IGNORECASE
            # )

        # # Extract exercise and solution blocks
        # import re
        
        # exercise_match = re.search(
            # r'\\begin\{exercise\}(.*?)\\end\{exercise\}',
            # conversation_latex,
            # re.DOTALL | re.IGNORECASE
        # )

        # # Look for solution - it might not have \end{solution} yet
        # solution_match = re.search(
            # r'\\begin\{solution\}(.*?)(?:\\end\{solution\}|$)',
            # conversation_latex,
            # re.DOTALL | re.IGNORECASE
        # )

        # exercise_content = ""
        # solution_content = ""

        # if exercise_match:
            # exercise_content = exercise_match.group(1).strip()

        # if solution_match:
            # solution_content = solution_match.group(1).strip()
            # # Remove trailing incomplete markers
            # solution_content = re.sub(r'\\end\{solution\}\s*$', '', solution_content).strip()

        # # If nothing found, use full conversation in exercise
        # if not exercise_content and not solution_content:
            # exercise_content = conversation_latex

        # # Open dialog
        # from dialogs import AddEditExerciseDialog
        # dialog = AddEditExerciseDialog(
            # self,
            # None,
            # self.db.get_all_levels() if self.db else [],
            # self.db.get_topic_tree() if self.db else []
        # )

        # # Pre-fill metadata from AI-generated exercise if available
        # if hasattr(self, 'current_ai_metadata') and self.current_ai_metadata:
            # metadata = self.current_ai_metadata
            
            # # Fill name
            # dialog.name_edit.setText(metadata.get('title', ''))
            
            # # Fill level
            # level = metadata.get('level', '')
            # if level:
                # # Normalize level names to match combo box
                # level_lower = level.lower()
                # if 'basic' in level_lower or 'basique' in level_lower or 'مبتدئ' in level_lower:
                    # dialog.level_combo.setCurrentText('Basic')
                # elif 'intermediate' in level_lower or 'intermédiaire' in level_lower or 'متوسط' in level_lower:
                    # dialog.level_combo.setCurrentText('Intermediate')
                # elif 'advanced' in level_lower or 'avancé' in level_lower or 'متقدم' in level_lower:
                    # dialog.level_combo.setCurrentText('Advanced')
                # else:
                    # dialog.level_combo.setCurrentText(level)
            
            # # Fill keywords - THIS IS THE IMPORTANT PART
            # keywords = metadata.get('keywords', [])
            # if keywords:
                # # Convert list to comma-separated string
                # if isinstance(keywords, list):
                    # keywords_text = ', '.join(keywords)
                # else:
                    # keywords_text = str(keywords)
                # dialog.keywords_edit.setText(keywords_text)

        # # Fill exercise and solution content
        # if exercise_content:
            # dialog.exercise_edit.setPlainText(exercise_content)

        # if solution_content:
            # dialog.solution_edit.setPlainText(solution_content)

        # # Status message
        # status_parts = []
        # if exercise_content:
            # status_parts.append(self.tr("exercise_detected"))
        # if solution_content:
            # status_parts.append(self.tr("solution_detected"))
            # if not re.search(r'\\end\{solution\}', conversation_latex):
                # status_parts.append(self.tr("not_complete_msg"))
        
        # if not status_parts:
            # status_parts.append("⚠️ Full conversation in Exercise field")

        # QMessageBox.information(self, "Auto-detection", "\n".join(status_parts))

        # if dialog.exec_() == AddEditExerciseDialog.Accepted:
            # data = dialog.get_data()
            # try:
                # if self.db:
                    # ex_id, keycode = self.db.add_exercise(
                        # name=data['name'],
                        # latex=data['latex'],
                        # solution=data['solution'],
                        # level=data['level'],
                        # topic_ids=data['topic_ids'],
                        # keywords=data['keywords']  # This now includes the AI-generated keywords
                    # )
                    # QMessageBox.information(
                        # self,
                        # "Success",
                        # f"Exercise saved!\nCode: {keycode}"
                    # )
                    # self.add_chat_message(
                        # "System",
                        # f"✅ Saved with code: {keycode}"
                    # )
                    # if hasattr(self.main_window, 'load_exercise'):
                        # self.main_window.load_exercise(ex_id)
                    # # Clear partial solution after successful save
                    # self.partial_solution = None
                # else:
                    # QMessageBox.warning(self, "Error", "Database not available")
            # except Exception as e:
                # QMessageBox.critical(self, "Error", f"Failed:\n{str(e)}")


    def save_conversation_unified(self):
        """
        Unified save that handles partial solutions and assembles them.
        """
        if not self.chat_history:
            # Create custom warning dialog with translated buttons
            dialog = QMessageBox(self)
            dialog.setWindowTitle(self.tr("no_conversation_title"))
            dialog.setText(self.tr("no_conversation_message"))
            dialog.setIcon(QMessageBox.Warning)
            
            # Add translated OK button
            ok_btn = dialog.addButton(self.tr("ok"), QMessageBox.AcceptRole)
            dialog.exec_()
            return

        # Get full conversation
        conversation_latex = self.get_conversation_as_latex()

        # If we have a partial solution being built, use that instead
        if hasattr(self, 'partial_solution') and self.partial_solution:
            # Replace any incomplete solution in conversation with the assembled one
            import re
            conversation_latex = re.sub(
                r'\\begin\{solution\}.*?(?=\\begin\{|$)',
                self.partial_solution,
                conversation_latex,
                flags=re.DOTALL | re.IGNORECASE
            )

        # Extract exercise and solution blocks
        import re
        
        exercise_match = re.search(
            r'\\begin\{exercise\}(.*?)\\end\{exercise\}',
            conversation_latex,
            re.DOTALL | re.IGNORECASE
        )

        # Look for solution - it might not have \end{solution} yet
        solution_match = re.search(
            r'\\begin\{solution\}(.*?)(?:\\end\{solution\}|$)',
            conversation_latex,
            re.DOTALL | re.IGNORECASE
        )

        exercise_content = ""
        solution_content = ""

        if exercise_match:
            exercise_content = exercise_match.group(1).strip()

        if solution_match:
            solution_content = solution_match.group(1).strip()
            # Remove trailing incomplete markers
            solution_content = re.sub(r'\\end\{solution\}\s*$', '', solution_content).strip()

        # If nothing found, use full conversation in exercise
        if not exercise_content and not solution_content:
            exercise_content = conversation_latex

        # Open dialog
        from dialogs import AddEditExerciseDialog
        dialog = AddEditExerciseDialog(
            self,
            None,
            self.db.get_all_levels() if self.db else [],
            self.db.get_topic_tree() if self.db else []
        )

        # Pre-fill metadata from AI-generated exercise if available
        if hasattr(self, 'current_ai_metadata') and self.current_ai_metadata:
            metadata = self.current_ai_metadata
            
            # Fill name
            dialog.name_edit.setText(metadata.get('title', ''))
            
            # Fill level
            level = metadata.get('level', '')
            if level:
                # Normalize level names to match combo box
                level_lower = level.lower()
                if 'basic' in level_lower or 'basique' in level_lower or 'مبتدئ' in level_lower:
                    dialog.level_combo.setCurrentText('Basic')
                elif 'intermediate' in level_lower or 'intermédiaire' in level_lower or 'متوسط' in level_lower:
                    dialog.level_combo.setCurrentText('Intermediate')
                elif 'advanced' in level_lower or 'avancé' in level_lower or 'متقدم' in level_lower:
                    dialog.level_combo.setCurrentText('Advanced')
                else:
                    dialog.level_combo.setCurrentText(level)
            
            # Fill keywords - THIS IS THE IMPORTANT PART
            keywords = metadata.get('keywords', [])
            if keywords:
                # Convert list to comma-separated string
                if isinstance(keywords, list):
                    keywords_text = ', '.join(keywords)
                else:
                    keywords_text = str(keywords)
                dialog.keywords_edit.setText(keywords_text)

        # Fill exercise and solution content
        if exercise_content:
            dialog.exercise_edit.setPlainText(exercise_content)

        if solution_content:
            dialog.solution_edit.setPlainText(solution_content)

        # Status message
        status_parts = []
        if exercise_content:
            status_parts.append(self.tr("exercise_detected"))
        if solution_content:
            status_parts.append(self.tr("solution_detected"))
            if not re.search(r'\\end\{solution\}', conversation_latex):
                status_parts.append(self.tr("solution_incomplete"))
        
        if not status_parts:
            status_parts.append(self.tr("full_conversation"))

        # Create custom information dialog with translated OK button
        info_dialog = QMessageBox(self)
        info_dialog.setWindowTitle(self.tr("auto_detection"))
        info_dialog.setText("\n".join(status_parts))
        info_dialog.setIcon(QMessageBox.Information)
        info_dialog.addButton(self.tr("ok"), QMessageBox.AcceptRole)
        info_dialog.exec_()

        if dialog.exec_() == AddEditExerciseDialog.Accepted:
            data = dialog.get_data()
            try:
                if self.db:
                    ex_id, keycode = self.db.add_exercise(
                        name=data['name'],
                        latex=data['latex'],
                        solution=data['solution'],
                        level=data['level'],
                        topic_ids=data['topic_ids'],
                        keywords=data['keywords']  # This now includes the AI-generated keywords
                    )
                    
                    # Success message with translated OK button
                    success_dialog = QMessageBox(self)
                    success_dialog.setWindowTitle(self.tr("success"))
                    success_dialog.setText(self.tr("exercise_saved").format(keycode=keycode))
                    success_dialog.setIcon(QMessageBox.Information)
                    success_dialog.addButton(self.tr("ok"), QMessageBox.AcceptRole)
                    success_dialog.exec_()
                    
                    self.add_chat_message(
                        "System",
                        self.tr("saved_with_code").format(keycode=keycode)
                    )
                    if hasattr(self.main_window, 'load_exercise'):
                        self.main_window.load_exercise(ex_id)
                    # Clear partial solution after successful save
                    self.partial_solution = None
                else:
                    # Error message with translated OK button
                    error_dialog = QMessageBox(self)
                    error_dialog.setWindowTitle(self.tr("error"))
                    error_dialog.setText(self.tr("database_unavailable"))
                    error_dialog.setIcon(QMessageBox.Warning)
                    error_dialog.addButton(self.tr("ok"), QMessageBox.AcceptRole)
                    error_dialog.exec_()
            except Exception as e:
                # Error message with translated OK button
                error_dialog = QMessageBox(self)
                error_dialog.setWindowTitle(self.tr("error"))
                error_dialog.setText(self.tr("save_failed").format(error=str(e)))
                error_dialog.setIcon(QMessageBox.Critical)
                error_dialog.addButton(self.tr("ok"), QMessageBox.AcceptRole)
                error_dialog.exec_()

    def clear_chat(self):
        """Clear the chat history."""
        # Create custom dialog
        dialog = QMessageBox(self)
        dialog.setWindowTitle(self.tr("clear_chat"))
        dialog.setText(self.tr("clear_confirmation"))
        
        # Create custom buttons with translations
        yes_btn = dialog.addButton(self.tr("yes"), QMessageBox.YesRole)
        no_btn = dialog.addButton(self.tr("no"), QMessageBox.NoRole)
        dialog.setDefaultButton(no_btn)
        
        dialog.exec_()
        
        if dialog.clickedButton() == yes_btn:
            self.chat_history = []
            self.add_chat_message("AI", self.tr("clear_chat_message"))

    def generate_offline_exercise(self):
        """Generate exercise using offline rule-based system."""
        import random
        exercises = [
            "Find the derivative of $f(x) = x^3 + 2x^2 - 5x + 1$.",
            "Solve the equation: $x^2 - 4x + 4 = 0$.",
            "Calculate the integral: $\\int (3x^2 + 2x - 1) dx$.",
            "Find the limit: $\\lim_{x \\to 0} \\frac{\\sin(x)}{x}$.",
            "Solve the system: $\\begin{cases} 2x + 3y = 7 \\\\ x - y = 1 \\end{cases}$"
        ]
        return random.choice(exercises)
    def generate_offline_solution(self):
        """Generate solution using offline rule-based system."""
        return "This is a placeholder solution. In online mode, AI would generate the actual solution."
    def update_config(self, new_config):
        """Update AI configuration."""
        self.ai_config = new_config
        self.update_ai_status()