import pandas as pd
import os

master_file = "data/veraval_master_data.csv"
new_file = "data/new_data.csv"

# Read existing master
if os.path.exists(master_file):
    master = pd.read_csv(master_file)
else:
    master = pd.DataFrame()

# Read newly fetched data
new_data = pd.read_csv(new_file)

# Add new data
master = pd.concat([master, new_data], ignore_index=True)

# Remove duplicate records
master.drop_duplicates(inplace=True)

# Save updated master
master.to_csv(master_file, index=False)

print("Master dataset updated!")
print("Total records:", len(master))
