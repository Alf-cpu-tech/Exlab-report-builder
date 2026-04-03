#this file is a copy of the dataParsing file that was made by Kian
import pandas as pd
import numpy as np

dirtyData = pd.read_excel("Copy of CPET_DM01__Max Breath by Breath_class.xlsx")

#the following code was taken from https://www.geeksforgeeks.org/data-analysis/how-to-automate-data-cleaning-in-python/
#im going to try and adapt it for our purposes
def outlier_handling(df, column_with_outliers):
    q1 = df[column_with_outliers].rolling(window=4).quantile(0.25)
    print(q1)
    q3 = df[column_with_outliers].rolling(window=4).quantile(0.75)
    print(q3)
    iqr = q3 - q1
    # remove outliers
    df = df[(df[column_with_outliers] > (q1 - 1.1 * iqr)) 
            & (df[column_with_outliers] < (q3 + 1.1 * iqr))] 
    return df


pd.set_option("display.max_rows", 30)
pd.set_option("display.max_columns", 6)
#calling the function and passing the
cleanData = outlier_handling(dirtyData, "V'O2")

print(cleanData)