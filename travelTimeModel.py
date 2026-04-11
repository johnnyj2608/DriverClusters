import pandas as pd
import numpy as np
import geopandas as gpd
import h3
import pickle
import glob

H3_RESOLUTION = 8


# -----------------------------
# ZONES → CENTROIDS
# -----------------------------
def buildZoneCentroidMap(shpPath):
    zones = gpd.read_file(shpPath)
    zones["centroid"] = zones.geometry.centroid

    zoneMap = {}
    for _, row in zones.iterrows():
        zoneId = int(row["LocationID"])
        zoneMap[zoneId] = (row["centroid"].y, row["centroid"].x)

    return zoneMap


# -----------------------------
# STREAM FILES (NO CONCAT)
# -----------------------------
def processFiles(folderPath, zoneMap, sampleSize=2_000_000):

    files = glob.glob(folderPath + "/*.parquet")

    print(f"Found {len(files)} files")

    baseCounts = {}
    hourSum = {}
    monthSum = {}
    globalSum = 0
    globalCount = 0

    for f in files:
        print("Processing:", f)

        df = pd.read_parquet(f)

        df = df[
            [
                "pickup_datetime",
                "dropoff_datetime",
                "PULocationID",
                "DOLocationID"
            ]
        ].copy()

        df["pickup_datetime"] = pd.to_datetime(df["pickup_datetime"])
        df["dropoff_datetime"] = pd.to_datetime(df["dropoff_datetime"])

        df["durationSec"] = (
            df["dropoff_datetime"] - df["pickup_datetime"]
        ).dt.total_seconds()

        # filter early (IMPORTANT for memory)
        df = df[(df["durationSec"] > 60) & (df["durationSec"] < 7200)]

        # sample per file
        if len(df) > sampleSize // len(files):
            df = df.sample(sampleSize // len(files), random_state=42)

        df["hour"] = df["pickup_datetime"].dt.hour
        df["month"] = df["pickup_datetime"].dt.month

        # convert zones → lat/lon
        df["puLat"] = df["PULocationID"].map(lambda z: zoneMap.get(z, (np.nan, np.nan))[0])
        df["puLon"] = df["PULocationID"].map(lambda z: zoneMap.get(z, (np.nan, np.nan))[1])

        df["doLat"] = df["DOLocationID"].map(lambda z: zoneMap.get(z, (np.nan, np.nan))[0])
        df["doLon"] = df["DOLocationID"].map(lambda z: zoneMap.get(z, (np.nan, np.nan))[1])

        df = df.dropna()

        # H3 encoding
        df["puCell"] = df.apply(lambda r: h3.latlng_to_cell(r.puLat, r.puLon, H3_RESOLUTION), axis=1)
        df["doCell"] = df.apply(lambda r: h3.latlng_to_cell(r.doLat, r.doLon, H3_RESOLUTION), axis=1)

        # accumulate stats (NO giant dataframe)
        for r in df.itertuples():

            key = (r.puCell, r.doCell)

            baseCounts[key] = baseCounts.get(key, 0) + r.durationSec

            hourSum[r.hour] = hourSum.get(r.hour, 0) + r.durationSec
            monthSum[r.month] = monthSum.get(r.month, 0) + r.durationSec

            globalSum += r.durationSec
            globalCount += 1

    return baseCounts, hourSum, monthSum, globalSum, globalCount


# -----------------------------
# BUILD FINAL MODEL
# -----------------------------
def buildModel(baseCounts, hourSum, monthSum, globalSum, globalCount):

    baseModel = {}
    for k, v in baseCounts.items():
        baseModel[k] = v  # (we'll normalize later if needed)

    globalMean = globalSum / globalCount

    hourFactor = {
        k: (v / globalCount) / globalMean for k, v in hourSum.items()
    }

    monthFactor = {
        k: (v / globalCount) / globalMean for k, v in monthSum.items()
    }

    return baseModel, hourFactor, monthFactor, globalMean


# -----------------------------
# SAVE MODEL
# -----------------------------
def saveModel(model, path="h3Model.pkl"):
    with open(path, "wb") as f:
        pickle.dump(model, f)


# -----------------------------
# RUN
# -----------------------------
folderPath = "fhvhv_data_2025"
zoneShpPath = "taxiZones/taxi_zones.shp"

print("Loading zones...")
zoneMap = buildZoneCentroidMap(zoneShpPath)

print("Training streaming model...")
baseCounts, hourSum, monthSum, globalSum, globalCount = processFiles(folderPath, zoneMap)

print("Building final model...")
model = buildModel(baseCounts, hourSum, monthSum, globalSum, globalCount)

print("Saving...")
saveModel(model)

print("DONE ✔ Memory-safe model built")