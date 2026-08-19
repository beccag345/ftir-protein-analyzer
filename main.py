# SPDX-License-Identifier: MIT

import sys
from PySide6.QtWidgets import QApplication, QPushButton
from PySide6.QtCore import Slot

@Slot()
def say_hello():
    print("This is a simple test!")

# Qt app creation
app = QApplication()
btn = QPushButton("Test text")
btn.clicked.connect(say_hello)
btn.show()
# Main loop
app.exec()
