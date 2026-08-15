import pandas as pd
import os
import matplotlib.pyplot as plt
import numpy as np
from pybaselines import Baseline
from scipy.signal import savgol_filter
from scipy.optimize import curve_fit

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
            file_df["Smooth Abs"] = sav_filt_2
            
            dfs.append(file_df)
        except:
            raise RuntimeError(f"Failed to read/parse {file}")
    try:
        return pd.concat(dfs).groupby('Wavenumber').mean()
    except:
        raise RuntimeError(f"Failed to average provided files")
    
def gaus_f(x, amp, mu, sig):
    """
        Calculates value of f(x), where f is the function of a gaussian curve guessed based on passed params
        
        Args:
            x (float or int): input variable
            amp (float or int): amplitude
            mu (float or int): mean or expected value, which is the center of the peak
            sig (float or int): standard deviation, which controls the width of the peak
    """
    return amp*np.exp(-(x-mu)**2/sig**2)
        
if __name__ == "__main__":
    working_df = avg_dfs(map(lambda f: f"./Data/{f}", os.listdir("./Data/")))
    plt.plot(working_df.index, working_df['Smooth Abs'])

    plt.plot([1590, 1700], [0.0, 0.0], linestyle = 'dotted')

    plt.gca().invert_xaxis()
    plt.show()
        
