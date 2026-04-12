import numpy as np
from collections import defaultdict
from utils import haversine, depotBearing

def buildCityClusters(members):

    groups = defaultdict(lambda: {"members": [], "count": 0})

    for m in members:
        city = m["city"]

        # --------------------------
        # NYC GROUPING RULES
        # --------------------------

        if city in ["New York", "Bronx"]:
            key = "MANHATTAN_BRONX"

        elif city == "Staten Island":
            key = "STATEN_ISLAND"

        else:
            key = "MAIN"

        groups[key]["members"].append(m)
        groups[key]["count"] += 1

    return groups

def computeWedgeIndex(bearing, innerAngle, outerSplits):
    sliceAngle = innerAngle / outerSplits

    fanIndex = int(bearing // innerAngle)
    diffAngle = (bearing - fanIndex * innerAngle + 360) % 360
    splitIndex = int(min(diffAngle // sliceAngle, outerSplits - 1))

    return fanIndex * outerSplits + splitIndex

def mergeCityToWedges(cityClusters, depot, outerWedges, innerAngle, outerSplits):
    sliceAngle = innerAngle / outerSplits

    for cityName, cityData in cityClusters.items():
        members = cityData["members"]
        if not members:
            continue

        lats = np.array([m['lat'] for m in members])
        lons = np.array([m['lon'] for m in members])

        dists = haversine(depot[0], depot[1], lats, lons)
        closestIdx = np.argmin(dists)

        closestMember = members[closestIdx]
        closestLat = closestMember['lat']
        closestLon = closestMember['lon']

        bearing = depotBearing(
            depot,
            np.array([closestLat]),
            np.array([closestLon])
        )[0]

        fanIndex = int(bearing // innerAngle)
        diffAngle = (bearing - fanIndex * innerAngle + 360) % 360
        splitIndex = int(min(diffAngle // sliceAngle, outerSplits - 1))

        wedgeIndex = fanIndex * outerSplits + splitIndex

        outerWedges[wedgeIndex]["members"].extend(members)
        outerWedges[wedgeIndex]["count"] += len(members)

def calcMemberWedges(members, depot, innerRadius, innerAngle, outerSplits, stopFlag):
    numFans = int(360 / innerAngle)
    totalOuterWedges = numFans * outerSplits

    wedges = {
        "inner": {i: {"members": [], "count": 0} for i in range(numFans)},
        "outer": {i: {"members": [], "count": 0} for i in range(totalOuterWedges)},
        "count": len(members),
    }

    # Convert member data to numpy arrays
    lats = np.array([m['lat'] for m in members])
    lons = np.array([m['lon'] for m in members])

    # Compute distances and bearings vectorized
    dists = haversine(depot[0], depot[1], lats, lons)
    bearings = depotBearing(depot, lats, lons)

    sliceAngle = innerAngle / outerSplits

    fanIndices = (bearings // innerAngle).astype(int)
    diffAngles = (bearings - fanIndices * innerAngle + 360) % 360
    splitIndices = np.minimum((diffAngles // sliceAngle).astype(int), outerSplits - 1)
    wedgeIndices = fanIndices * outerSplits + splitIndices

    for idx, member in enumerate(members):
        if stopFlag.value: return None
        if dists[idx] <= innerRadius:
            wedges["inner"][fanIndices[idx]]["members"].append(member)
            wedges["inner"][fanIndices[idx]]["count"] += 1
        else:
            wedges["outer"][wedgeIndices[idx]]["members"].append(member)
            wedges["outer"][wedgeIndices[idx]]["count"] += 1

    return wedges

def calcVehicleWedges(vehicles, wedges, stopFlag):
    totalMembers = 0
    for w in wedges:
        totalMembers += wedges[w]["count"]

    assignments = defaultdict(list)

    while totalMembers > 0:
        for v in vehicles:
            if stopFlag.value: return None

            bestWedge, minDiff = None, None

            for w in wedges:
                remaining = wedges[w]["count"]
                if remaining <= 0:
                    continue

                diff = v["capacity"] - remaining
                if bestWedge is None or diff < minDiff:
                    bestWedge = w
                    minDiff = diff
                    if diff == 0:
                        break

            if bestWedge is None:
                break

            assignedCount = min(v["capacity"], wedges[bestWedge]["count"])
            wedges[bestWedge]["count"] -= assignedCount
            totalMembers -= assignedCount

            assignments[bestWedge].append({**v})
            v["trip"] += 1

    return assignments