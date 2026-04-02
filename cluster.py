import traceback
from datetime import timedelta
from excel import getMembersFromExcel, exportMembersToExcel
from cvrp import computeRoutes
from plot import plotCoordinatesOnMap

def quadrantMembers(members, depot):
    depotLat, depotLon = depot
    quadrants = {
        "NE": {"members": [], "count": 0},
        "NW": {"members": [], "count": 0},
        "SE": {"members": [], "count": 0},
        "SW": {"members": [], "count": 0}
    }

    for m in members:
        if m["lat"] >= depotLat and m["lon"] >= depotLon:
            quadrant = "NE"
        elif m["lat"] >= depotLat and m["lon"] < depotLon:
            quadrant = "NW"
        elif m["lat"] < depotLat and m["lon"] >= depotLon:
            quadrant = "SE"
        else:
            quadrant = "SW"

        quadrants[quadrant]["members"].append(m)
        quadrants[quadrant]["count"] += 1

    return quadrants

def quadrantVehicles(quadrants, vehicles):
    vehicleList = vehicles.copy()
    vehicleList.sort(key=lambda v: v["capacity"])

    totalMembers = 0
    for q in quadrants.values():
        totalMembers += q["count"]

    assignments = {}
    for q in quadrants:
        assignments[q] = []
        
    tripNumber = 1

    while totalMembers > 0:
        vehiclesBatch = vehicleList.copy()

        while vehiclesBatch:
            vehicle = vehiclesBatch.pop()

            bestQ = None
            smallestDiff = None

            for q in quadrants:
                remaining = quadrants[q]["count"]
                if remaining <= 0:
                    continue

                diff = vehicle["capacity"] - remaining
                if bestQ is None or diff < smallestDiff:
                    bestQ = q
                    smallestDiff = diff
                    if diff == 0:
                        break

            if bestQ is None:
                break

            assignments[bestQ].append({
                **vehicle,
                "trip": tripNumber
            })

            assignedCount = min(vehicle["capacity"], quadrants[bestQ]["count"])
            quadrants[bestQ]["count"] -= assignedCount
            totalMembers -= assignedCount
        tripNumber += 1

    return assignments

def routeByQuadrant(members, depot, vehicles, stopFlag):
    assignedMembers = quadrantMembers(members, depot)
    assignedVehicles = quadrantVehicles(assignedMembers, vehicles)

    quadrantRoutes = {}

    for quadrant, vehiclesList in assignedVehicles.items():
        if stopFlag.value: return None

        membersList = assignedMembers[quadrant]["members"]

        if not membersList or not vehiclesList:
            continue

        vehicleCapacities = []
        for v in vehiclesList:
            vehicleCapacities.append(v["capacity"])

        routes, times = computeRoutes(
            membersList,
            depot,
            vehicleCapacities
        )

        quadrantRoutes[quadrant] = {
            "members": membersList,
            "routes": routes,
            "times": times,
            "vehicles": vehiclesList
        }

    return quadrantRoutes

def processQuadrantData(quadrantRoutes, datetime, stopFlag):
    trips = []
    arrivalTimes = {}

    for data in quadrantRoutes.values():
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

        statusLabel.configure(text=f"Setting Quadrants...")
        statusLabel.update()
        quadrantRoutes = routeByQuadrant(members, depot, vehicles, stopFlag)

        statusLabel.configure(text=f"Processing Data...")
        statusLabel.update()
        routesData = processQuadrantData(quadrantRoutes, datetime, stopFlag)

        statusLabel.configure(text=f"Plotting Map...")
        statusLabel.update()
        map = plotCoordinatesOnMap(depot, routesData, stopFlag)

        statusLabel.configure(text=f"Preparing Excel...")
        statusLabel.update()
        excel = exportMembersToExcel(routesData, stopFlag)
        
        callback(map, excel, error=None)

    except Exception as e:
        print("An error occurred:", str(e))
        traceback.print_exc()
        callback(mapHtml=None, excelBytes=None, error=str(e))