import pandas as pd
import numpy as np

# Read the data from the Excel file
dirtyData = pd.read_excel("Copy of CPET_DM01__Max Breath by Breath_class.xlsx")

def remove_far_away_values(df, column_name = "V'O2", n=3):
    """
    Removes values that are too far from the mean of the previous `n` values in the specified column.
    
    :param df: pandas DataFrame containing the data
    :param column_name: name of the column to process
    :param n: number of previous values to compare against
    :return: DataFrame with outliers removed
    """
    for i in range(n, len(df)):
        current_value = df.loc[i, column_name]
        previous_values = df.loc[i-n:i-1, column_name].values
        mean_previous = np.mean(previous_values)
        std_dev_previous = np.std(previous_values)
        
        # If the current value is more than 2 standard deviations away from the mean of the previous values
        if abs(current_value - mean_previous) > 2 * std_dev_previous:
            df.at[i, column_name] = None  # or any other method to handle this
    
    return df

# Apply the function to remove outliers in the 'V'O2' column
cleanData = remove_far_away_values(dirtyData, "V'O2")

pd.set_option("display.max_rows", 30)
pd.set_option("display.max_columns", 10)
print(cleanData)