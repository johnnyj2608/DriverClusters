# Capacitated Vehicle Routing Problem

import time
import requests
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

# -----------------------------
# OSRM road-network distance
# -----------------------------
def getDistanceTimeMatrix(locations, retries=3, pause=5):
    coordsStr = ";".join([f"{lon},{lat}" for lat, lon in locations])
    url = f"https://router.project-osrm.org/table/v1/driving/{coordsStr}?annotations=distance,duration"

    for attempt in range(1, retries+1):
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
            print(f"OSRM attempt {attempt} failed: {e}")
            if attempt < retries:
                time.sleep(pause)
            else:
                raise RuntimeError(f"OSRM failed after {retries} attempts")

# -----------------------------
# Compute vehicle routes
# -----------------------------
def computeRoutes(
        mandatory, 
        optional, 
        depot, 
        vehicles,
        distanceMatrix=None,
        timeMatrix=None
    ):
    allMembers = mandatory + optional
    mandatoryCount = len(mandatory)

    locations = [depot] + [(m['lat'], m['lon']) for m in allMembers]
    demands = [0] + [int(m.get('demand', 1)) for m in allMembers]

    if distanceMatrix is None or timeMatrix is None:
        distanceMatrix, timeMatrix = getDistanceTimeMatrix(locations)

    numVehicles = len(vehicles)
    vehicleCapacities = [v["capacity"] for v in vehicles]

    mandatoryDemand = sum(demands[1:mandatoryCount + 1])
    totalCapacity = sum(vehicleCapacities)
    if mandatoryDemand > totalCapacity:
        raise ValueError("Not enough capacity")

    manager = pywrapcp.RoutingIndexManager(len(distanceMatrix), numVehicles, 0)
    routing = pywrapcp.RoutingModel(manager)

    def timeCallback(fromIndex, toIndex):
        return int(timeMatrix[manager.IndexToNode(fromIndex)][manager.IndexToNode(toIndex)])

    timeCallbackIndex = routing.RegisterTransitCallback(timeCallback)
    routing.SetArcCostEvaluatorOfAllVehicles(timeCallbackIndex)

    # Capacity callback
    def demandCallback(fromIndex):
        return demands[manager.IndexToNode(fromIndex)]
    demandCallbackIndex = routing.RegisterUnaryTransitCallback(demandCallback)
    routing.AddDimensionWithVehicleCapacity(
        demandCallbackIndex,
        0,
        vehicleCapacities,
        True,
        'Capacity'
    )

    for i in range(mandatoryCount + 1, len(allMembers) + 1):
        index = manager.NodeToIndex(i)
        penalty = 1000 + int(distanceMatrix[0][i] / 10)
        routing.AddDisjunction([index], penalty)

    searchParameters = pywrapcp.DefaultRoutingSearchParameters()
    searchParameters.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
    solution = routing.SolveWithParameters(searchParameters)

    routes = []
    usedNodes = set()

    if solution:
        for v in range(numVehicles):
            index = routing.Start(v)
            route = []

            while not routing.IsEnd(index):
                node = manager.IndexToNode(index)
                route.append(node)

                if node != 0:
                    usedNodes.add(node)

                index = solution.Value(routing.NextVar(index))

            route.append(0)

            if len(route) > 2:
                routes.append(route)

    nodeToMember = {i + 1: m for i, m in enumerate(allMembers)}

    leftoverMembers = {
        id(allMembers[i])
        for i in range(mandatoryCount, len(allMembers))
        if (i + 1) not in usedNodes
    }

    def depotDistance(node):
        return distanceMatrix[0][node]

    cleanedRoutes = []
    for route in routes:
        internalNodes = [n for n in route if n != 0]
        internalNodes.sort(key=depotDistance, reverse=True)
        cleanedRoutes.append(internalNodes)

    return cleanedRoutes, timeMatrix, nodeToMember, leftoverMembers