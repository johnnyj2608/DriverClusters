import traceback
import random
import numpy as np
from collections import defaultdict
from datetime import timedelta
from excel import getMembersFromExcel, exportMembersToExcel
from cvrp import getDistanceTimeMatrix, computeRoutes
from plot import plotCoordinatesOnMap

def depotBearing(depot, lats, lons):
    lat1, lon1 = np.radians(depot[0]), np.radians(depot[1])
    lat2, lon2 = np.radians(lats), np.radians(lons)

    dLon = lon2 - lon1
    x = np.sin(dLon) * np.cos(lat2)
    y = np.cos(lat1) * np.sin(lat2) - np.sin(lat1) * np.cos(lat2) * np.cos(dLon)
    bearings = np.degrees(np.arctan2(x, y)) % 360
    return bearings

def haversine(lat1, lon1, lats2, lons2):
    R = 6371000  # Earth radius in meters
    lat1, lon1 = np.radians(lat1), np.radians(lon1)
    lats2, lons2 = np.radians(lats2), np.radians(lons2)
    
    dlat = lats2 - lat1
    dlon = lons2 - lon1

    a = np.sin(dlat/2)**2 + np.cos(lat1)*np.cos(lats2)*np.sin(dlon/2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))
    return R * c

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
    tripNumber = 1

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

            assignments[bestWedge].append({
                **v,
                "trip": tripNumber
            })

        tripNumber += 1

    return assignments

def sliceMatrixWedge(fullDistanceMatrix, fullTimeMatrix, wedgeMembers, memberToIndex):
    indices = [0]
    for m in wedgeMembers:
        indices.append(memberToIndex[id(m)])

    wedgeDistanceMatrix = []
    wedgeTimeMatrix = []

    for i in indices:
        distRow = [fullDistanceMatrix[i][j] for j in indices]
        timeRow = [fullTimeMatrix[i][j] for j in indices]
        wedgeDistanceMatrix.append(distRow)
        wedgeTimeMatrix.append(timeRow)

    return wedgeDistanceMatrix, wedgeTimeMatrix

def routeByWedges(members, depot, vehicles, statusLabel, stopFlag):
    innerRadius, innerAngle, outerSplits = 500, 90, 3
    memberWedges = calcMemberWedges(members, depot, innerRadius, innerAngle, outerSplits, stopFlag)
    outerWedges = memberWedges["outer"]
    innerWedges = memberWedges["inner"]

    locations = [depot] + [(m['lat'], m['lon']) for m in members]
    fullDistanceMatrix, fullTimeMatrix = getDistanceTimeMatrix(locations)
    memberToIndex = {}
    for i, m in enumerate(members):
        memberToIndex[id(m)] = i + 1

    vehicleWedges = calcVehicleWedges(vehicles, outerWedges, stopFlag)

    wedgeRoutes = {}
    totalWedges = len(vehicleWedges)

    for i, (wedge, vehiclesList) in enumerate(vehicleWedges.items(), start=1):
        if stopFlag.value: return None

        if not vehiclesList:
            continue

        outerMembers = outerWedges[wedge]["members"]
        innerMembers = innerWedges[wedge // outerSplits]["members"]

        if not outerMembers:
            continue

        distanceMatrix, timeMatrix = sliceMatrixWedge(
            fullDistanceMatrix,
            fullTimeMatrix,
            wedgeMembers=outerMembers + innerMembers,
            memberToIndex=memberToIndex
        )

        statusLabel.configure(text=f"Setting Wedge {i}/{totalWedges}...")
        statusLabel.update()
        routes, times, assigned, leftover = computeRoutes(
            outerMembers,
            innerMembers,
            depot,
            vehiclesList,
            distanceMatrix = distanceMatrix,
            timeMatrix = timeMatrix,
        )

        wedgeRoutes[wedge] = {
            "members": assigned,
            "routes": routes,
            "times": times,
            "vehicles": vehiclesList
        }

        innerWedges[wedge // outerSplits]["members"] = leftover

    return wedgeRoutes

def processRouteData(wedgeRoutes, initialTime, stopFlag):
    trips = []
    arrivalTimes = {}

    for data in wedgeRoutes.values():
        if stopFlag.value: return None

        routes = data["routes"]
        vehicles = data["vehicles"]
        members = data["members"]
        times = data["times"]

        for trip, route in enumerate(routes):
            if stopFlag.value: return None

            vehicle = vehicles[trip]
            vehicleId = vehicle["carId"]

            tripData = {
                "driver": vehicle["driver"],
                "carId": vehicle["carId"],
                "capacity": vehicle["capacity"],
                "trip": vehicle["trip"],
                "members": []
            }

            startTime = arrivalTimes.get(vehicleId, initialTime)
            randomOffset = random.randint(0, 5)
            startTime += timedelta(minutes=randomOffset)

            cumulativeTime = [startTime]
            totalTime = startTime

            # Compute cumulative times along the route
            for i in range(1, len(route)):
                prevIdx = route[i - 1]
                currIdx = route[i]
                seconds = times[prevIdx][currIdx]
                totalTime += timedelta(seconds=seconds)
                cumulativeTime.append(totalTime)

            arrivalTimes[vehicleId] = totalTime

            for stopNum, idx in enumerate(route):
                if idx == 0:  # skip depot
                    continue

                member = members[idx - 1]

                tripData["members"].append({
                    **member,
                    "stopNum": stopNum,
                    "pickup": cumulativeTime[stopNum].strftime("%I:%M %p"),
                    "arrival": totalTime.strftime("%I:%M %p")
                })

            trips.append(tripData)

    return trips

def cluster(filePath, initialTime, insurance, statusLabel, stopFlag, callback):
    try:
        statusLabel.configure(text=f"Retrieving Members...")
        statusLabel.update() 
        depot, vehicles, members = getMembersFromExcel(filePath, initialTime, insurance, stopFlag)
        if not members:
            raise ValueError("Missing data")
        
        statusLabel.configure(text=f"Setting Wedges...")
        statusLabel.update()
        wedgeRoutes = routeByWedges(members, depot, vehicles, statusLabel, stopFlag)

        statusLabel.configure(text=f"Processing Data...")
        statusLabel.update()
        routesData = processRouteData(wedgeRoutes, initialTime, stopFlag)

        statusLabel.configure(text=f"Plotting Map...")
        statusLabel.update()
        map = plotCoordinatesOnMap(depot, routesData, initialTime, stopFlag)

        statusLabel.configure(text=f"Preparing Excel...")
        statusLabel.update()
        excel = exportMembersToExcel(routesData, stopFlag)

        callback(map, excel, error=None)

    except Exception as e:
        print("An error occurred:", str(e))
        traceback.print_exc()
        callback(mapHtml=None, excelBytes=None, error=str(e))