import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPalette, QColor, QKeySequence, QShortcut

from src.controller import AppController

if __name__ == "__main__":
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("DeepLook")

    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window, QColor(0, 0, 0))
    pal.setColor(QPalette.ColorRole.WindowText, QColor(255, 255, 255))
    app.setPalette(pal)

    ctrl = AppController()

    QShortcut(QKeySequence("Ctrl+Shift+I"), app).activated.connect(ctrl._toggle_mode)
    QShortcut(QKeySequence("Ctrl+Shift+Q"), app).activated.connect(ctrl.stop)
    QShortcut(QKeySequence("Ctrl+Shift+Q"), app).activated.connect(app.quit)

    ctrl.start()
    sys.exit(app.exec())
