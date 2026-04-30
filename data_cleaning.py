import pandas as pd
import numpy as np
import os
###this is mostly AI generated with a bunch of promts  based on the previous attempts and files


# Read the data from the Excel file


def replace_far_away_values(df, column_name="V'O2", n=3):
    """
    Replaces values that are too far from the mean of the previous `n` values in the specified column
    with a value interpolated between the closest valid points after smoothing with a moving average.
    
    :param df: pandas DataFrame containing the data
    :param column_name: name of the column to process
    :param n: number of previous values to compare against
    :return: DataFrame with outliers replaced
    """
    # Smooth the data using a moving average
    window_size = 5
    df[column_name] = df[column_name].rolling(window=window_size, min_periods=1).mean()
    
    for i in range(n, len(df)):
        current_value = df.loc[i, column_name]
        previous_values = df.loc[i-n:i-1, column_name].values
        mean_previous = np.mean(previous_values)
        std_dev_previous = np.std(previous_values)
        
        # If the current value is more than 2 standard deviations away from the mean of the previous values
        if abs(current_value - mean_previous) > 2 * std_dev_previous:
            df.at[i, column_name] = np.nan  # First set to NaN to facilitate interpolation
    
    # Interpolate the missing values
    df[column_name].interpolate(method='linear', inplace=True)
    print("cleaning successfull")
    return df

# Apply the function to replace outliers in the 'V'O2' column


if __name__ == "__main__":
    replace_far_away_values(df, "V'O2", n=3)
