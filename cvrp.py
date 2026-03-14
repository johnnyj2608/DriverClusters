# Capacitated Vehicle Routing Problem

from ortools.constraint_solver import routing_enums_pb2
from ortools.constraint_solver import pywrapcp
import math

# -----------------------------
# Haversine distance
# -----------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda/2)**2
    return R * 1000 * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))  # meters

# -----------------------------
# Create distance matrix
# -----------------------------
def createDistanceMatrix(locations):
    size = len(locations)
    distanceMatrix = []
    for i in range(size):
        row = []
        for j in range(size):
            row.append(int(haversine(locations[i][0], locations[i][1],
                                     locations[j][0], locations[j][1])))
        distanceMatrix.append(row)
    return distanceMatrix

# -----------------------------
# Compute vehicle routes
# -----------------------------
def computeRoutes(members, vehicleSize=7, depotIndex=0):
    if not members:
        return []

    locations = [(0,0)] + [(m['latitude'], m['longitude']) for m in members]
    demands = [0] + [m.get('demand', 1) for m in members]
    distanceMatrix = createDistanceMatrix(locations)

    # Number of vehicles = ceil(total demand / vehicleSize)
    totalDemand = sum(demands)
    numVehicles = max(1, math.ceil(totalDemand / vehicleSize))

    manager = pywrapcp.RoutingIndexManager(len(distanceMatrix), numVehicles, depotIndex)
    routing = pywrapcp.RoutingModel(manager)

    # Distance callback
    def distanceCallback(fromIndex, toIndex):
        return distanceMatrix[manager.IndexToNode(fromIndex)][manager.IndexToNode(toIndex)]
    routing.SetArcCostEvaluatorOfAllVehicles(routing.RegisterTransitCallback(distanceCallback))

    # Capacity callback
    def demandCallback(fromIndex):
        return demands[manager.IndexToNode(fromIndex)]
    demandCallbackIndex = routing.RegisterUnaryTransitCallback(demandCallback)
    routing.AddDimensionWithVehicleCapacity(
        demandCallbackIndex,
        0,
        [vehicleSize] * numVehicles,
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
    return routes