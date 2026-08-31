# SPDX-License-Identifier: MIT

import os
from dataclasses import dataclass

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np
import pandas as pd
from pybaselines import Baseline
from scipy.optimize import curve_fit
from scipy.signal import savgol_filter

def tech_df(file, plot_range=[1700, 1590]):
    """Returns a df of smoothed 2nd derivative values based on provided plot range and single FTIR technical replicate file"""
    # Check range validity and reset to default if invalid range provided
    if (not isinstance(plot_range, list) or len(plot_range) != 2 or not isinstance(plot_range[0], (int, float)) or not isinstance(plot_range[1], (int, float))):
        plot_range = [1700, 1590]
    try:
        file_df = pd.read_csv(file, sep="\t", names=["Wavenumber","Abs"])
        # Select plot region
        mask = ((file_df["Wavenumber"] <= max(plot_range)) & (file_df["Wavenumber"] >= min(plot_range)))
        file_df = file_df.loc[mask]
        
        # Correct baseline
        x = file_df["Wavenumber"].values
        y = file_df["Abs"].values
        corr_y, params = Baseline(x).asls(data=y)
        file_df["Corrected Abs"] = file_df["Abs"] - corr_y
        
        # Apply Savitsky-Golay filter
        abs_to_smooth = "Corrected Abs" if ("Corrected Abs" in file_df.columns.tolist()) else "Abs"
            
        sav_filt_2 = savgol_filter(file_df[abs_to_smooth], window_length=9, polyorder=6, deriv=2)
        file_df["Second Derivative"] = sav_filt_2
        
        return file_df
    except:
        print(f"Failed to read/parse {file}")
        return None
    

# TODO: refactor this for a design based on interacting with individial replicates until the very final output
def avg_dfs(files):
    """
    Returns a single pandas dataframe representing averaged plot data for provided files
    
    Args:
        files (list): path strings of all files to be averaged
    """
    dfs = []
    for file in files:
        try:
            file_df = pd.read_csv(file, sep="\t", names=["Wavenumber","Abs"])
            # Select Amide I region
            mask = ((file_df["Wavenumber"] <= 1700) & (file_df["Wavenumber"] >= 1590))
            file_df = file_df.loc[mask]

            # Correct baseline
            x = file_df["Wavenumber"].values
            y = file_df["Abs"].values
            corr_y, params = Baseline(x).asls(data=y)
            file_df["Corrected Abs"] = file_df["Abs"] - corr_y
            
            # Apply Savitsky-Golay filter
            abs_to_smooth = "Corrected Abs" if ("Corrected Abs" in file_df.columns.tolist()) else "Abs"
                
            sav_filt_2 = savgol_filter(file_df[abs_to_smooth], window_length=9, polyorder=6, deriv=2)
            file_df["Second Derivative"] = sav_filt_2
            
            dfs.append(file_df)
        except:
            raise RuntimeError(f"Failed to read/parse {file}")
    try:
        return pd.concat(dfs).groupby('Wavenumber').mean()
    except:
        raise RuntimeError(f"Failed to average provided files")


@dataclass(frozen=True)
class GaussianPeak:
    """Parameters resulting from a local Gaussian fit."""

    amplitude: float
    center: float
    sigma: float

    def evaluate(self, x):
        """
        Args:
            x (np.array): array of x datapoints for which to calculate gaussian y-vals
        Returns:
            an ```np.array``` of length equal to x with corresponding y-vals
        """
        x = np.asarray(x)
        return self.amplitude * np.exp(
            -0.5 * ((x - self.center) / self.sigma) ** 2
        )

    @property
    def area(self):
        """Return this derivative Gaussian's area, not an absorbance-band area."""
        return abs(self.amplitude * self.sigma * np.sqrt(2 * np.pi))


def fit_gaussian(x, y, guess=None):
    """
    Fits a negative Gaussian to the supplied peak data

    Args:
        x (array-like): wavenumber values for the selected peak
        y (array-like): second-derivative values for the selected peak
        guess (tuple, optional): initial amplitude, center, and sigma values

    Returns:
        tuple: fitted GaussianPeak and parameter covariance matrix
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)

    center_index = np.argmin(y) # local min
    auto_guess = (
        y[center_index], # amp
        x[center_index], # mu
        np.ptp(x) / 6, # sigma
    )

    parameters, covariance = curve_fit(
        lambda x, amplitude, center, sigma: GaussianPeak(
            amplitude, center, sigma
        ).evaluate(x),
        x,
        y,
        p0=(guess if guess else auto_guess),
        bounds=(
            [-np.inf, np.min(x), np.finfo(float).eps],
            [0, np.max(x), np.inf],
        ),
    )

    peak = GaussianPeak(*parameters)
    return peak, covariance

if __name__ == "__main__":
    working_df = avg_dfs(map(lambda f: f"./Data/{f}", os.listdir("./Data/")))

    fig, ax = plt.subplots()

    wavenumber = working_df.index.to_numpy()
    second_derivative = working_df["Second Derivative"].to_numpy()
    ax.plot(wavenumber, second_derivative, label="Average second derivative")
    ax.xaxis.set_minor_locator(ticker.MultipleLocator(1))
    ax.plot([1590, 1700], [0.0, 0.0], linestyle = 'dotted')
    ax.invert_xaxis()

    plt.show()
