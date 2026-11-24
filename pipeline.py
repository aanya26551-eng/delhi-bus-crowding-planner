# ==========================================
# DELHI BUS CROWDING DATA PIPELINE (COLAB)
# ==========================================
import os, glob, zipfile, json
import pandas as pd
import numpy as np

print("🔍 Step 1: Looking for uploaded dataset...")
files = glob.glob("*.zip") + glob.glob("*.csv") + glob.glob("*.xlsx")

df = None
if files:
    target = files[0]
    print(f"✅ Found file: {target}")
    if target.endswith(".zip"):
        with zipfile.ZipFile(target, 'r') as z:
            csv_names = [f for f in z.namelist() if f.endswith('.csv')]
            print(f"📦 Extracting {csv_names[0]}...")
            with z.open(csv_names[0]) as f:
                df = pd.read_csv(f, low_memory=False)
    elif target.endswith(".csv"):
        df = pd.read_csv(target, low_memory=False)
    elif target.endswith(".xlsx"):
        df = pd.read_excel(target)
    print(f"📊 Loaded {len(df):,} rows! Columns: {list(df.columns)}")
else:
    print("⚠️ No dataset file uploaded yet—generating realistic Delhi DTC/Cluster sample data so you aren't blocked!")
    np.random.seed(42)
    routes = [
        ("534", "Anand Vihar ISBT", "Mehrauli Terminal", 52),
        ("764", "Najafgarh Terminal", "Nehru Place Terminal", 48),
        ("429", "Mori Gate Terminal", "Kalkaji Mandir", 42),
        ("OMS (+)", "Uttam Nagar Terminal", "Anand Vihar ISBT", 58),
        ("543", "Anand Vihar ISBT", "Safdarjung Terminal", 46),
        ("729", "Kapashera Border", "Mori Gate Terminal", 55),
    ]
    rows = []
    for route_id, orig, dest, base_mins in routes:
        for is_weekend in [0, 1]:
            for hour in range(6, 23):
                # Simulate morning (8-10am) and evening (5-8pm) Delhi rush hours
                peak_factor = 1.0
                if not is_weekend and hour in [8, 9, 10, 17, 18, 19, 20]:
                    peak_factor = 2.6
                elif is_weekend and hour in [12, 13, 17, 18, 19]:
                    peak_factor = 1.6
                trips = np.random.randint(3, 8)
                for _ in range(trips):
                    pax = int(np.clip(np.random.normal(24 * peak_factor, 8), 5, 78))
                    rows.append({
                        "route_no": route_id,
                        "origin": orig,
                        "destination": dest,
                        "hour": hour,
                        "is_weekend": is_weekend,
                        "passengers": pax,
                        "travel_mins": int(base_mins * (1.25 if peak_factor > 2 else 1.0))
                    })
    df = pd.DataFrame(rows)

# ==========================================
# Step 2: Clean & Compute Crowding Levels
# ==========================================
print("\n⚙️ Step 2: Computing passenger loads & crowding scores...")

# Standardize column names flexibly if using raw CSV
cols_lower = {c.lower(): c for c in df.columns}
if "passengers" not in df.columns:
    # Auto-detect route, time, and passenger/ticket count columns
    route_col = next((cols_lower[k] for k in cols_lower if "route" in k), df.columns[0])
    time_col = next((cols_lower[k] for k in cols_lower if "time" in k or "date" in k or "hour" in k), None)
    pax_col = next((cols_lower[k] for k in cols_lower if "ticket" in k or "pax" in k or "count" in k or "pass" in k), None)
    orig_col = next((cols_lower[k] for k in cols_lower if "orig" in k or "from" in k or "source" in k or "start" in k), None)
    dest_col = next((cols_lower[k] for k in cols_lower if "dest" in k or "to" in k or "end" in k), None)

    work = pd.DataFrame()
    work["route_no"] = df[route_col].astype(str)
    if time_col:
        dt = pd.to_datetime(df[time_col], errors="coerce")
        work["hour"] = dt.dt.hour.fillna(9).astype(int)
        work["is_weekend"] = (dt.dt.dayofweek >= 5).astype(int)
    else:
        work["hour"] = 9
        work["is_weekend"] = 0
    work["passengers"] = pd.to_numeric(df[pax_col], errors="coerce").fillna(1) if pax_col else 1
    work["origin"] = df[orig_col].astype(str) if orig_col else "Anand Vihar ISBT"
    work["destination"] = df[dest_col].astype(str) if dest_col else "Connaught Place"
    work["travel_mins"] = 45

    # Aggregate tickets per route/hour/day-type
    grouped = work.groupby(["route_no", "origin", "destination", "hour", "is_weekend"], as_index=False).agg(
        passengers=("passengers", "sum"),
        sample_trips=("passengers", "count"),
        travel_mins=("travel_mins", "mean")
    )
    # Normalize passenger load per bus trip (assuming ~4-6 buses/hour on active corridors)
    grouped["avg_bus_load"] = (grouped["passengers"] / np.maximum(grouped["sample_trips"] / 15.0, 1)).clip(6, 82)
else:
    grouped = df.groupby(["route_no", "origin", "destination", "hour", "is_weekend"], as_index=False).agg(
        avg_bus_load=("passengers", "mean"),
        sample_trips=("passengers", "count"),
        travel_mins=("travel_mins", "mean")
    )

# Standard Delhi Low-Floor AC/Non-AC Bus Capacity = 42 seats, 70 max crush load
SEAT_CAPACITY = 42.0
grouped["load_ratio"] = (grouped["avg_bus_load"] / SEAT_CAPACITY).round(2)

def label_crowding(ratio):
    if ratio <= 0.75:
        return "Seats Available"
    elif ratio <= 1.15:
        return "Standing Room"
    else:
        return "Crowded"

grouped["crowding_level"] = grouped["load_ratio"].apply(label_crowding)
grouped["confidence"] = np.where(grouped["sample_trips"] >= 5, "High", "Low Sample")
grouped["avg_bus_load"] = grouped["avg_bus_load"].round(0).astype(int)
grouped["travel_mins"] = grouped["travel_mins"].round(0).astype(int)

# Save clean summary for the Web App
output_file = "crowding_summary.json"
grouped.to_json(output_file, orient="records", indent=2)

print(f"\n🎉 SUCCESS! Saved {len(grouped)} route-hour profiles to '{output_file}'.")
print("\nPreview of Peak vs Off-Peak Results:")
print(grouped[["route_no", "hour", "is_weekend", "avg_bus_load", "load_ratio", "crowding_level"]].head(10).to_string(index=False))
