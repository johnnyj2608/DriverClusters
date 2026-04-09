import random
import numpy as np
from datetime import timedelta

def haversine(lat1, lon1, lats2, lons2):
    R = 6371000  # Earth radius in meters
    lat1, lon1 = np.radians(lat1), np.radians(lon1)
    lats2, lons2 = np.radians(lats2), np.radians(lons2)
    
    dlat = lats2 - lat1
    dlon = lons2 - lon1

    a = np.sin(dlat/2)**2 + np.cos(lat1)*np.cos(lats2)*np.sin(dlon/2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
    return R * c

def depotBearing(depot, lats, lons):
    lat1, lon1 = np.radians(depot[0]), np.radians(depot[1])
    lat2, lon2 = np.radians(lats), np.radians(lons)

    dLon = lon2 - lon1
    x = np.sin(dLon) * np.cos(lat2)
    y = np.cos(lat1) * np.sin(lat2) - np.sin(lat1) * np.cos(lat2) * np.cos(dLon)
    bearings = np.degrees(np.arctan2(x, y)) % 360
    return bearings

def sliceMatrixWedge(fullDistanceMatrix, fullTimeMatrix, wedgeMembers, memberToIndex):
    indices = [0] + [memberToIndex[id(m)] for m in wedgeMembers]
    indices = np.array(indices)

    fullDistanceMatrix = np.array(fullDistanceMatrix)
    fullTimeMatrix = np.array(fullTimeMatrix)

    wedgeDistanceMatrix = fullDistanceMatrix[np.ix_(indices, indices)]
    wedgeTimeMatrix = fullTimeMatrix[np.ix_(indices, indices)]

    return wedgeDistanceMatrix.tolist(), wedgeTimeMatrix.tolist()

def computeTimes(route, times, startTime, reverse=False, maxRandomMinutes=5):
    cumulativeTimes = [None] * len(route)
    currentTime = startTime

    if reverse:
        for i in range(len(route) - 1, -1, -1):
            if i == len(route) - 1:
                cumulativeTimes[i] = currentTime
            else:
                currIdx = route[i]
                nextIdx = route[i + 1]
                travelSeconds = times[currIdx][nextIdx]

                randomDelay = random.randint(0, maxRandomMinutes * 60)
                travelSeconds += randomDelay

                currentTime += timedelta(seconds=travelSeconds)
                cumulativeTimes[i] = currentTime
    else:
        cumulativeTimes[0] = currentTime
        for i in range(1, len(route)):
            prevIdx = route[i - 1]
            currIdx = route[i]
            travelSeconds = times[prevIdx][currIdx]

            randomDelay = random.randint(0, maxRandomMinutes * 60)
            travelSeconds += randomDelay

            currentTime += timedelta(seconds=travelSeconds)
            cumulativeTimes[i] = currentTime

    return cumulativeTimes, currentTime