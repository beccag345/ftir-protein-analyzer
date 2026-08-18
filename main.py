# SPDX-License-Identifier: MIT

import sys
from PySide6.QtWidgets import QApplication, QLabel

app = QApplication(sys.argv)
label = QLabel("Hello, World!")
label.show()
app.exec()
