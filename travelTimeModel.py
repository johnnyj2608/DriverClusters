import pandas as pd
import numpy as np
import geopandas as gpd
import h3
import pickle

H3_RESOLUTION = 8


# -----------------------------
# LOAD HVFHV DATA (CLEAN + SAMPLE)
# -----------------------------
def loadHvfhv(path, sampleSize=500_000):
    df = pd.read_parquet(path)

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

    # filter bad trips
    df = df[(df["durationSec"] > 60) & (df["durationSec"] < 7200)]

    # sample for speed
    if len(df) > sampleSize:
        df = df.sample(sampleSize, random_state=42)

    return df


# -----------------------------
# TAXI ZONES → CENTROIDS
# -----------------------------
def buildZoneCentroidMap(shpPath):
    zones = gpd.read_file(shpPath)
    zones["centroid"] = zones.geometry.centroid

    zoneMap = {}
    for _, row in zones.iterrows():
        zoneId = int(row["LocationID"])
        lat = row["centroid"].y
        lon = row["centroid"].x
        zoneMap[zoneId] = (lat, lon)

    return zoneMap


# -----------------------------
# ADD LAT/LON
# -----------------------------
def addLatLon(df, zoneMap):
    df["puLat"] = df["PULocationID"].map(lambda z: zoneMap.get(z, (np.nan, np.nan))[0])
    df["puLon"] = df["PULocationID"].map(lambda z: zoneMap.get(z, (np.nan, np.nan))[1])

    df["doLat"] = df["DOLocationID"].map(lambda z: zoneMap.get(z, (np.nan, np.nan))[0])
    df["doLon"] = df["DOLocationID"].map(lambda z: zoneMap.get(z, (np.nan, np.nan))[1])

    df = df.dropna(subset=["puLat", "puLon", "doLat", "doLon"])
    return df


# -----------------------------
# ADD H3 CELLS
# -----------------------------
def addH3Cells(df):
    df["puCell"] = df.apply(
        lambda r: h3.latlng_to_cell(r.puLat, r.puLon, H3_RESOLUTION),
        axis=1
    )

    df["doCell"] = df.apply(
        lambda r: h3.latlng_to_cell(r.doLat, r.doLon, H3_RESOLUTION),
        axis=1
    )

    return df


# -----------------------------
# BUILD MODEL (AGGREGATION STEP)
# -----------------------------
def buildH3Model(df):
    df["hour"] = df["pickup_datetime"].dt.hour

    # base OD travel times
    baseModel = (
        df.groupby(["puCell", "doCell"])["durationSec"]
        .mean()
        .to_dict()
    )

    # global baseline
    globalMean = df["durationSec"].mean()

    # hourly scaling factor
    hourStats = df.groupby("hour")["durationSec"].mean()
    hourFactor = (hourStats / globalMean).to_dict()

    return baseModel, hourFactor, globalMean


# -----------------------------
# SAVE MODEL
# -----------------------------
def saveModel(baseModel, hourFactor, globalMean, path="h3Model.pkl"):
    with open(path, "wb") as f:
        pickle.dump((baseModel, hourFactor, globalMean), f)


# -----------------------------
# LOAD MODEL
# -----------------------------
def loadModel(path="h3Model.pkl"):
    with open(path, "rb") as f:
        return pickle.load(f)


# -----------------------------
# PREDICTION
# -----------------------------
def estimateTime(puCell, doCell, hour,
                 baseModel, hourFactor, globalMean):

    base = baseModel.get((puCell, doCell), globalMean)
    factor = hourFactor.get(hour, 1.0)

    return base * factor


# -----------------------------
# PIPELINE
# -----------------------------

hvfhvPath = "fhvhv_tripdata_2025-04.parquet"
zoneShpPath = "taxiZones/taxi_zones.shp"

print("Loading data...")
df = loadHvfhv(hvfhvPath)

print("Loading zones...")
zoneMap = buildZoneCentroidMap(zoneShpPath)

print("Adding coordinates...")
df = addLatLon(df, zoneMap)

print("Building H3 grid...")
df = addH3Cells(df)

print("Training aggregated model...")
baseModel, hourFactor, globalMean = buildH3Model(df)

print("Saving model...")
saveModel(baseModel, hourFactor, globalMean)

print("DONE ✔ Model saved as h3Model.pkl")