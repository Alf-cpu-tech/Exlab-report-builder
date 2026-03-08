##pip install pandas openpyxl
import pandas as pd

db = pd.read_excel("Copy of CPET_DM01__Max Breath by Breath_class.xlsx")
print(db)

# t  Phase Marker  V'O2  V'O2/kg  ...  RER    V'E   VT    BF   METS

#output 
#               t     Phase  Marker      V'O2  ...         V'E        VT         BF      METS
#0    0:03:00.200  Exercise     NaN  1.649330  ...   44.202120  2.874000  15.380000  4.133659
#1    0:03:03.360  Exercise     NaN  1.374482  ...   33.993180  1.791000  18.980000  3.444818
#2    0:03:06.260  Exercise     NaN  1.415027  ...   35.052600  1.695000  20.680000  3.546434
#3    0:03:09.880  Exercise     NaN  1.299791  ...   33.487970  2.021000  16.570000  3.257621
#4    0:03:13.300  Exercise     NaN  1.324150  ...   33.817120  1.928000  17.540000  3.318672