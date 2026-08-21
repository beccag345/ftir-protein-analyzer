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
    )
from PySide6.QtCore import (
    Qt,
    Slot,
    QDir,
    QAbstractListModel,
    QModelIndex
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
    def __init__(self, files: list, *args, **kwargs):
        super().__init__(*args, **kwargs)
        v_layout = QVBoxLayout()
        self.setLayout(v_layout)
        self.file_list = files
        
        # Create a list view of files at the top
        file_list_disp = QListView()
        clipped_paths = list(map(lambda f: f.split("/")[-1], self.file_list))
        model = ListViewModel(data_list=clipped_paths)
        file_list_disp.setModel(model)
        v_layout.addWidget(file_list_disp)
        
class ListViewModel(QAbstractListModel):
    """Used to represent opened files of replicates within a sample"""
    
    def __init__(self, data_list: list, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data_list = data_list

    def rowCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return len(self.data_list)

    def data(
        self,
        index: QModelIndex,
        role=Qt.ItemDataRole.DisplayRole,
    ):
        if not index.isValid():
            return None

        row = index.row()
        if not 0 <= row < len(self.data_list):
            return None

        if role == Qt.ItemDataRole.DisplayRole:
            return self.data_list[row]

        return None
                 

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
            editor_view = GraphEditor(files=self.selected_files)
            self.addWidget(editor_view)
        
