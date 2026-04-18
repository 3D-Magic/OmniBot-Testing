#!/usr/bin/env python3
"""
OMNIBOT TITAN - PyQt5 Kiosk Browser
Fullscreen web browser for Raspberry Pi display
"""

import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtCore import QUrl, Qt
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineSettings

class KioskBrowser(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("OMNIBOT TITAN")
        self.showFullScreen()
        
        self.browser = QWebEngineView()
        self.setCentralWidget(self.browser)
        
        settings = self.browser.settings()
        settings.setAttribute(QWebEngineSettings.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.LocalStorageEnabled, True)
        settings.setAttribute(QWebEngineSettings.PluginsEnabled, True)
        settings.setAttribute(QWebEngineSettings.FullScreenSupportEnabled, True)
        settings.setAttribute(QWebEngineSettings.TouchIconsEnabled, True)
        settings.setAttribute(QWebEngineSettings.FocusOnNavigationEnabled, True)
        
        self.browser.setStyleSheet("""
            QWebEngineView {
                background: #0a0a0f;
            }
        """)
        
        url = os.environ.get('OMNIBOT_URL', 'http://localhost:8081')
        self.browser.setUrl(QUrl(url))
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()
        super().keyPressEvent(event)

def main():
    os.environ['QT_QPA_PLATFORM'] = 'xcb'
    os.environ['QT_AUTO_SCREEN_SCALE_FACTOR'] = '0'
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    from PyQt5.QtGui import QPalette, QColor
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(10, 10, 15))
    palette.setColor(QPalette.WindowText, Qt.white)
    app.setPalette(palette)
    
    window = KioskBrowser()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
