import pandas as pd
import glob
import os

# Folder containing the fetched CSV files
DATA_FOLDER = "data"

# Master dataset
MASTER_FILE = os.path.join(DATA_FOLDER, "veraval_master_data.csv")

# Find all CSV files in data folder
all_files = glob.glob(os.path.join(DATA_FOLDER, "*.csv"))

# Remove the master file from the list
data_files = [
    file for file in all_files
    if os.path.abspath(file) != os.path.abspath(MASTER_FILE)
]

print(f"Found {len(data_files)} data files.")

if not data_files:
    print("No data files found.")
    exit()

# Read all existing data files
dataframes = []

for file in data_files:
    try:
        df = pd.read_csv(file)

        # Keep track of where the data came from
        df["source_file"] = os.path.basename(file)

        dataframes.append(df)

        print(
            f"Loaded {os.path.basename(file)} "
            f"({len(df)} rows)"
        )

    except Exception as e:
        print(f"Could not read {file}: {e}")

# Combine everything
master_df = pd.concat(
    dataframes,
    ignore_index=True
)

print("\nBefore removing duplicates:")
print(f"Rows: {len(master_df)}")

# Remove exact duplicate rows
master_df.drop_duplicates(inplace=True)

# Reset index
master_df.reset_index(drop=True, inplace=True)

# Try to find timestamp column
time_columns = [
    "timestamp",
    "time",
    "datetime",
    "date_time",
    "date"
]

time_column = None

for column in time_columns:
    if column in master_df.columns:
        time_column = column
        break

# Sort by timestamp if available
if time_column:

    master_df[time_column] = pd.to_datetime(
        master_df[time_column],
        errors="coerce"
    )

    master_df = master_df.sort_values(
        by=time_column
    )

    print(f"Sorted by: {time_column}")

else:
    print("No timestamp column found.")

# Save master dataset
master_df.to_csv(
    MASTER_FILE,
    index=False
)

print("\n==============================")
print("MASTER DATASET UPDATED")
print("==============================")
print(f"File: {MASTER_FILE}")
print(f"Rows: {len(master_df)}")
print(f"Columns: {len(master_df.columns)}")

# Missing values
print("\nMissing values:")
print(master_df.isnull().sum())
