# SPDX-License-Identifier: MIT

from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QVBoxLayout,
    QSplitter,
    QTabWidget,
    QToolButton,
    QWidget,
    QTextEdit,
    QLabel,
)
from custom_widgets import (
    ImportBtn, 
    MainWindow,
    GraphEditor,
    ImportAndEdit
)
from PySide6.QtCore import Slot, Signal


class AddableTabWidget(QTabWidget):
    """A tab widget with a plus button beside the last open tab."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setObjectName("workspaceTabs")
        self.tabBar().setObjectName("workspaceTabBar")

        self.add_tab_button = QToolButton(self)
        self.add_tab_button.setObjectName("addTabButton")
        self.add_tab_button.setText("+")
        self.add_tab_button.setToolTip("Create a new sample")
        self.add_tab_button.setAutoRaise(True)
        self.add_tab_button.setFixedSize(25, 25)
        self._position_add_tab_button()

    def tabInserted(self, index):
        super().tabInserted(index)
        self._position_add_tab_button()

    def tabRemoved(self, index):
        super().tabRemoved(index)
        self._position_add_tab_button()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_add_tab_button()

    def _position_add_tab_button(self):
        tab_bar = self.tabBar()
        if self.count(): # if there are active tabs
            last_tab = tab_bar.tabRect(self.count() - 1)
            last_tab_top_right = tab_bar.mapTo(self, last_tab.topRight())

            x = last_tab_top_right.x() + 4
            y = last_tab_top_right.y() + (
                last_tab.height() - self.add_tab_button.height()
            ) // 2
        else:
            tab_bar_top_left = tab_bar.mapTo(self, tab_bar.rect().topLeft())
            x = tab_bar_top_left.x()
            y = tab_bar_top_left.y()

        self.add_tab_button.move(x, max(0, y))
        self.add_tab_button.raise_()


# Qt app creation
app = QApplication()
stylesheet_path = Path(__file__).with_name("styles.qss")
app.setStyleSheet(stylesheet_path.read_text(encoding="utf-8"))

main_window = MainWindow()

tabs = AddableTabWidget(parent=main_window)
tabs.setTabsClosable(True)
main_window.setCentralWidget(tabs)

class Tab(QWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        stretch_layout = QHBoxLayout(self)

        self.splitter = QSplitter()
        stretch_layout.addWidget(self.splitter)
        stretch_layout.setStretchFactor(self.splitter, 1)
        graph_editor = ImportAndEdit()
        self.splitter.addWidget(graph_editor)        
        
        output_container = QWidget()
        self.splitter.addWidget(output_container)
        self.splitter.setSizes([400, 400])
        output_layout = QVBoxLayout()
        output_container.setLayout(output_layout)
        
        ratio_graph = QLabel("Output graph goes here")
        output_layout.addWidget(ratio_graph)
        
        output_box = QTextEdit()
        output_box.setReadOnly(True)
        graph_editor.currentChanged.connect(
            lambda _index: output_box.setPlainText(graph_editor.get_output())
        )
        output_layout.addWidget(output_box)        

@Slot()
def add_new_tab():
    new_tab = Tab()
    new_tab_index = tabs.addTab(new_tab, "New Sample")
    tabs.setCurrentIndex(new_tab_index)

@Slot(int)
def close_tab(index):
    if tabs.count() > 1:
        tab = tabs.widget(index)
        tabs.removeTab(index)
        tab.deleteLater()


tabs.add_tab_button.clicked.connect(add_new_tab)
tabs.tabCloseRequested.connect(close_tab)
add_new_tab()
# Main loop
main_window.show()
app.exec()
