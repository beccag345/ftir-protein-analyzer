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


def gaussian(x, amplitude, center, sigma):
    """Evaluate a Gaussian using sigma as its standard deviation."""
    return amplitude * np.exp(-0.5 * ((x - center) / sigma) ** 2)


@dataclass(frozen=True)
class GaussianPeak:
    """Parameters resulting from a local Gaussian fit."""

    amplitude: float
    center: float
    sigma: float

    def evaluate(self, x):
        return gaussian(np.asarray(x), self.amplitude, self.center, self.sigma)

    @property
    def area(self):
        """Return this derivative Gaussian's area, not an absorbance-band area."""
        return abs(self.amplitude * self.sigma * np.sqrt(2 * np.pi))


def fit_gaussian(x, y, guess=None):
    """Fit a negative Gaussian to the supplied peak data."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)

    center_index = np.argmin(y) # local min
    auto_guess = (
        y[center_index], # amp
        x[center_index], # mu
        np.ptp(x) / 6, # sigma
    )

    parameters, covariance = curve_fit(
        gaussian,
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
