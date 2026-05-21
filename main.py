import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon, QPixmap
from main_window import MainWindow

def main():
    """Main entry point for the application."""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # Optional: Add custom styling
    app.setStyleSheet("""
        QMainWindow, QDialog {
            background-color: #f5f5f5;
        }
        QPushButton {
            background-color: #0078d4;
            color: white;
            border: none;
            padding: 8px 8px;
            border-radius: 4px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #106ebe;
        }
        QPushButton:pressed {
            background-color: #005a9e;
        }
    """)

    app.setWindowIcon(QIcon("YasmeenTex.svg"))
    
    main_window = MainWindow()
    
    main_window.show()
    
    main_window.showMaximized()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
