import math
import sys
import pyqtgraph as pg
import pandas as pd
import numpy as np
from enum import IntEnum, auto
from PySide6.QtWidgets import (
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
    QAbstractListModel,
    QModelIndex
    )
import scipy
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
        self.filepath = filepath
        self.data = ftir.tech_df(file = filepath)
        self.gaussian = pd.DataFrame()
        self.max_peaks, self.local_min_xs = self._local_min() # total number of peaks to be fitted and a list of their wavenum positions
        self.peaks_fitted = 0 # peaks that have already been fitted
        x_interp_tuple = self._get_x_intercepts()
        x_intercepts = pd.concat([x_interp_tuple[0], x_interp_tuple[1]]) # adds x-intercept points to the working dataframe for future gaussian fitting
        length = len(x_intercepts)
        x_intercepts = pd.DataFrame({"Wavenumber": x_intercepts, 
                                     "Abs": np.full(length, np.nan),
                                     "Corrected Abs": np.full(length, np.nan), 
                                     "Second Derivative": np.zeros(length), 
                                     "Point Type": np.full(length, self.PointType.INTERCEPT)})
        self.data = pd.concat([self.data, x_intercepts], ignore_index=True).sort_values(by="Wavenumber").reset_index(drop=True)
        
        # Automatically fit 2nd deriv curve to the data using the least-squares method
        local_minima = self.data.loc[self.data["Point Type"].eq(self.PointType.MIN)]
        params = np.asarray(self._get_guess_params(local_minima["Wavenumber"], local_minima["Second Derivative"], x_interp_tuple[0], x_interp_tuple[1]))
        
        # Fit the 2nd derivative curve to the data using the least-squares method
        
        xdata = self.data["Wavenumber"].loc[ ~self.data["Point Type"].eq(self.PointType.INTERCEPT) ].to_numpy(copy=False)
        ydata = self.data["Second Derivative"].loc[ ~self.data["Point Type"].eq(self.PointType.INTERCEPT) ].to_numpy(copy=False) # Removes artificial x-intercept points from the data to be fitted
        
        # Since our true gaussian function values are so low, normalize the ydata against the depth of the deepest 2nd deriv local min
        norm_factor = abs(
            1 / self.data.loc[self.data["Point Type"].eq(self.PointType.MIN), "Second Derivative"].min()  
            )
        norm_ydata = norm_factor * ydata
        
        params[::3] *= norm_factor

        n_peaks = len(params) // 3
        SIGMA_MIN = 1e-3  # Numerical floor; consider a resolution-based limit

        bounds = (
            np.tile([0, SIGMA_MIN, xdata.min()], n_peaks),
            np.tile([np.inf, np.inf, xdata.max()], n_peaks),
        )
        
        self.opt_params = scipy.optimize.curve_fit(self._2nd_deriv_sum,
                                                   xdata,
                                                   norm_ydata,
                                                   p0=params,
                                                   maxfev=100000,
                                                   bounds=bounds)
        
        # Now restore the original function by dividing optimized As by it, since they are directly proportional to 2nd deriv f(x)
        self.opt_params[0][::3] /= norm_factor
        
        # This is a function that can be called to get the fitted 2nd derivative curve based on the optimized parameters
        self.fitted_2nd_deriv = lambda x: self._2nd_deriv_sum(x, *self.opt_params[0])
        
        self.integrated_areas = self._integrate(self.opt_params[0][::3], self.opt_params[0][1::3], self.opt_params[0][2::3])
        # Compute protein secondary structure ratios
        total_area = self.integrated_areas["Integrated Area"].sum()
        peak_ratios = self.integrated_areas.copy()
        peak_ratios["Fraction"] = peak_ratios["Integrated Area"] / total_area if total_area != 0 else 0
        
        sec_struct_ratios = pd.DataFrame()
        sec_struct_ratios.index = ["α-helix", "3⏨-helix", "β-sheet", "β-turn", "Random Coil", "Unknown"]
        
        sec_struct_ratios.loc["α-helix", "Fraction"] = peak_ratios.loc[peak_ratios["Wavenumber"].between(1652, 1658.8, inclusive="left"), "Fraction"].sum()
        sec_struct_ratios.loc["3⏨-helix", "Fraction"] = peak_ratios.loc[peak_ratios["Wavenumber"].between(1658.8, 1666, inclusive="left"), "Fraction"].sum()
        sec_struct_ratios.loc["β-sheet", "Fraction"] = peak_ratios.loc[
            peak_ratios["Wavenumber"].between(1622, 1644, inclusive="left") | 
            peak_ratios["Wavenumber"].between(1688, 1700, inclusive="left"), "Fraction"].sum()
        sec_struct_ratios.loc["β-turn", "Fraction"] = peak_ratios.loc[peak_ratios["Wavenumber"].between(1666, 1688, inclusive="left"), "Fraction"].sum()
        sec_struct_ratios.loc["Random Coil", "Fraction"] = peak_ratios.loc[peak_ratios["Wavenumber"].between(1644, 1652, inclusive="left"), "Fraction"].sum()
        sec_struct_ratios.loc["Unknown", "Fraction"] = peak_ratios.loc[~peak_ratios["Wavenumber"].between(1622, 1700, inclusive="left"), "Fraction"].sum()

        self.sec_struct_ratios = sec_struct_ratios

    class PointType(IntEnum):
        REGULAR = 0
        MIN = 1
        INTERCEPT = 2
        
    def _integrate(self, As, sigmas, mus):
        """Finds the area underneath original gaussians given As, sigmas, and mus
        Return:
            Pandas dataframe with a wavenumber column of peak locations and corresponding integrated area column
        """
        if (len(As) != len(sigmas)) or (len(sigmas) != len(mus) or (len(As) != len(mus))):
            raise ValueError("As, sigmas, and mus must be of the same length")
        
        integrated_areas = []
        for A, sigma, mu in zip(As, sigmas, mus):
            integrated_areas.append(
                A * sigma * np.sqrt(2 * np.pi)
            )
            
        return pd.DataFrame({"Wavenumber": mus, "Integrated Area": integrated_areas})
        
    def _2nd_deriv_sum(self, x, *args):
        """Returns the sum of all 2nd derivatives of gaussians based on provided parameters
           Parameters follow the format of [A1, sigma1, mu1, A2, sigma2, mu2, ...]"""
        result = np.zeros_like(x)
        if (len(args) % 3 != 0):
            raise ValueError("Number of parameters must be a multiple of 3 (A, sigma, mu for each gaussian)")
        for i in range(0, len(args), 3):
            A, sigma, mu = args[i:i + 3]
            result += (A/(sigma**4))*((x - mu)**2 - sigma**2)*np.exp(-((x - mu)**2)/(2*sigma**2))
        
        return result
        
    def _get_guess_params(self, local_min_xs, local_min_ys, left_intercepts, right_intercepts):
        """Returns a list of guess parameters for LS curve fit in format compatible with _2nd_deriv_sum function"""
        # We are estimating the A of the original gaussian based on the y-coordinate of the local minimum, which is roughly
        # at the depth of the central peak of the 2nd derivative of the gaussian.
        # Therefore, A ≈ -(y(local min)) * sigma^2
        
        # convert everything into numpy arrays for easier math operations and to avoid issues with pandas indexing
        local_min_ys = np.asarray(local_min_ys)
        left_intercepts = np.asarray(left_intercepts)
        right_intercepts = np.asarray(right_intercepts)
        
        sigmas = (right_intercepts - left_intercepts) / 2
        As = -local_min_ys * (sigmas**2)
        mus = local_min_xs
        
        return [param for sublist in zip(As, sigmas, mus) for param in sublist]
        
    def _local_min(self):
            """Helper function representing the total nubmer of local minima in the plotted graph,
            as well as an array of colors corresponding to datapoints (blue for regular, green for fitted, red for not fitted yet)
            Returns:
                (qty, locations) (tuple)
            """
            y = self.data["Second Derivative"].to_numpy(copy=False)
            minima_mask = (y[1:-1] < y[:-2]) & (y[1:-1] < y[2:]) & (y[1:-1] < 0) # boolean array where minima are True
            # Add column with point types hinting at future recoloring to the df
            self.data["Point Type"] = np.full(len(self.data), self.PointType.REGULAR)
            
            full_minima_mask = np.zeros(len(self.data), dtype=bool) # temporarily fill with False
            full_minima_mask[1:-1] = minima_mask # apply clipped mask to overall mask
            
            self.data.loc[full_minima_mask, "Point Type"] = self.PointType.MIN
            locations = self.data["Wavenumber"].to_numpy(copy=False)[1:-1][minima_mask]
            return len(locations), locations # TODO: potentially get rid of this since there's a dedicated point type column in the df now

    def _get_x_intercepts(self):
        """For every local minimum type point in the working dataframe, crawls the plot both right and left along the x-axis until it finds the 
        nearest x-intercept (linearly interpolated), then adds that point to the dataframe as a new row
        
        Returns:
            x_intercepts (pd.Series): pandas series of all x-intercept points found in the working dataframe"""
        
        # In practice it's more efficient to compile these x-intercepts into a Python list and then append it to the df in one go.

        sorted_df = self.data.sort_values(by="Wavenumber") # sort by x-axis for merge_asof to work properly

        # This is going to be the right df in merge_asof
        positive_derivs = self.data.loc[self.data["Second Derivative"].gt(0)].sort_values(by="Wavenumber")
        positive_derivs = positive_derivs[["Wavenumber", "Second Derivative"]]
        positive_derivs = positive_derivs.rename(columns={"Wavenumber": "Wavenumber_pos_pt", "Second Derivative": "Second Derivative_pos_pt"}) # this ensure left wn column doesn't get merged with the right wn column in the next step
        # Left df in merge_asof
        local_minima = sorted_df.loc[sorted_df["Point Type"].eq(self.PointType.MIN)]
        #print("LOCAL MINIMA <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
        #print(local_minima)
        
        # TODO NEW IMPLEMENTATION
        # nearest positive points that are to the left of each local min
        left_pos = pd.merge_asof(local_minima, positive_derivs, left_on="Wavenumber", right_on="Wavenumber_pos_pt", direction="backward")
        left_pos = left_pos[["Wavenumber_pos_pt", "Second Derivative_pos_pt"]]
        #print("LEFT POSITIVE <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
        #print(left_pos)
        right_pos = pd.merge_asof(local_minima, positive_derivs, left_on="Wavenumber", right_on="Wavenumber_pos_pt", direction="forward")
        right_pos = right_pos[["Wavenumber_pos_pt", "Second Derivative_pos_pt"]]
        # Now find the other points that we're using to interpolate for x-intercepts
        # Find a way to remove these positive points from the df being merged so that we don't get the same point as the nearest
        
        left_interp_anchors = pd.merge_asof(left_pos, sorted_df,
                                            left_on="Wavenumber_pos_pt",
                                            right_on="Wavenumber",
                                            direction="forward",
                                            allow_exact_matches=False)
        left_interp_anchors = left_interp_anchors[["Wavenumber", "Second Derivative"]]
        #print("LEFT INTERP ANCHORS <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<")
        #print(left_interp_anchors)
        right_interp_anchors = pd.merge_asof(right_pos, sorted_df,
                                             left_on="Wavenumber_pos_pt",
                                             right_on="Wavenumber",
                                             direction="backward",
                                             allow_exact_matches=False)
        right_interp_anchors = right_interp_anchors[["Wavenumber", "Second Derivative"]]
        
        # Combine positive points and their corresponding interpolation anchors into one df for easier processing
        x1 = pd.concat([left_pos["Wavenumber_pos_pt"], right_pos["Wavenumber_pos_pt"]], ignore_index=True)
        left_x1 = left_pos["Wavenumber_pos_pt"]
        right_x1 = right_pos["Wavenumber_pos_pt"]
        
        x2 = pd.concat([left_interp_anchors["Wavenumber"], right_interp_anchors["Wavenumber"]], ignore_index=True)
        left_x2 = left_interp_anchors["Wavenumber"]
        right_x2 = right_interp_anchors["Wavenumber"]
        
        y1 = pd.concat([left_pos["Second Derivative_pos_pt"], right_pos["Second Derivative_pos_pt"]], ignore_index=True)
        left_y1 = left_pos["Second Derivative_pos_pt"]
        right_y1 = right_pos["Second Derivative_pos_pt"]
        
        y2 = pd.concat([left_interp_anchors["Second Derivative"], right_interp_anchors["Second Derivative"]], ignore_index=True)
        left_y2 = left_interp_anchors["Second Derivative"]
        right_y2 = right_interp_anchors["Second Derivative"]        
        # END NEW IMPLEMENTATION

        # Interpolation
        # Find the x intercept using the line equation
        left_x_intercepts = -(left_y1 * (left_x2 - left_x1) / (left_y2 - left_y1)) + left_x1
        right_x_intercepts = -(right_y1 * (right_x2 - right_x1) / (right_y2 - right_y1)) + right_x1

        return (left_x_intercepts, right_x_intercepts)

class GraphEditor(QWidget):
    """Main widget Displays technical replicate FTIR and allows to fit gaussians to them"""
    def __init__(self, files: list, *args, **kwargs):
        super().__init__(*args, **kwargs)
        v_layout = QVBoxLayout()
        self.setLayout(v_layout)
        self.file_list = files # List of paths
        self.plot_objs = list(map(lambda f: PlotData(filepath=f), self.file_list))
        self.active_file = 0 # Changes when another technical replicate is selected        
        self.active_plot = None # TODO currently active DataFrame that can be modified from the fitter slot
        self.lin_region = pg.LinearRegionItem() # used to select plot areas for gaussian fitting
        
        # Create a list view of files at the top
        file_list_disp = QListView()
        clipped_paths = list(map(lambda f: f.split("/")[-1], self.file_list))
        model = ListViewModel(data_list=clipped_paths)
        file_list_disp.setModel(model)
        v_layout.addWidget(file_list_disp)
        
        # Counter showing gaussian fitting progress (shows how many negative peaks have been accounted for)
        self.gaus_counter = QLabel()
        v_layout.addWidget(self.gaus_counter)
        
        # Button to fit gaussian peaks to processed 2nd derivative plot
        fit_btn = QPushButton("Fit curve")
        fit_btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        fit_btn.pressed.connect(self.fit_gaussian)
        v_layout.addWidget(fit_btn)
        
        # Main plot control area for fitting gaussians
        file_list_disp.selectionModel().currentChanged.connect(self.change_active_plot)
        self.graphics_view = pg.GraphicsView()
        v_layout.addWidget(self.graphics_view)

        self.plot_item = pg.PlotItem()
        self.plot_item.invertX()
        self.plot_item.addItem(self.lin_region)
        self.plot_item.addLine(y=0, movable=False) # show x-axis
        self.graphics_view.setCentralItem(self.plot_item)
        
        # Used to color-code points on the plot based on fitting status
        self._brushes = np.asarray(
            [pg.mkBrush("#003A91"),
            pg.mkBrush("#FFAD31"),
            pg.mkBrush("#FFFF00")])
        
        # This is what gets displayed in the output box on the right side of the splitter in main.py
        self.integral_data = [replicate.integrated_areas for replicate in self.plot_objs]
        
    @Slot()
    def fit_gaussian(self):
        """Fits gaussian curve to the plot within the selected linear region via the least-squares method
        The idea is that """
        # Retrieve current bounds of the selection region
        sel_region = self.lin_region.getRegion()
        self._min_in_bounds(lower=sel_region[0], upper=sel_region[1])
        
        # TODO retrieve points of interest from 2nd derivative plot
        pass
             
    def _min_in_bounds(self, lower, upper):
        """Returns true if and only if there is exactly one unfitted local minimum within the provided range"""
        print(f"from {lower} to {upper}")
        
        min_pts = self.plot_objs[self.active_file].local_min_xs # numpy array of local minima locations
        
        if np.count_nonzero(((min_pts > lower) & (min_pts < upper))) == 1:
            print("True")
            return True
        print("False")
        return False
        
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
        active_obj = self.plot_objs[active_index]
        
        df = active_obj.data
        x = df["Wavenumber"].to_numpy(copy=False)
        y = df["Second Derivative"].to_numpy(copy=False)
        colors = self._brushes[df["Point Type"]]
        
        self.plot_item.removeItem(self.active_plot)
        self.plot_item.removeItem(self.fitted_curve) if hasattr(self, "fitted_curve") else None
        
        self.active_plot = self.plot_item.plot(
                            x,
                            y,
                            symbolBrush=colors,
                            symbol='d',
                            symbolSize=5,
                        )
        
        fitted_func = active_obj.fitted_2nd_deriv
        # Construct a smooth fitted curve to display on this plot
        curve_x = np.linspace(min(x), max(x), 1000)
        curve_y = fitted_func(curve_x)
        self.fitted_curve = self.plot_item.plot(curve_x, curve_y, pen=pg.mkPen(color="#C800FF", width=0.5))
                
        self.lin_region.setRegion((min(x), min(x) + np.ptp(x) / 10))
        self.lin_region.setBounds((min(x), max(x)))
            
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
        self.selected_files = []
        
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
            
    def get_output(self):
        """ 
        Returns the outputs of all files in the graph editor as a string, which can be displayed in a QTextEdit widget
        """
        raw_csvs = ""
        cumul_df = pd.DataFrame()
        if self.count() > 1: # If the graph editor has been added to the stack
            for replicate in self.widget(1).plot_objs:
                raw_csvs += f"File {replicate.filepath}:\n {replicate.integrated_areas.to_csv(index=False)}\n\n"
                #print(replicate.sec_struct_ratios)
                cumul_df = pd.concat([cumul_df, replicate.sec_struct_ratios], ignore_index=False)

        processed_df = cumul_df.groupby(level=0).mean()
        processed_df["SEM"] = cumul_df.groupby(level=0).sem()["Fraction"]
        
        string_output = f"{processed_df.to_csv()}\n\n{raw_csvs}"
        return string_output
                
                
        
        
        
