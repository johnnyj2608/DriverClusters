# Capacitated Vehicle Routing Problem

import math
import requests
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

# -----------------------------
# Haversine backup
# -----------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000  # meters

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def getHaversineMatrix(locations):
    n = len(locations)
    distances = [[0] * n for _ in range(n)]
    durations = [[0] * n for _ in range(n)]

    avg_speed_mps = 8.33  # about 30 km/h

    for i in range(n):
        lat1, lon1 = locations[i]
        for j in range(n):
            if i == j:
                continue

            lat2, lon2 = locations[j]
            d = haversine(lat1, lon1, lat2, lon2)

            distances[i][j] = int(d)
            durations[i][j] = int(d / avg_speed_mps)

    return distances, durations

# -----------------------------
# OSRM road-network distance
# -----------------------------
def getDistanceAndTimeMatrix(locations):
    coordsStr = ";".join([f"{lon},{lat}" for lat, lon in locations])
    url = f"https://router.project-osrm.org/table/v1/driving/{coordsStr}?annotations=distance,duration"

    try:
        r = requests.get(
            url,
            timeout=(10, 60),
            headers={"User-Agent": "driverclusters/1.0"}
        )
        r.raise_for_status()
        data = r.json()

        if "distances" not in data or "durations" not in data:
            raise ValueError("OSRM request failed: " + str(data))

        return data["distances"], data["durations"]

    except Exception as e:
        print(f"OSRM failed, using Haversine backup: {e}")
        return getHaversineMatrix(locations)

# -----------------------------
# Compute vehicle routes
# -----------------------------
def computeRoutes(members, depot, vehicles):
    if not members:
        return []

    locations = [depot] + [(m['lat'], m['lon']) for m in members]
    demands = [0] + [int(m.get('demand', 1)) for m in members]
    distanceMatrix, timeMatrix = getDistanceAndTimeMatrix(locations)

    numVehicles = len(vehicles)

    manager = pywrapcp.RoutingIndexManager(len(distanceMatrix), numVehicles, 0)
    routing = pywrapcp.RoutingModel(manager)

    # Distance callback
    def distanceCallback(fromIndex, toIndex):
        return int(distanceMatrix[manager.IndexToNode(fromIndex)][manager.IndexToNode(toIndex)])
    transitCallbackIndex = routing.RegisterTransitCallback(distanceCallback)
    routing.SetArcCostEvaluatorOfAllVehicles(transitCallbackIndex)

    # Capacity callback
    def demandCallback(fromIndex):
        return demands[manager.IndexToNode(fromIndex)]
    demandCallbackIndex = routing.RegisterUnaryTransitCallback(demandCallback)
    routing.AddDimensionWithVehicleCapacity(
        demandCallbackIndex,
        0,
        vehicles,
        True,
        'Capacity'
    )

    searchParameters = pywrapcp.DefaultRoutingSearchParameters()
    searchParameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    solution = routing.SolveWithParameters(searchParameters)

    routes = []
    if solution:
        for vehicleId in range(numVehicles):
            index = routing.Start(vehicleId)
            route = []
            while not routing.IsEnd(index):
                route.append(manager.IndexToNode(index))
                index = solution.Value(routing.NextVar(index))
            route.append(manager.IndexToNode(index))
            if route:
                routes.append(route)
    return routes, timeMatrix