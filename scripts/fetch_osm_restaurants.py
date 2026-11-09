"""Fetch OpenStreetMap restaurant listings for districts the Zomato snapshot barely covers.

OSM gives a name, a place type, coordinates, and sometimes a cuisine tag. It has no
rating, no cost for two, and no menu, so those stay null. These rows are kept in their
own table and are never merged into the Zomato restaurants.

Usage: .venv/bin/python scripts/fetch_osm_restaurants.py
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ingestion.canonical import canonicalize_token  # noqa: E402
from map.districts import assign_district, district_records  # noqa: E402

PROCESSED = ROOT / "data" / "processed"
RAW_DIR = ROOT / "data" / "raw" / "osm"
ENDPOINTS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
)
USER_AGENT = "DelhiFoodIndex-university-project"
THIN_BELOW = 20
CAP = 30
AMENITIES = "restaurant|fast_food|cafe"


def main() -> None:
    zomato = pd.read_parquet(PROCESSED / "restaurants.parquet")
    zomato["district"] = assign_district(zomato)
    counts = zomato.groupby("district")["restaurant_id"].nunique()
    records = {record["name"]: record for record in district_records()}
    targets = [name for name in records if int(counts.get(name, 0)) < THIN_BELOW]
    print("Districts below", THIN_BELOW, "Zomato restaurants:", targets, flush=True)

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    found: dict[str, dict] = {}
    for name in targets:
        west, south, east, north = records[name]["geometry"].bounds
        elements = _query(name, (south, west, north, east))
        (RAW_DIR / f"overpass_{name.lower().replace(' ', '_')}.json").write_text(json.dumps(elements))
        for element in elements:
            row = _row(element)
            if row:
                found[row["osm_id"]] = row
        print(f"{name}: {len(elements)} elements in bbox", flush=True)

    table = pd.DataFrame(found.values())
    table["district"] = assign_district(table)
    table = table.dropna(subset=["district"])
    table = table[table["district"].isin(targets)].copy()

    totals = table.groupby("district")["osm_id"].nunique().to_dict()
    chosen = []
    for name in targets:
        part = table[table["district"] == name].copy()
        part["_has_cuisine"] = part["cuisine_raw"].notna()
        part = part.sort_values(["_has_cuisine", "osm_id"], ascending=[False, True]).head(CAP)
        chosen.append(part.drop(columns="_has_cuisine"))
    sample = pd.concat(chosen, ignore_index=True)
    sample["osm_listed_in_district"] = sample["district"].map(totals).astype(int)
    sample["rating"] = pd.NA
    sample["cost_for_two"] = pd.NA
    sample["source"] = "openstreetmap"
    sample.to_parquet(PROCESSED / "osm_restaurants.parquet", index=False)
    print(sample.groupby("district").agg(kept=("osm_id", "count"), listed=("osm_listed_in_district", "first")))
    print("Saved", len(sample), "rows to", PROCESSED / "osm_restaurants.parquet")


def _query(name: str, bbox: tuple[float, float, float, float]) -> list[dict]:
    south, west, north, east = bbox
    text = (
        f'[out:json][timeout:120];nwr["amenity"~"^({AMENITIES})$"]["name"]'
        f"({south:.5f},{west:.5f},{north:.5f},{east:.5f});out center tags;"
    )
    body = urllib.parse.urlencode({"data": text}).encode()
    last: Exception | None = None
    for attempt in range(6):
        endpoint = ENDPOINTS[attempt % len(ENDPOINTS)]
        request = urllib.request.Request(endpoint, data=body, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                return json.load(response)["elements"]
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, KeyError) as error:
            last = error
            print(f"  {name}: attempt {attempt + 1} on {endpoint} failed: {error}", flush=True)
            time.sleep(10)
    raise RuntimeError(f"Overpass failed for {name}: {last}")


def _row(element: dict) -> dict | None:
    tags = element.get("tags", {})
    name = (tags.get("name") or "").strip()
    if not name:
        return None
    lat = element.get("lat") or (element.get("center") or {}).get("lat")
    lon = element.get("lon") or (element.get("center") or {}).get("lon")
    if lat is None or lon is None:
        return None
    cuisine_raw = tags.get("cuisine")
    tokens = []
    for part in str(cuisine_raw or "").split(";"):
        token = canonicalize_token(part)
        if token and token not in tokens:
            tokens.append(token)
    address = ", ".join(
        value
        for value in (
            " ".join(filter(None, [tags.get("addr:housenumber"), tags.get("addr:street")])),
            tags.get("addr:suburb"),
        )
        if value
    )
    return {
        "osm_id": f"{element['type']}/{element['id']}",
        "name": name,
        "amenity": tags.get("amenity"),
        "cuisine_raw": cuisine_raw,
        "canonical_cuisines": " | ".join(tokens) if tokens else None,
        "address": address or None,
        "latitude": float(lat),
        "longitude": float(lon),
        "collected_at": pd.Timestamp.utcnow().strftime("%Y-%m-%d"),
    }


if __name__ == "__main__":
    main()
