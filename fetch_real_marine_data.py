```python
"""
Fetch REAL marine + weather data for all Veraval coastal nodes
using Open-Meteo Marine and Weather APIs.

Input:
    veraval_marine_nodes.csv

Output:
    data/veraval_nodes_REAL_data_<timestamp>.csv

No API key required.
"""

import time
import requests
import pandas as pd
import datetime
import os


# ============================================================
# API URLs
# ============================================================

MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"


# ============================================================
# Settings
# ============================================================

BATCH_SIZE = 50
SLEEP_BETWEEN_BATCHES = 1


# ============================================================
# Fetch data for a batch of coordinates
# ============================================================

def fetch_batch(lat_list, lon_list):

    lat_str = ",".join(map(str, lat_list))
    lon_str = ",".join(map(str, lon_list))

    # ---------------- Marine API ----------------

    marine_params = {
        "latitude": lat_str,
        "longitude": lon_str,
        "current": (
            "wave_height,wave_direction,wave_period,"
            "swell_wave_height,swell_wave_direction,swell_wave_period,"
            "ocean_current_velocity,ocean_current_direction,"
            "sea_surface_temperature"
        ),
        "timezone": "Asia/Kolkata",
    }

    # ---------------- Weather API ----------------

    weather_params = {
        "latitude": lat_str,
        "longitude": lon_str,
        "current": (
            "wind_speed_10m,"
            "wind_direction_10m,"
            "precipitation"
        ),
        "wind_speed_unit": "kmh",
        "timezone": "Asia/Kolkata",
    }

    # Request marine data
    marine_response = requests.get(
        MARINE_URL,
        params=marine_params,
        timeout=30
    )

    marine_response.raise_for_status()
    marine_data = marine_response.json()

    # Request weather data
    weather_response = requests.get(
        WEATHER_URL,
        params=weather_params,
        timeout=30
    )

    weather_response.raise_for_status()
    weather_data = weather_response.json()

    # Multiple coordinates return a list
    marine_list = (
        marine_data
        if isinstance(marine_data, list)
        else [marine_data]
    )

    weather_list = (
        weather_data
        if isinstance(weather_data, list)
        else [weather_data]
    )

    return marine_list, weather_list


# ============================================================
# Safety / hazard rule
# ============================================================

def safe_to_venture(wave_h, wind_kmph):

    if wave_h is None or wind_kmph is None:
        return None, "Data unavailable"

    if wave_h > 2.5 or wind_kmph > 45:
        return False, "High wave/wind"

    return True, "No hazard"


# ============================================================
# Main function
# ============================================================

def main(
    input_csv="veraval_marine_nodes.csv",
    output_csv="veraval_nodes_REAL_data.csv"
):

    # --------------------------------------------------------
    # Read the 140 Veraval nodes
    # --------------------------------------------------------

    print(f"Reading nodes from: {input_csv}")

    nodes = pd.read_csv(input_csv)

    # --------------------------------------------------------
    # Check required columns
    # --------------------------------------------------------

    required_columns = [
        "node_id",
        "latitude",
        "longitude",
        "district",
        "zone_type"
    ]

    missing_columns = [
        col for col in required_columns
        if col not in nodes.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing columns in {input_csv}: {missing_columns}"
        )

    nodes = nodes[required_columns].copy()

    print(f"Total nodes found: {len(nodes)}")

    # --------------------------------------------------------
    # Store results
    # --------------------------------------------------------

    results = []

    # --------------------------------------------------------
    # Process nodes in batches
    # 140 nodes = 50 + 50 + 40
    # --------------------------------------------------------

    for i in range(0, len(nodes), BATCH_SIZE):

        chunk = nodes.iloc[i:i + BATCH_SIZE]

        print(
            f"\nFetching nodes "
            f"{i + 1} to {min(i + BATCH_SIZE, len(nodes))} "
            f"of {len(nodes)}..."
        )

        marine_list, weather_list = fetch_batch(
            chunk["latitude"].tolist(),
            chunk["longitude"].tolist()
        )

        # ----------------------------------------------------
        # Combine node information + API data
        # ----------------------------------------------------

        for row, marine, weather in zip(
            chunk.itertuples(index=False),
            marine_list,
            weather_list
        ):

            marine_current = marine.get("current", {}) or {}
            weather_current = weather.get("current", {}) or {}

            wave_height = marine_current.get("wave_height")
            wind_speed = weather_current.get("wind_speed_10m")

            safe, hazard = safe_to_venture(
                wave_height,
                wind_speed
            )

            results.append({

                "node_id": row.node_id,

                "latitude": row.latitude,

                "longitude": row.longitude,

                "district": row.district,

                "zone_type": row.zone_type,

                "observation_time":
                    marine_current.get("time"),

                "wave_height_m":
                    wave_height,

                "wave_direction_deg":
                    marine_current.get("wave_direction"),

                "wave_period_s":
                    marine_current.get("wave_period"),

                "swell_wave_height_m":
                    marine_current.get("swell_wave_height"),

                "swell_wave_direction_deg":
                    marine_current.get("swell_wave_direction"),

                "swell_wave_period_s":
                    marine_current.get("swell_wave_period"),

                "ocean_current_velocity_kmh":
                    marine_current.get(
                        "ocean_current_velocity"
                    ),

                "ocean_current_direction_deg":
                    marine_current.get(
                        "ocean_current_direction"
                    ),

                "sst_celsius":
                    marine_current.get(
                        "sea_surface_temperature"
                    ),

                "wind_speed_kmph":
                    wind_speed,

                "wind_direction_deg":
                    weather_current.get(
                        "wind_direction_10m"
                    ),

                "precipitation_mm":
                    weather_current.get(
                        "precipitation"
                    ),

                "safe_to_venture":
                    safe,

                "hazard_type":
                    hazard,
            })

        print(
            f"Completed "
            f"{min(i + BATCH_SIZE, len(nodes))}/{len(nodes)} nodes."
        )

        time.sleep(SLEEP_BETWEEN_BATCHES)

    # ========================================================
    # Create final DataFrame
    # ========================================================

    real_df = pd.DataFrame(results)

    # --------------------------------------------------------
    # Save CSV
    # --------------------------------------------------------

    real_df.to_csv(
        output_csv,
        index=False
    )

    print("\n==========================================")
    print("DATA COLLECTION COMPLETED")
    print("==========================================")

    print(f"Nodes requested : {len(nodes)}")
    print(f"Rows collected  : {len(real_df)}")
    print(f"Output file     : {output_csv}")

    print("\nFirst 5 rows:")
    print(real_df.head())


# ============================================================
# Run
# ============================================================

if __name__ == "__main__":

    os.makedirs("data", exist_ok=True)

    timestamp = datetime.datetime.now().strftime(
        "%Y%m%d_%H%M"
    )

    output_file = (
        f"data/veraval_nodes_REAL_data_{timestamp}.csv"
    )

    main(
        input_csv="veraval_marine_nodes.csv",
        output_csv=output_file
    )
```
