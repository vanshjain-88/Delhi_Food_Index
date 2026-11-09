"""Phase 1 pilot: three Delhi localities from the Kaggle Zomato menu snapshot.

Downloads the published dataset, keeps Connaught Place, Hauz Khas, and Karol Bagh,
and writes pilot Parquet tables plus a data-quality report. Does not scrape Zomato.
"""

from __future__ import annotations

import json
import os
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT / "src"))

from ingestion.zomato_menu import (  # noqa: E402
    find_lat_lon,
    find_text,
    iter_menu_items,
    normalize_name,
    parse_price,
)

DATASET = "archangel0x01/zomato-india-delivery-menus"
SOURCE_NAME = f"kaggle:{DATASET}"
RAW_DIR = ROOT / "data" / "raw" / "zomato"
PILOT_DIR = ROOT / "data" / "raw" / "pilot"
REPORT_PATH = ROOT / "reports" / "phase1_data_quality.md"
PARQUET_NAME = "delhi_restaurants.parquet"
DOC_FILES = (
    "DATA_LICENSE_NOTICE.md",
    "LICENSE",
    "TOP_LEVEL_SCHEMA.md",
    "zomato_restaurants_india_summary.json",
)
MAX_RESTAURANTS = 200
COLUMN_CANDIDATES = {
    "res_id": ("res_id", "restaurant_id", "id"),
    "name": ("restaurant_name", "name"),
    "city": ("city_name", "city"),
    "locality": ("locality_name", "locality"),
    "cuisine": ("cuisine_string", "cuisines", "cuisine"),
    "rating": ("delivery_rating", "rating"),
    "rating_count": ("rating_count", "votes", "delivery_votes", "vote_count"),
    "cost_for_two": ("cost_for_two", "cost", "average_cost_for_two"),
    "json": ("json", "raw_json", "record"),
}


def sql_string(path: Path) -> str:
    return str(path).replace("'", "''")


def authenticate():
    token_file = Path.home() / ".kaggle" / "access_token"
    legacy_file = Path.home() / ".kaggle" / "kaggle.json"
    if not os.environ.get("KAGGLE_API_TOKEN") and not token_file.exists() and not legacy_file.exists():
        raise SystemExit(
            "Kaggle is not logged in, so the snapshot cannot be downloaded yet.\n"
            "Generate a token at https://www.kaggle.com/settings/api and add this line to "
            f"{ROOT / '.env'}:\n"
            "KAGGLE_API_TOKEN=your-token-here\n"
            "Then rerun: .venv/bin/python scripts/run_zomato_pilot.py"
        )
    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
    except ImportError as exc:
        raise SystemExit(f"The kaggle package failed to import: {exc}") from exc
    api = KaggleApi()
    api.authenticate()
    return api


def _extract_if_zipped(raw_dir: Path, file_name: str) -> None:
    zipped = raw_dir / f"{file_name}.zip"
    if not zipped.exists():
        return
    with zipfile.ZipFile(zipped) as archive:
        archive.extractall(raw_dir)
    zipped.unlink()


def ensure_download(api) -> dict:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = RAW_DIR / "SOURCE_MANIFEST.json"
    downloaded_at = datetime.now(timezone.utc).isoformat()
    if manifest_path.exists():
        try:
            downloaded_at = json.loads(manifest_path.read_text(encoding="utf-8")).get("downloaded_at", downloaded_at)
        except json.JSONDecodeError:
            pass
    for file_name in DOC_FILES:
        dest = RAW_DIR / file_name
        if dest.exists() and dest.stat().st_size > 0:
            print(f"already present: {dest.name}")
            continue
        print(f"downloading {file_name}")
        api.dataset_download_file(
            DATASET, file_name, path=str(RAW_DIR), force=False, quiet=False, unzip=True
        )
        _extract_if_zipped(RAW_DIR, file_name)
        if not dest.exists():
            raise SystemExit(f"Download finished but {file_name} is not in {RAW_DIR}.")
    parquet_path = RAW_DIR / PARQUET_NAME
    if not parquet_path.exists():
        raise SystemExit(
            f"Delhi extract not found at {parquet_path}. "
            "The all-India snapshot was deleted after the Delhi rows were saved."
        )
    metadata = {"dataset": DATASET, "downloaded_at": downloaded_at}
    try:
        listing = api.dataset_list(search="zomato-india-delivery-menus")
        for item in listing or []:
            ref = getattr(item, "ref", "") or ""
            if ref.endswith("zomato-india-delivery-menus"):
                metadata["kaggle_last_updated"] = getattr(item, "lastUpdated", None)
                metadata["kaggle_title"] = getattr(item, "title", None)
                break
    except Exception as exc:
        metadata["metadata_error"] = str(exc)
    (manifest_path).write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


def parquet_columns(con: duckdb.DuckDBPyConnection, path: Path) -> list[str]:
    rows = con.execute(f"DESCRIBE SELECT * FROM read_parquet('{sql_string(path)}')").fetchall()
    return [row[0] for row in rows]


def resolve_columns(columns: list[str]) -> dict[str, str]:
    lookup = {column.lower(): column for column in columns}
    resolved = {}
    missing = []
    for logical, candidates in COLUMN_CANDIDATES.items():
        actual = next((lookup[name] for name in candidates if name in lookup), None)
        if actual is None and logical in {"res_id", "name", "city", "locality", "json"}:
            missing.append(logical)
        if actual is not None:
            resolved[logical] = actual
    if missing:
        raise SystemExit(
            "The snapshot parquet is missing required columns: "
            + ", ".join(missing)
            + f"\nColumns found: {', '.join(columns)}"
        )
    return resolved


def quote_ident(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def assign_pilot_locality(locality: str | None) -> str | None:
    text = (locality or "").lower().strip()
    compact = text.replace(".", "").replace(" ", "")
    if "connaught" in text or compact == "cp":
        return "Connaught Place"
    if "hauz khas" in text or "hauzkhas" in compact:
        return "Hauz Khas"
    if "karol bagh" in text or "karolbagh" in compact:
        return "Karol Bagh"
    return None


def load_delhi_frame(con: duckdb.DuckDBPyConnection, path: Path, columns: dict[str, str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    city = quote_ident(columns["city"])
    locality = quote_ident(columns["locality"])
    selected = [quote_ident(columns[key]) for key in columns]
    inventory = con.execute(
        f"""
        SELECT {city} AS city_name, {locality} AS locality_name, count(*) AS restaurants
        FROM read_parquet('{sql_string(path)}')
        WHERE lower(coalesce(CAST({city} AS VARCHAR), '')) LIKE '%delhi%'
        GROUP BY 1, 2
        ORDER BY restaurants DESC, locality_name
        """
    ).fetchdf()
    frame = con.execute(
        f"""
        SELECT {", ".join(selected)}
        FROM read_parquet('{sql_string(path)}')
        WHERE lower(coalesce(CAST({city} AS VARCHAR), '')) LIKE '%delhi%'
          AND (
            lower(coalesce(CAST({locality} AS VARCHAR), '')) LIKE '%connaught%'
            OR lower(replace(coalesce(CAST({locality} AS VARCHAR), ''), ' ', '')) IN ('cp')
            OR lower(coalesce(CAST({locality} AS VARCHAR), '')) LIKE '%hauz khas%'
            OR lower(replace(coalesce(CAST({locality} AS VARCHAR), ''), ' ', '')) LIKE '%hauzkhas%'
            OR lower(coalesce(CAST({locality} AS VARCHAR), '')) LIKE '%karol bagh%'
            OR lower(replace(coalesce(CAST({locality} AS VARCHAR), ''), ' ', '')) LIKE '%karolbagh%'
          )
        """
    ).fetchdf()
    return inventory, frame


def cap_restaurants(frame: pd.DataFrame) -> tuple[pd.DataFrame, bool]:
    if len(frame) <= MAX_RESTAURANTS:
        return frame, False
    counts = frame["pilot_locality"].value_counts().to_dict()
    localities = sorted(counts)
    total = sum(counts.values())
    quotas = {name: max(1, int(MAX_RESTAURANTS * counts[name] / total)) for name in localities}
    while sum(quotas.values()) > MAX_RESTAURANTS:
        name = max(quotas, key=quotas.get)
        if quotas[name] == 1:
            break
        quotas[name] -= 1
    while sum(quotas.values()) < MAX_RESTAURANTS:
        name = max(localities, key=lambda loc: counts[loc] / quotas[loc])
        quotas[name] += 1
    parts = []
    for name, quota in quotas.items():
        part = frame[frame["pilot_locality"] == name].sort_values("res_id").head(quota)
        parts.append(part)
    return pd.concat(parts, ignore_index=True), True


def _record(value) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str) and value.strip():
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return {}


def menu_payload(record: dict):
    for key in ("menu", "menus", "order_menu", "menu_data"):
        value = record.get(key)
        if value not in (None, [], {}, ""):
            return value
    return None


def _number(value) -> float | None:
    return parse_price(value)


def build_tables(frame: pd.DataFrame, columns: dict[str, str], collection_date: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    restaurants = []
    dishes = []
    for row in frame.itertuples(index=False):
        values = row._asdict()
        res_id = values.get(columns["res_id"])
        if res_id is None or (isinstance(res_id, float) and pd.isna(res_id)):
            continue
        res_id = str(res_id)
        record = _record(values.get(columns["json"]))
        name = values.get(columns["name"]) or find_text(record, ("name", "restaurant_name"))
        locality = values.get(columns["locality"])
        city = values.get(columns["city"])
        lat, lon = find_lat_lon(record)
        rating = values.get(columns["rating"]) if "rating" in columns else None
        if rating is None or (isinstance(rating, float) and pd.isna(rating)):
            rating = find_text(record, ("delivery_rating", "rating", "aggregate_rating"))
        try:
            rating = None if rating is None or (isinstance(rating, float) and pd.isna(rating)) else float(rating)
        except (TypeError, ValueError):
            rating = parse_price(rating)
        rating_count = values.get(columns["rating_count"]) if "rating_count" in columns else None
        if rating_count is None or (isinstance(rating_count, float) and pd.isna(rating_count)):
            rating_count = find_text(record, ("votes", "rating_count", "vote_count", "review_count"))
        try:
            rating_count = None if rating_count is None or (isinstance(rating_count, float) and pd.isna(rating_count)) else int(float(str(rating_count).replace(",", "")))
        except (TypeError, ValueError):
            rating_count = None
        cost = values.get(columns["cost_for_two"]) if "cost_for_two" in columns else None
        if cost is None or (isinstance(cost, float) and pd.isna(cost)):
            cost = find_text(record, ("cost_for_two", "average_cost_for_two", "cft"))
        cuisine = values.get(columns["cuisine"]) if "cuisine" in columns else None
        if cuisine is None or (isinstance(cuisine, float) and pd.isna(cuisine)):
            cuisine = find_text(record, ("cuisine_string", "cuisines"))
        address = find_text(record, ("address", "locality_verbose", "location"))
        phone = find_text(record, ("phone", "phone_no", "mobile_phone", "contact_number"))
        url = find_text(record, ("restaurant_url", "url", "order_url"))
        menu_node = record.get("menu") if isinstance(record.get("menu"), dict) else {}
        price_blocked = menu_node.get("price_login_blocker")
        restaurants.append(
            {
                "restaurant_id": f"zomato:{res_id}",
                "name": None if name is None or (isinstance(name, float) and pd.isna(name)) else str(name),
                "normalized_name": normalize_name(None if name is None or (isinstance(name, float) and pd.isna(name)) else str(name)),
                "address": address,
                "locality_name": None if locality is None or (isinstance(locality, float) and pd.isna(locality)) else str(locality),
                "pilot_locality": values.get("pilot_locality"),
                "city_name": None if city is None or (isinstance(city, float) and pd.isna(city)) else str(city),
                "latitude": lat,
                "longitude": lon,
                "rating": rating,
                "rating_count": rating_count,
                "cost_for_two": _number(cost),
                "cuisine": None if cuisine is None or (isinstance(cuisine, float) and pd.isna(cuisine)) else str(cuisine),
                "phone": phone,
                "url": url,
                "source": SOURCE_NAME,
                "source_id": res_id,
                "collection_date": collection_date,
                "dish_price_blocked": price_blocked if isinstance(price_blocked, bool) else None,
            }
        )
        payload = menu_payload(record)
        items = list(iter_menu_items(payload)) if payload is not None else []
        seen = set()
        for index, item in enumerate(items):
            key = (
                item["normalized_dish_name"],
                item["category"],
                item["price"],
                item["item_source_id"],
            )
            if key in seen:
                continue
            seen.add(key)
            item_id = item["item_source_id"] or f"{item['normalized_dish_name'] or 'dish'}:{index}"
            dishes.append(
                {
                    "dish_id": f"zomato:{res_id}:{item_id}",
                    "restaurant_id": f"zomato:{res_id}",
                    "dish_name": item["dish_name"],
                    "normalized_dish_name": item["normalized_dish_name"],
                    "category": item["category"],
                    "cuisine": None if cuisine is None or (isinstance(cuisine, float) and pd.isna(cuisine)) else str(cuisine),
                    "price": item["price"],
                    "description": item["description"],
                    "is_veg": item["is_veg"],
                    "is_bestseller": item["is_bestseller"],
                    "image_url": item["image_url"],
                    "source": SOURCE_NAME,
                    "source_id": item["item_source_id"],
                    "collection_date": collection_date,
                }
            )
    restaurant_frame = pd.DataFrame(restaurants)
    dish_frame = pd.DataFrame(dishes)
    if not dish_frame.empty and not restaurant_frame.empty:
        veg_summary = (
            dish_frame.groupby("restaurant_id")["is_veg"]
            .apply(lambda series: _restaurant_veg(series))
            .rename("veg_nonveg")
        )
        restaurant_frame = restaurant_frame.merge(veg_summary, on="restaurant_id", how="left")
    elif not restaurant_frame.empty:
        restaurant_frame["veg_nonveg"] = None
    return restaurant_frame, dish_frame


def _restaurant_veg(series: pd.Series) -> str | None:
    known = series.dropna()
    if known.empty:
        return None
    if bool(known.all()):
        return "veg"
    if not bool(known.any()):
        return "nonveg"
    return "mixed"


def _missing_table(frame: pd.DataFrame) -> list[str]:
    lines = ["| column | missing | missing % |", "|---|---:|---:|"]
    total = len(frame)
    for column in frame.columns:
        missing = int(frame[column].isna().sum())
        pct = 0 if total == 0 else 100 * missing / total
        lines.append(f"| {column} | {missing} | {pct:.1f} |")
    return lines


def _md_table(frame: pd.DataFrame, columns: list[str], limit: int) -> str:
    view = frame.loc[:, [column for column in columns if column in frame.columns]].head(limit)
    if view.empty:
        return "_no rows_"
    header = "| " + " | ".join(view.columns) + " |"
    rule = "| " + " | ".join("---" for _ in view.columns) + " |"
    body = []
    for row in view.itertuples(index=False):
        cells = []
        for value in row:
            text = "" if value is None or (isinstance(value, float) and pd.isna(value)) else str(value)
            text = text.replace("|", "/").replace("\n", " ")
            if len(text) > 80:
                text = text[:77] + "..."
            cells.append(text)
        body.append("| " + " | ".join(cells) + " |")
    return "\n".join([header, rule, *body])


def _cuisine_count(frame: pd.DataFrame) -> int:
    if frame.empty or "cuisine" not in frame.columns:
        return 0
    names = set()
    for value in frame["cuisine"].dropna():
        for part in str(value).split(","):
            name = part.strip()
            if name:
                names.add(name.lower())
    return len(names)


def write_report(
    restaurants: pd.DataFrame,
    dishes: pd.DataFrame,
    inventory: pd.DataFrame,
    metadata: dict,
    capped: bool,
    matched_before_cap: int,
) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    restaurant_dupes = 0
    if not restaurants.empty:
        restaurant_dupes = int(restaurants["source_id"].duplicated().sum())
    dish_dupes = 0
    if not dishes.empty:
        dish_dupes = int(
            dishes.duplicated(subset=["restaurant_id", "normalized_dish_name", "category", "price"]).sum()
        )
    price_coverage = 0.0
    if not dishes.empty:
        price_coverage = 100 * dishes["price"].notna().mean()
    locality_coverage = 0.0
    coord_coverage = 0.0
    if not restaurants.empty:
        locality_coverage = 100 * restaurants["locality_name"].notna().mean()
        coord_coverage = 100 * (restaurants["latitude"].notna() & restaurants["longitude"].notna()).mean()
    lines = [
        "# Phase 1 data-quality report",
        "",
        "Pilot only. Three Delhi localities from the Kaggle Zomato delivery-menu snapshot.",
        "",
        "## Source",
        "",
        f"- Dataset: `{DATASET}`",
        f"- Downloaded at: {metadata.get('downloaded_at')}",
        f"- Kaggle last updated: {metadata.get('kaggle_last_updated', 'unavailable')}",
        "- Access method: Kaggle API download of the published parquet. This run did not scrape Zomato.",
        "- License note: the Kaggle card lists MIT and also warns that the contents are scraped marketplace data. Raw files are local only and are gitignored.",
        "",
        "## Pilot definition",
        "",
        "- Localities: Connaught Place, Hauz Khas, Karol Bagh",
        f"- Delhi rows matching those locality names, before the cap: {matched_before_cap}",
        f"- Cap of {MAX_RESTAURANTS} restaurants applied: {'yes' if capped else 'no'}",
        "",
        "## Counts",
        "",
        f"- Restaurants: {len(restaurants)}",
        f"- Menu items: {len(dishes)}",
        f"- Unique dishes (normalized name): {0 if dishes.empty else dishes['normalized_dish_name'].nunique()}",
        f"- Cuisine labels: {_cuisine_count(restaurants)}",
        f"- Localities in the pilot: {0 if restaurants.empty else restaurants['pilot_locality'].nunique()}",
        f"- Price coverage: {price_coverage:.1f}% of menu items have a positive price",
        f"- Locality coverage: {locality_coverage:.1f}% of restaurants",
        f"- Coordinate coverage: {coord_coverage:.1f}% of restaurants",
        f"- Duplicate restaurant ids: {restaurant_dupes}",
        f"- Duplicate dish rows (same restaurant, name, category, price): {dish_dupes}",
        "",
        "## Pilot locality counts",
        "",
        _md_table(
            restaurants.groupby("pilot_locality", dropna=False).size().reset_index(name="restaurants")
            if not restaurants.empty
            else restaurants,
            ["pilot_locality", "restaurants"],
            10,
        ),
        "",
        "## Problems",
        "",
    ]
    blocked = 0
    if not restaurants.empty and "dish_price_blocked" in restaurants.columns:
        blocked = int(restaurants["dish_price_blocked"].fillna(False).sum())
    if dishes.empty or price_coverage == 0:
        lines.extend(
            [
                f"- Dish prices are missing. {blocked} of {len(restaurants)} pilot menus set `price_login_blocker` to true, and the dish objects have no price field.",
                "- Modifier-group prices exist for some add-ons. Those were not copied onto dishes.",
                "- Hauz Khas is almost absent as a locality label in this snapshot. The Delhi inventory below shows the labels that do occur.",
                "",
            ]
        )
    else:
        lines.append("- No blocking data-quality failure in this run.")
        lines.append("")
    lines.extend(
        [
            "## Restaurant missing values",
            "",
            *(_missing_table(restaurants) if not restaurants.empty else ["_no restaurants_"]),
            "",
            "## Menu-item missing values",
            "",
            *(_missing_table(dishes) if not dishes.empty else ["_no menu items_"]),
            "",
            "## Delhi locality inventory (top 25 by restaurant count)",
            "",
            "This is a count only. Menu rows were parsed for the pilot localities.",
            "",
            _md_table(inventory, ["city_name", "locality_name", "restaurants"], 25),
            "",
            "## Sample restaurants",
            "",
            _md_table(
                restaurants,
                ["name", "pilot_locality", "locality_name", "cuisine", "rating", "cost_for_two", "latitude", "longitude"],
                8,
            ),
            "",
            "## Sample dishes",
            "",
            _md_table(
                dishes,
                ["dish_name", "category", "price", "is_veg", "description", "image_url"],
                8,
            ),
            "",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"wrote {REPORT_PATH}")


def main() -> None:
    api = authenticate()
    metadata = ensure_download(api)
    parquet_path = RAW_DIR / PARQUET_NAME
    con = duckdb.connect()
    columns = resolve_columns(parquet_columns(con, parquet_path))
    print("resolved columns:", columns)
    inventory, frame = load_delhi_frame(con, parquet_path, columns)
    PILOT_DIR.mkdir(parents=True, exist_ok=True)
    inventory.to_csv(PILOT_DIR / "delhi_locality_counts.csv", index=False)
    print(f"delhi locality rows: {len(inventory)}")
    locality_col = columns["locality"]
    frame["pilot_locality"] = frame[locality_col].map(assign_pilot_locality)
    frame = frame[frame["pilot_locality"].notna()].copy()
    frame["res_id"] = frame[columns["res_id"]].astype(str)
    matched = len(frame)
    print(f"matched restaurants: {matched}")
    print(frame["pilot_locality"].value_counts().to_string() if matched else "no matches")
    if matched == 0:
        write_report(pd.DataFrame(), pd.DataFrame(), inventory, metadata, False, 0)
        raise SystemExit(
            "No restaurants matched Connaught Place, Hauz Khas, or Karol Bagh. "
            f"See {PILOT_DIR / 'delhi_locality_counts.csv'} for the labels actually present."
        )
    frame, capped = cap_restaurants(frame)
    collection_date = metadata.get("downloaded_at", "")[:10]
    restaurants, dishes = build_tables(frame, columns, collection_date)
    restaurants.to_parquet(PILOT_DIR / "pilot_restaurants.parquet", index=False)
    dishes.to_parquet(PILOT_DIR / "pilot_menu_items.parquet", index=False)
    print(f"restaurants written: {len(restaurants)}")
    print(f"menu items written: {len(dishes)}")
    write_report(restaurants, dishes, inventory, metadata, capped, matched)


if __name__ == "__main__":
    main()
