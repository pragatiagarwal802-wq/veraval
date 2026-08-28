"""
Fetch REAL marine + weather data for Veraval coastal nodes using Open-Meteo APIs.
No API key needed. Free for non-commercial use.

Sources:
- Marine API   -> wave height, wave direction, sea surface temperature
- Weather API  -> wind speed, wind direction, precipitation

Output schema matches the mock Excel (veraval_nodes_live_data_full_csv.xlsx)
so it can be swapped in directly wherever the mock data was being used.

Install once:  pip install requests pandas openpyxl
"""

import time
import requests
import pandas as pd

MARINE_URL = "https://marine-api.open-meteo.com/v1/marine"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

BATCH_SIZE = 50          # Open-Meteo supports batching many coords in one call
SLEEP_BETWEEN_BATCHES = 1  # seconds, be polite to the free tier


def fetch_batch(lat_list, lon_list):
    """One API call per batch, for ALL coordinates in that batch at once."""
    lat_str = ",".join(map(str, lat_list))
    lon_str = ",".join(map(str, lon_list))

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
    weather_params = {
        "latitude": lat_str,
        "longitude": lon_str,
        "current": "wind_speed_10m,wind_direction_10m,precipitation",
        "wind_speed_unit": "kmh",
        "timezone": "Asia/Kolkata",
    }

    marine_resp = requests.get(MARINE_URL, params=marine_params, timeout=30).json()
    weather_resp = requests.get(WEATHER_URL, params=weather_params, timeout=30).json()

    # When multiple coordinates are sent, Open-Meteo returns a LIST of results
    # (one dict per coordinate, in the same order you sent them).
    marine_list = marine_resp if isinstance(marine_resp, list) else [marine_resp]
    weather_list = weather_resp if isinstance(weather_resp, list) else [weather_resp]
    return marine_list, weather_list


def safe_to_venture(wave_h, wind_kmph):
    """
    Placeholder safety rule — replace with real INCOIS/IMD advisory thresholds
    once you have them. This is just so the pipeline has SOMETHING to reason over.

    NOTE: we return "No hazard" instead of "None" on purpose — pandas' read_csv
    silently converts the literal string "None" into NaN on read-back, which makes
    it look like data is missing when it isn't.
    """
    if wave_h is None or wind_kmph is None:
        return None, "Data unavailable"
    if wave_h > 2.5 or wind_kmph > 45:
        return False, "High wave/wind"
    return True, "No hazard"


def main(input_excel="veraval_nodes_live_data_full_csv.xlsx",
         output_csv="veraval_nodes_REAL_data.csv"):

    nodes = pd.read_excel(input_excel)[
        ["node_id", "latitude", "longitude", "district", "zone_type"]
    ]

    results = []
    for i in range(0, len(nodes), BATCH_SIZE):
        chunk = nodes.iloc[i:i + BATCH_SIZE]
        marine_list, weather_list = fetch_batch(
            chunk["latitude"].tolist(), chunk["longitude"].tolist()
        )

        for row, m, w in zip(chunk.itertuples(), marine_list, weather_list):
            m_cur = m.get("current", {}) or {}
            w_cur = w.get("current", {}) or {}

            wave_h = m_cur.get("wave_height")
            wind_speed = w_cur.get("wind_speed_10m")
            safe, hazard = safe_to_venture(wave_h, wind_speed)

            results.append({
                "node_id": row.node_id,
                "latitude": row.latitude,
                "longitude": row.longitude,
                "district": row.district,
                "zone_type": row.zone_type,
                "observation_time": m_cur.get("time"),  # proves this is real, timestamped data
                "wave_height_m": wave_h,
                "wave_direction_deg": m_cur.get("wave_direction"),
                "wave_period_s": m_cur.get("wave_period"),
                "swell_wave_height_m": m_cur.get("swell_wave_height"),
                "swell_wave_direction_deg": m_cur.get("swell_wave_direction"),
                "swell_wave_period_s": m_cur.get("swell_wave_period"),
                "ocean_current_velocity_kmh": m_cur.get("ocean_current_velocity"),
                "ocean_current_direction_deg": m_cur.get("ocean_current_direction"),
                "sst_celsius": m_cur.get("sea_surface_temperature"),
                "wind_speed_kmph": wind_speed,
                "wind_direction_deg": w_cur.get("wind_direction_10m"),
                "precipitation_mm": w_cur.get("precipitation"),
                "safe_to_venture": safe,
                "hazard_type": hazard,
            })

        print(f"Fetched {min(i + BATCH_SIZE, len(nodes))}/{len(nodes)} nodes...")
        time.sleep(SLEEP_BETWEEN_BATCHES)

    real_df = pd.DataFrame(results)
    real_df.to_csv(output_csv, index=False)
    print(f"\nSaved real data to {output_csv}")
    print(real_df.head())


if __name__ == "__main__":
    if __name__ == "__main__":
    import datetime
    import os

    os.makedirs("data", exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")
    main(output_csv=f"data/veraval_nodes_REAL_data_{timestamp}.csv")
