"""
Veraval Chlorophyll — Daily Incremental Fetch (for GitHub Actions)
=====================================================================
Fetches the LATEST available day's chlorophyll for all 140 nodes and
appends it to a growing history CSV. Safe to run daily via cron -- won't
create duplicate rows if a date is already recorded.

Requires two environment variables (set as GitHub Secrets):
  COPERNICUSMARINE_SERVICE_USERNAME
  COPERNICUSMARINE_SERVICE_PASSWORD

Expects a committed file in the repo: veraval_marine_nodes.csv
  (columns: node_id, latitude, longitude)
"""

import os
import copernicusmarine
import pandas as pd
import xarray as xr
import numpy as np
from datetime import date, timedelta

NODES_PATH = "veraval_marine_nodes.csv"
HISTORY_PATH = "veraval_chlorophyll_history.csv"
LOOKBACK_DAYS = 6   # how far back to search for the freshest available day

# ---------------------------------------------------------------------------
# 1. LOAD NODES
# ---------------------------------------------------------------------------
nodes = pd.read_csv(NODES_PATH).drop_duplicates('node_id')[['node_id', 'latitude', 'longitude']]

lat_min, lat_max = nodes['latitude'].min() - 0.1, nodes['latitude'].max() + 0.1
lon_min, lon_max = nodes['longitude'].min() - 0.1, nodes['longitude'].max() + 0.1

today = date.today()
start_date = (today - timedelta(days=LOOKBACK_DAYS)).strftime('%Y-%m-%d')
end_date = today.strftime('%Y-%m-%d')

print(f"Nodes: {len(nodes)}")
print(f"Searching window: {start_date} to {end_date} for the freshest available day")

# ---------------------------------------------------------------------------
# 2. DOWNLOAD A SHORT RECENT WINDOW (handles NRT publishing lag)
# ---------------------------------------------------------------------------
copernicusmarine.subset(
    dataset_id="cmems_obs-oc_glo_bgc-plankton_nrt_l4-gapfree-multi-4km_P1D",
    variables=["CHL"],
    minimum_longitude=lon_min, maximum_longitude=lon_max,
    minimum_latitude=lat_min, maximum_latitude=lat_max,
    start_datetime=f"{start_date}T00:00:00",
    end_datetime=f"{end_date}T23:59:59",
    output_directory=".",
    output_filename="chl_latest_raw.nc",
    overwrite=True,
    username=os.environ["COPERNICUSMARINE_SERVICE_USERNAME"],
    password=os.environ["COPERNICUSMARINE_SERVICE_PASSWORD"],
)

ds = xr.open_dataset("chl_latest_raw.nc")

# ---------------------------------------------------------------------------
# 3. PICK THE MOST RECENT DATE THAT ACTUALLY HAS DATA
# ---------------------------------------------------------------------------
available_dates = pd.to_datetime(ds['time'].values)
chosen_date = None
for d in sorted(available_dates, reverse=True):
    if not bool(ds['CHL'].sel(time=d).isnull().all()):
        chosen_date = d
        break

if chosen_date is None:
    print("No fresh chlorophyll data available in this window -- skipping today's run.")
    raise SystemExit(0)   # exit cleanly, not as a failure -- this can happen legitimately

chosen_date_str = chosen_date.strftime('%Y-%m-%d')
print(f"Using {chosen_date_str} as today's chlorophyll date.")

# ---------------------------------------------------------------------------
# 4. CHECK IF THIS DATE IS ALREADY IN THE HISTORY (avoid duplicate runs)
# ---------------------------------------------------------------------------
if os.path.exists(HISTORY_PATH):
    history = pd.read_csv(HISTORY_PATH)
    if chosen_date_str in history['observation_date'].astype(str).values:
        print(f"{chosen_date_str} is already recorded -- nothing new to add.")
        raise SystemExit(0)
else:
    history = pd.DataFrame(columns=['node_id', 'observation_date', 'chlorophyll_mg_m3'])

# ---------------------------------------------------------------------------
# 5. MATCH EACH NODE TO THE NEAREST GRID CELL FOR THIS DATE
# ---------------------------------------------------------------------------
new_rows = []
for _, node in nodes.iterrows():
    point = ds['CHL'].sel(
        latitude=node['latitude'], longitude=node['longitude'], method='nearest'
    ).sel(time=chosen_date, method='nearest')
    chl_value = float(point.values) if not np.isnan(point.values) else None
    new_rows.append({
        'node_id': node['node_id'],
        'observation_date': chosen_date_str,
        'chlorophyll_mg_m3': chl_value,
    })

new_df = pd.DataFrame(new_rows)

# ---------------------------------------------------------------------------
# 6. APPEND + SAVE
# ---------------------------------------------------------------------------
updated = pd.concat([history, new_df], ignore_index=True)
updated.to_csv(HISTORY_PATH, index=False)

print(f"\nAppended {len(new_df)} rows for {chosen_date_str}.")
print(f"History file now has {len(updated)} total rows across {updated['observation_date'].nunique()} dates.")
