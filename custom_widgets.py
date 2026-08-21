import sys
from PySide6.QtWidgets import (
    QApplication, 
    QTabWidget, 
    QHBoxLayout, 
    QVBoxLayout,
    QPushButton, 
    QSplitter, 
    QMainWindow, 
    QWidget,
    QStackedWidget,
    QSizePolicy,
    QFileDialog,
    QListView,
    QFileSystemModel
    )
from PySide6.QtCore import (
    Slot,
    QDir,
    QAbstractListModel
    )

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setGeometry(100, 100, 800, 600)  
        self.setMinimumSize(400, 300)

class ImportBtn(QPushButton):
    """Prompts user to select files to be averaged"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, text="Files go here", **kwargs)
        self.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)

class GraphEditor(QWidget):
    """Displays technical replicate FTIR and allows to fit gaussians to them"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        v_layout = QVBoxLayout()
        self.setLayout(v_layout)
        
        opened_files_list = QListView()
        model = QFileSystemModel()
        model.setRootPath(QDir.currentPath())
        opened_files_list.setModel(model)
        v_layout.addWidget(opened_files_list)
        
class ListViewModel(QAbstractListModel):
    """Used to represent the opened """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    def rowCount(self, index, role):
        return super().rowCount()         

class ImportAndEdit(QStackedWidget):
    """ 
    Section in the left half of the splitter.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        import_btn = ImportBtn()
        import_btn.clicked.connect(self.display_graphs)
        self.addWidget(import_btn)
        
    @Slot()
    def display_graphs(self):
        """ 
        Replaces file import button with a paginated graph editor
        """
        # Display file explorer
        explorer = QFileDialog()
        self.selected_files = explorer.getOpenFileNames()[0]
        self.widgetAdded.connect(self.setCurrentIndex)
        if self.selected_files:
            editor_view = GraphEditor()
            self.addWidget(editor_view)
        # Create list view of files
