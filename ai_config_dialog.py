"""
ai_config_dialog.py: AI configuration dialog for LaTeX Exercise Viewer.
"""
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QComboBox, QLineEdit, QPushButton, QLabel,
    QGroupBox, QMessageBox, QApplication
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont


class AIConfigDialog(QDialog):
    """Dialog for configuring AI settings."""
    
    def __init__(self, parent=None, config=None):
        super().__init__(parent)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.config = config or {}
        
        self.setWindowTitle("AI Assistant Configuration")
        self.setMinimumWidth(500)
        self.setMinimumHeight(650)
        
        self.setup_ui()
        self.load_config()
    
    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Title
        title = QLabel("AI Assistant Configuration")
        title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        layout.addWidget(title)
        
        # Mode selection
        mode_group = QGroupBox("AI Mode")
        mode_layout = QVBoxLayout(mode_group)
        
        self.ai_mode_combo = QComboBox()
        self.ai_mode_combo.addItem("Offline (Rule-based, no internet)", "offline")
        self.ai_mode_combo.addItem("Online (AI-powered, requires internet)", "online")
        self.ai_mode_combo.currentIndexChanged.connect(self._on_ai_mode_changed)
        mode_layout.addWidget(self.ai_mode_combo)
        
        layout.addWidget(mode_group)
        
        # Online AI settings (initially hidden)
        self.online_ai_group = QGroupBox("Online AI Settings")
        online_layout = QFormLayout(self.online_ai_group)
        
        # Provider selection
        self.ai_provider_combo = QComboBox()
        providers = [
            ("Groq (Fast & Free)", "groq"),
            ("Qwen - Alibaba Cloud (Paid)", "qwen"),
            ("DeepSeek (Paid)", "deepseek"),
            ("OpenAI ChatGPT (Paid)", "openai"),
            ("Hugging Face (Free, no key needed)", "huggingface"),
            ("Anthropic Claude (Paid)", "anthropic"),
            ("Google Gemini (Paid)", "gemini")
        ]
        for name, key in providers:
            self.ai_provider_combo.addItem(name, key)
        self.ai_provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        online_layout.addRow("Provider:", self.ai_provider_combo)
        
        # API Key
        self.ai_api_key = QLineEdit()
        self.ai_api_key.setEchoMode(QLineEdit.Password)
        self.ai_api_key.setPlaceholderText("Enter API key")
        online_layout.addRow("API Key:", self.ai_api_key)
        
        # Show/Hide API key button
        key_btn_layout = QHBoxLayout()
        self.show_key_btn = QPushButton("👁 Show")
        self.show_key_btn.setMaximumWidth(80)
        self.show_key_btn.clicked.connect(self._toggle_api_key_visibility)
        key_btn_layout.addWidget(self.show_key_btn)
        key_btn_layout.addStretch()
        online_layout.addRow("", key_btn_layout)
        
        # Model selection
        self.ai_model_combo = QComboBox()
        online_layout.addRow("Model:", self.ai_model_combo)
        
        # Test connection button
        test_btn = QPushButton("🔗 Test Connection")
        test_btn.clicked.connect(self._test_ai_connection)
        online_layout.addRow("", test_btn)
        
        # Status label
        self.ai_status_label = QLabel("Not configured")
        self.ai_status_label.setStyleSheet("color: #666; padding: 5px;")
        online_layout.addRow("Status:", self.ai_status_label)
        
        layout.addWidget(self.online_ai_group)
        
        # Info section
        info_group = QGroupBox("ℹ Information")
        info_layout = QVBoxLayout(info_group)
        
        info_text = QLabel(
            "<b>Get API Keys:</b><br>"
            "• Groq (Free): <a href='https://console.groq.com'>console.groq.com</a><br>"
            "• Qwen: <a href='https://dashscope.console.aliyun.com'>dashscope.console.aliyun.com</a><br>"
            "• DeepSeek: <a href='https://platform.deepseek.com'>platform.deepseek.com</a><br>"
            "• OpenAI: <a href='https://platform.openai.com/api-keys'>platform.openai.com</a><br>"
            "• HuggingFace: <a href='https://huggingface.co/settings/tokens'>huggingface.co/settings/tokens</a><br>"
            "• Anthropic: <a href='https://console.anthropic.com'>console.anthropic.com</a><br>"
            "• Google AI Studio: <a href='https://aistudio.google.com'>aistudio.google.com</a>"
        )
        info_text.setWordWrap(True)
        info_text.setOpenExternalLinks(True)
        info_text.setStyleSheet("padding: 10px; background: #f0f0f0; border-radius: 5px;")
        info_layout.addWidget(info_text)
        
        layout.addWidget(info_group)
        
        layout.addStretch()
        
        # Buttons
        button_layout = QHBoxLayout()
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.accept)
        button_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
        # Initially hide online settings
        self.online_ai_group.setVisible(False)
        self._update_models_list()
        self._update_api_key_requirement()
    
    def load_config(self):
        """Load configuration into UI."""
        mode = self.config.get('mode', 'offline')
        index = self.ai_mode_combo.findData(mode)
        if index >= 0:
            self.ai_mode_combo.setCurrentIndex(index)
        
        provider = self.config.get('provider', 'groq')
        index = self.ai_provider_combo.findData(provider)
        if index >= 0:
            self.ai_provider_combo.setCurrentIndex(index)
        
        self.ai_api_key.setText(self.config.get('api_key', ''))
        
        model = self.config.get('model', '')
        if model and self.ai_model_combo.findText(model) >= 0:
            self.ai_model_combo.setCurrentText(model)
    
    def get_config(self):
        """Get configuration from UI."""
        return {
            'mode': self.ai_mode_combo.currentData(),
            'provider': self.ai_provider_combo.currentData(),
            'api_key': self.ai_api_key.text(),
            'model': self.ai_model_combo.currentText(),
            'enabled': True
        }
    
    def _on_ai_mode_changed(self, index):
        """Handle AI mode change"""
        mode = self.ai_mode_combo.currentData()
        self.online_ai_group.setVisible(mode == "online")
        
        if mode == "online":
            self._update_models_list()

    def _on_provider_changed(self, index):
        """Handle provider change"""
        self._update_models_list()
        self._update_api_key_requirement()
    
    def _update_models_list(self):
        """Update available models based on provider."""
        self.ai_model_combo.clear()
        
        provider = self.ai_provider_combo.currentData()
        
        # Models with descriptions for better UX
        models = {
            'groq': [
                'llama-3.3-70b-versatile', 
                'mixtral-8x7b-32768', 
                'llama-3.1-8b-instant'
            ],
            'openai': [
                'gpt-4o',
                'gpt-4o-mini', 
                'gpt-3.5-turbo'
            ],
            'anthropic': [
                'claude-3-haiku-20240307',
                'claude-3-sonnet-20240229', 
                'claude-3-opus-20240229'
            ],
            'gemini': [
                'gemini-pro',
                'gemini-pro-vision'
            ],
            'qwen': [
                'qwen-turbo',
                'qwen-plus', 
                'qwen-max'
            ],
            # CORRECTION: DeepSeek models that actually work
            'deepseek': [
                'deepseek-chat',           # Modèle principal de chat
                'deepseek-reasoner',       # Pour le raisonnement
                'deepseek-v2',             # Version 2
                'deepseek-coder'           # Pour le code
            ],
            'huggingface': [
                'microsoft/DialoGPT-large',
                'google/flan-t5-xxl',
                'mistralai/Mistral-7B-Instruct-v0.1'
            ]
        }
        
        available_models = models.get(provider, [])
        
        if available_models:
            self.ai_model_combo.addItems(available_models)
            
            # Set default model based on provider
            default_models = {
                'groq': 'llama-3.3-70b-versatile',
                'openai': 'gpt-4o-mini',
                'anthropic': 'claude-3-haiku-20240307',
                'gemini': 'gemini-pro',
                'qwen': 'qwen-turbo',
                'deepseek': 'deepseek-chat',
                'huggingface': 'microsoft/DialoGPT-large'
            }
            
            default_model = default_models.get(provider)
            if default_model in available_models:
                self.ai_model_combo.setCurrentText(default_model)
        else:
            self.ai_model_combo.addItem("default")
        
    def _update_api_key_requirement(self):
        """Update API key field requirement based on provider"""
        provider = self.ai_provider_combo.currentData()
        
        if provider == "huggingface":
            self.ai_api_key.setPlaceholderText("Optional (better rate limits)")
            self.ai_api_key.setStyleSheet("")
        else:
            self.ai_api_key.setPlaceholderText("Required")
            self.ai_api_key.setStyleSheet("border: 1px solid #ff6b6b;")

    def _toggle_api_key_visibility(self):
        """Toggle API key visibility"""
        if self.ai_api_key.echoMode() == QLineEdit.Password:
            self.ai_api_key.setEchoMode(QLineEdit.Normal)
            self.show_key_btn.setText("🔒 Hide")
        else:
            self.ai_api_key.setEchoMode(QLineEdit.Password)
            self.show_key_btn.setText("👁 Show")

    def _test_ai_connection(self):
        """Test AI connection"""
        mode = self.ai_mode_combo.currentData()
        
        if mode == "offline":
            QMessageBox.information(self, "Offline Mode", "Offline mode doesn't require connection.")
            return
        
        provider = self.ai_provider_combo.currentData()
        api_key = self.ai_api_key.text().strip()
        
        if not api_key and provider != "huggingface":
            QMessageBox.warning(self, "Missing API Key", "Please enter your API key.")
            return
        
        self.ai_status_label.setText("Testing connection...")
        self.ai_status_label.setStyleSheet("color: #ff9800;")
        QApplication.processEvents()
        
        # Test connection
        try:
            from online_ai_provider import OnlineAIProvider
            
            provider_obj = OnlineAIProvider()
            success = provider_obj.set_provider(provider, api_key, self.ai_model_combo.currentText())
            
            if not success:
                self.ai_status_label.setText("❌ Invalid provider configuration")
                self.ai_status_label.setStyleSheet("color: #f44336;")
                QMessageBox.warning(self, "Configuration Error", "Invalid provider configuration.")
                return
            
            response, error = provider_obj.query("Hello", max_tokens=10)
            
            if error:
                self.ai_status_label.setText(f"❌ Failed: {error}")
                self.ai_status_label.setStyleSheet("color: #f44336;")
                QMessageBox.warning(self, "Connection Failed", f"Error: {error}")
            else:
                self.ai_status_label.setText("✅ Connected successfully")
                self.ai_status_label.setStyleSheet("color: #4caf50;")
                QMessageBox.information(self, "Success", "Connection successful!")
                
        except Exception as e:
            self.ai_status_label.setText(f"❌ Error: {str(e)}")
            self.ai_status_label.setStyleSheet("color: #f44336;")
            QMessageBox.critical(self, "Error", str(e))