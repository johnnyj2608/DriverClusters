# Capacitated Vehicle Routing Problem

import requests
from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp

# -----------------------------
# OSRM road-network distance
# -----------------------------
def getDistanceAndTimeMatrix(locations):
    coordsStr = ";".join([f"{lon},{lat}" for lat, lon in locations])
    url = f"http://router.project-osrm.org/table/v1/driving/{coordsStr}?annotations=distance,duration"
    r = requests.get(url)
    data = r.json()
    
    if "distances" not in data or "durations" not in data:
        raise ValueError("OSRM request failed: " + str(data))
    
    return data["distances"], data["durations"]

# -----------------------------
# Compute vehicle routes
# -----------------------------
def computeRoutes(members, depot, vehicles):
    if not members:
        return []

    locations = [depot] + [(m['latitude'], m['longitude']) for m in members]
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
            if route:
                routes.append(route)
    return routes, timeMatrix