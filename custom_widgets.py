import sys
import pyqtgraph as pg
import pandas as pd
from dataclasses import dataclass
from PySide6.QtWidgets import (
    QApplication, 
    QTabWidget, 
    QHBoxLayout, 
    QVBoxLayout,
    QPushButton, 
    QMainWindow, 
    QWidget,
    QLabel,
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
    QItemSelectionModel,
    QModelIndex
    )
import ftir_graph as ftir

pg.setConfigOption("foreground", "k")
pg.setConfigOption("background", "w")

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
        
class PlotData():
    """Contains information about fitted gaussians, peaks, as well as the working dataframe for techical replicate plots"""
    def __init__(self, filepath):
        self.data = ftir.tech_df(file = filepath)
        self.gaussian = pd.DataFrame()
        self.max_peaks, self.local_min_xs = self._local_min() # total number of peaks to be fitted and a list of their wavenum positions
        self.peaks_fitted = 0 # peaks that have already been fitted
        
    def _local_min(self):
            """Helper function representing the total nubmer of local minima in the plotted graph
            Returns:
                (qty, locations) (tuple)
            """
            y = self.data["Second Derivative"].to_numpy(copy=False)
            minima = (y[1:-1] < y[:-2]) & (y[1:-1] < y[2:]) & (y[1:-1] < 0)
            locations = self.data["Wavenumber"].to_numpy(copy=False)[1:-1][minima].tolist()
            return len(locations), locations

class GraphEditor(QWidget):
    """Main widget Displays technical replicate FTIR and allows to fit gaussians to them"""
    def __init__(self, files: list, *args, **kwargs):
        super().__init__(*args, **kwargs)
        v_layout = QVBoxLayout()
        self.setLayout(v_layout)
        self.file_list = files # List of paths
        self.plot_objs = list(map(lambda f: PlotData(filepath=f), self.file_list))
        self.active_file = 0 # Changes when another technical replicate is selected        
        
        # Create a list view of files at the top
        file_list_disp = QListView()
        clipped_paths = list(map(lambda f: f.split("/")[-1], self.file_list))
        model = ListViewModel(data_list=clipped_paths)
        file_list_disp.setModel(model)
        v_layout.addWidget(file_list_disp)
        
        # Counter showing gaussian fitting progress (shows how many negative peaks have been accounted for)
        self.gaus_counter = QLabel()
        v_layout.addWidget(self.gaus_counter)
        
        # Main plot control area for fitting gaussians
        file_list_disp.selectionModel().currentChanged.connect(self.change_active_plot)
        self.graphics_view = pg.GraphicsView()
        v_layout.addWidget(self.graphics_view)

        self.plot_item = pg.PlotItem()
        self.graphics_view.setCentralItem(self.plot_item)

        self.curve = self.plot_item.plot()
        self.plot_item.addLine(
            y=0,
            movable=False,
            pen=pg.mkPen("k", width=1),
        )
        
    @Slot(QModelIndex)
    def change_active_plot(self, index):
        """Triggered when a technical replicate file is selected within the widget's QListView"""
        int_idx = index.row()
        self.active_file = int_idx
        self.set_plot_item(int_idx) # update plot area
        # update "gaussians to complete" counter
        current_obj = self.plot_objs[int_idx]
        self.gaus_counter.setText(f"Peaks fitted: {current_obj.peaks_fitted}/{current_obj.max_peaks}")
        
    def set_plot_item(self, active_index):
        """Returns a PlotItem containing the line plot based on provided technical replicate file index"""
        df = self.plot_objs[active_index].data
        x = df["Wavenumber"].to_numpy(copy=False)
        y = df["Second Derivative"].to_numpy(copy=False)
        self.curve.setData(x, y)
            
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
        
