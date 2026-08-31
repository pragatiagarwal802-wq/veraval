"""
Fetch live weather alerts from IMD's official CAP feed, filtered to only
alerts relevant to our Veraval/Gir Somnath operational area — not all of India.

This is a SEPARATE, standalone pipeline from fetch_real_marine_data.py —
runs on its own schedule, writes its own output file.

Install: pip install requests xmltodict pandas
"""

import datetime
import os
import requests
import xmltodict
import pandas as pd

CAP_FEED_URL = "https://cap-sources.s3.amazonaws.com/in-imd-en/rss.xml"

RELEVANT_KEYWORDS = [
    "gujarat", "saurashtra", "gir somnath", "junagadh",
    "porbandar", "veraval", "somnath", "kathiawar",
    "west coast", "arabian sea",
]


def is_relevant(text):
    if not text:
        return False
    text_lower = text.lower()
    return any(kw in text_lower for kw in RELEVANT_KEYWORDS)


def fetch_imd_alerts():
    resp = requests.get(CAP_FEED_URL, timeout=20)
    data = xmltodict.parse(resp.content)

    items = data["rss"]["channel"]["item"]
    if isinstance(items, dict):
        items = [items]

    all_alerts = []
    for item in items:
        title = item.get("title", "")
        description = item.get("description", "")
        all_alerts.append({
            "title": title,
            "description": description,
            "published": item.get("pubDate"),
            "detail_url": item.get("link"),
            "relevant_to_veraval": is_relevant(title) or is_relevant(description),
        })

    return pd.DataFrame(all_alerts)


def main(output_dir="imd_alerts"):
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M")

    df = fetch_imd_alerts()
    relevant = df[df["relevant_to_veraval"]]

    print(f"Total alerts in feed: {len(df)}")
    print(f"Relevant to Veraval/Gujarat coast: {len(relevant)}")
    print(relevant[["title", "published"]] if len(relevant) else "No active alerts for this region right now.")

    df.to_csv(f"{output_dir}/imd_alerts_all_{timestamp}.csv", index=False)
    relevant.to_csv(f"{output_dir}/imd_alerts_veraval_{timestamp}.csv", index=False)
    print(f"\nSaved to {output_dir}/")


if __name__ == "__main__":
    main()
