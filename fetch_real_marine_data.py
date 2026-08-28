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
# Fetch marine and weather data
# ============================================================

def fetch_batch(lat_list, lon_list):

    lat_str = ",".join(map(str, lat_list))
    lon_str = ",".join(map(str, lon_list))

    marine_params = {
        "latitude": lat_str,
        "longitude": lon_str,
        "current": (
            "wave_height,"
            "wave_direction,"
            "wave_period,"
            "swell_wave_height,"
            "swell_wave_direction,"
            "swell_wave_period,"
            "ocean_current_velocity,"
            "ocean_current_direction,"
            "sea_surface_temperature"
        ),
        "timezone": "Asia/Kolkata"
    }

    weather_params = {
        "latitude": lat_str,
        "longitude": lon_str,
        "current": (
            "wind_speed_10m,"
            "wind_direction_10m,"
            "precipitation"
        ),
        "wind_speed_unit": "kmh",
        "timezone": "Asia/Kolkata"
    }

    # Marine API request
    marine_response = requests.get(
        MARINE_URL,
        params=marine_params,
        timeout=30
    )

    marine_response.raise_for_status()
    marine_data = marine_response.json()

    # Weather API request
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
# Safety / hazard calculation
# ============================================================

def safe_to_venture(wave_height, wind_speed):

    if wave_height is None or wind_speed is None:
        return None, "Data unavailable"

    if wave_height > 2.5 or wind_speed > 45:
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
    # Read all 140 nodes
    # --------------------------------------------------------

    print(f"Reading nodes from: {input_csv}")

    nodes = pd.read_csv(input_csv)

    # --------------------------------------------------------
    # Required columns
    # --------------------------------------------------------

    required_columns = [
        "node_id",
        "latitude",
        "longitude",
        "district",
        "zone_type"
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in nodes.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing columns in {input_csv}: {missing_columns}"
        )

    nodes = nodes[required_columns].copy()

    # Remove rows with missing coordinates
    nodes = nodes.dropna(
        subset=["latitude", "longitude"]
    )

    print(f"Total nodes found: {len(nodes)}")

    # --------------------------------------------------------
    # Store results
    # --------------------------------------------------------

    results = []

    # --------------------------------------------------------
    # Process nodes in batches
    # --------------------------------------------------------

    for i in range(0, len(nodes), BATCH_SIZE):

        chunk = nodes.iloc[
            i:i + BATCH_SIZE
        ]

        start_node = i + 1
        end_node = min(
            i + BATCH_SIZE,
            len(nodes)
        )

        print(
            f"\nFetching nodes "
            f"{start_node} to {end_node} "
            f"of {len(nodes)}..."
        )

        marine_list, weather_list = fetch_batch(
            chunk["latitude"].tolist(),
            chunk["longitude"].tolist()
        )

        # ----------------------------------------------------
        # Combine node information with API data
        # ----------------------------------------------------

        for row, marine, weather in zip(
            chunk.itertuples(index=False),
            marine_list,
            weather_list
        ):

            marine_current = (
                marine.get("current", {}) or {}
            )

            weather_current = (
                weather.get("current", {}) or {}
            )

            wave_height = marine_current.get(
                "wave_height"
            )

            wind_speed = weather_current.get(
                "wind_speed_10m"
            )

            safe, hazard = safe_to_venture(
                wave_height,
                wind_speed
            )

            results.append({

                "node_id":
                    row.node_id,

                "latitude":
                    row.latitude,

                "longitude":
                    row.longitude,

                "district":
                    row.district,

                "zone_type":
                    row.zone_type,

                "observation_time":
                    marine_current.get("time"),

                "wave_height_m":
                    wave_height,

                "wave_direction_deg":
                    marine_current.get(
                        "wave_direction"
                    ),

                "wave_period_s":
                    marine_current.get(
                        "wave_period"
                    ),

                "swell_wave_height_m":
                    marine_current.get(
                        "swell_wave_height"
                    ),

                "swell_wave_direction_deg":
                    marine_current.get(
                        "swell_wave_direction"
                    ),

                "swell_wave_period_s":
                    marine_current.get(
                        "swell_wave_period"
                    ),

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
                    hazard
            })

        print(
            f"Completed "
            f"{end_node}/{len(nodes)} nodes."
        )

        time.sleep(
            SLEEP_BETWEEN_BATCHES
        )

    # ========================================================
    # Create final DataFrame
    # ========================================================

    real_df = pd.DataFrame(results)

    # ========================================================
    # Save output
    # ========================================================

    real_df.to_csv(
        output_csv,
        index=False
    )

    print("\n==========================================")
    print("DATA COLLECTION COMPLETED")
    print("==========================================")

    print(
        f"Nodes requested : {len(nodes)}"
    )

    print(
        f"Rows collected  : {len(real_df)}"
    )

    print(
        f"Output file     : {output_csv}"
    )

    print("\nFirst 5 rows:")
    print(real_df.head())


# ============================================================
# Run program
# ============================================================

if __name__ == "__main__":

    os.makedirs(
        "data",
        exist_ok=True
    )

    timestamp = datetime.datetime.now().strftime(
        "%Y%m%d_%H%M"
    )

    output_file = (
        f"data/"
        f"veraval_nodes_REAL_data_"
        f"{timestamp}.csv"
    )

    main(
        input_csv="veraval_marine_nodes.csv",
        output_csv=output_file
    )
```
