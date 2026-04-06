import math
import traceback
from collections import defaultdict
from datetime import timedelta
from excel import getMembersFromExcel, exportMembersToExcel
from cvrp import computeRoutes
from plot import plotCoordinatesOnMap

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2*R*math.atan2(math.sqrt(a), math.sqrt(1-a))

def depotBearing(depot, member):
    lat1, lon1 = math.radians(depot[0]), math.radians(depot[1])
    lat2, lon2 = math.radians(member['lat']), math.radians(member['lon'])
    dLon = lon2 - lon1
    x = math.sin(dLon) * math.cos(lat2)
    y = math.cos(lat1)*math.sin(lat2) - math.sin(lat1)*math.cos(lat2)*math.cos(dLon)
    bearing = math.atan2(x, y)
    return (math.degrees(bearing) + 360) % 360

def calcMemberWedges(
        members, 
        depot, 
        innerRadius, 
        innerAngle, 
        outerSplits,
        stopFlag, 
    ):
    numFans = int(360 / innerAngle)
    totalOuterWedges = numFans * outerSplits

    wedges = {
        "inner": {},
        "outer": {},
        "count": 0,
    }

    for i in range(numFans):
        wedges["inner"][i] = {"members": [], "count": 0}

    # Initialize outer wedges
    for i in range(totalOuterWedges):
        wedges["outer"][i] = {"members": [], "count": 0}

    sliceAngle = innerAngle / outerSplits

    for m in members:
        if stopFlag.value: return None

        dist = haversine(depot[0], depot[1], m['lat'], m['lon'])
        bearing = depotBearing(depot, m)

        # Determine which fan the member belongs to (0°, 90°, 180°, 270°)
        fanIndex = int(bearing // innerAngle)
        fanStart = fanIndex * innerAngle

        # Angle relative to the start of the fan
        diff = (bearing - fanStart + 360) % 360

        if dist <= innerRadius:
            wedges["inner"][fanIndex]["members"].append(m)
            wedges["inner"][fanIndex]["count"] += 1
        else:
            splitIndex = int(diff // sliceAngle)
            splitIndex = min(splitIndex, outerSplits - 1)
            wedgeIndex = fanIndex * outerSplits + splitIndex
            wedges["outer"][wedgeIndex]["members"].append(m)
            wedges["outer"][wedgeIndex]["count"] += 1
        wedges["count"] += 1

    return wedges

def calcVehicleWedges(vehicles, wedges, outerSplits, stopFlag):
    vehicleList = vehicles.copy()
    vehicleList.sort(key=lambda v: v["capacity"])
    
    innerWedges = wedges["inner"]
    outerWedges = wedges["outer"]
    totalMembers = wedges["count"]

    assignments = defaultdict(list)
    tripNumber = 1

    while totalMembers > 0:
        vehiclesBatch = vehicleList.copy()

        while vehiclesBatch:
            if stopFlag.value: return None
            vehicle = vehiclesBatch.pop()

            bestWedge = None
            minDiff = None

            for w in outerWedges:
                remaining = outerWedges[w]["count"]
                if remaining <= 0:
                    continue

                diff = vehicle["capacity"] - remaining
                if bestWedge is None or diff < minDiff:
                    bestWedge = w
                    minDiff = diff
                    if diff == 0:
                        break

            if bestWedge is None:
                break   # Need a way to pick up only inner members if outer is done

            assignedCount = min(vehicle["capacity"], outerWedges[bestWedge]["count"])
            outerWedges[bestWedge]["count"] -= assignedCount
            totalMembers -= assignedCount

            innerAssigned = 0
            leftoverCap = vehicle["capacity"] - assignedCount
            if leftoverCap > 0:
                innerIndex = bestWedge % outerSplits
                innerRemaining = innerWedges[innerIndex]["count"]
                innerAssigned = min(leftoverCap, innerRemaining)

                innerWedges[innerIndex]["count"] -= innerAssigned
                totalMembers -= innerAssigned

            assignments[bestWedge].append({
                **vehicle,
                "trip": tripNumber,
                "innerCount": innerAssigned
            })

        tripNumber += 1

    return assignments

def routeByWedges(members, depot, vehicles, statusLabel, stopFlag):
    innerRadius, innerAngle, outerSplits = 500, 90, 3
    memberWedges = calcMemberWedges(members, depot, innerRadius, innerAngle, outerSplits, stopFlag)
    vehicleWedges = calcVehicleWedges(vehicles, memberWedges, outerSplits, stopFlag)

    wedgeRoutes = {}
    totalWedges = len(vehicleWedges)
    
    for i, (wedge, vehiclesList) in enumerate(vehicleWedges.items(), start=1):
        if stopFlag.value: return None

        if not vehiclesList:
            continue

        vehicleCapacities, innerCount = [], 0
        for v in vehiclesList:
            vehicleCapacities.append(v["capacity"])
            innerCount += v["innerCount"]

        membersList = memberWedges["outer"][wedge]["members"]
        innerMembers = memberWedges["inner"][wedge % outerSplits]["members"]
        for _ in range(innerCount):
            membersList.append(innerMembers.pop())

        if not membersList:
            continue

        statusLabel.configure(text=f"Setting Wedge {i}/{totalWedges}...")
        statusLabel.update()
        routes, times = computeRoutes(
            membersList,
            depot,
            vehicleCapacities
        )

        wedgeRoutes[wedge] = {
            "members": membersList,
            "routes": routes,
            "times": times,
            "vehicles": vehiclesList
        }

    return wedgeRoutes

def processRouteData(wedgeRoutes, datetime, stopFlag):
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

            startTime = arrivalTimes.get(vehicleId, datetime)

            tripData = {
                "driver": vehicle["driver"],
                "carId": vehicle["carId"],
                "capacity": vehicle["capacity"],
                "trip": vehicle["trip"],
                "members": []
            }

            cumulativeTime = [startTime]
            totalTime = startTime

            # Compute cumulative times along the route
            for i in range(1, len(route)):
                prevIdx = route[i - 1]
                currIdx = route[i]
                seconds = times[prevIdx][currIdx] if times else 0
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
                    "arrival": cumulativeTime[-1].strftime("%I:%M %p")
                })

            trips.append(tripData)

    return trips

def cluster(filePath, datetime, insurance, statusLabel, stopFlag, callback):
    try:
        statusLabel.configure(text=f"Retrieving Members...")
        statusLabel.update() 
        depot, vehicles, members = getMembersFromExcel(filePath, datetime, insurance, stopFlag)
        if not members:
            raise ValueError("Missing data")
        
        statusLabel.configure(text=f"Setting Wedges...")
        statusLabel.update()
        wedgeRoutes = routeByWedges(members, depot, vehicles, statusLabel, stopFlag)

        statusLabel.configure(text=f"Processing Data...")
        statusLabel.update()
        routesData = processRouteData(wedgeRoutes, datetime, stopFlag)

        statusLabel.configure(text=f"Plotting Map...")
        statusLabel.update()
        map = plotCoordinatesOnMap(depot, routesData, datetime, stopFlag)

        statusLabel.configure(text=f"Preparing Excel...")
        statusLabel.update()
        excel = exportMembersToExcel(routesData, stopFlag)

        callback(map, excel, error=None)

    except Exception as e:
        print("An error occurred:", str(e))
        traceback.print_exc()
        callback(mapHtml=None, excelBytes=None, error=str(e))