import traceback
from datetime import timedelta
from utils import getRandomDelay, sliceMatrixWedge, computeTimes
from excel import getMembersFromExcel, exportMembersToExcel
from cvrp import getDistanceTimeMatrix, computeRoutes
from plot import plotCoordinatesOnMap
from cluster import (
    buildCityClusters,
    mergeCityToWedges,
    calcMemberWedges,
    calcVehicleWedges,
)

def routeByWedges(members, depot, vehicles, stopFlag):
    innerRadius, innerAngle, outerSplits = 1000, 90, 3
    cityClusters = buildCityClusters(members)
    mainMembers = cityClusters.pop("MAIN")["members"]
    memberWedges = calcMemberWedges(mainMembers, depot, innerRadius, innerAngle, outerSplits, stopFlag)
    outerWedges = memberWedges["outer"]
    innerWedges = memberWedges["inner"]

    locations = [depot] + [(m['lat'], m['lon']) for m in members]
    fullDistanceMatrix, fullTimeMatrix = getDistanceTimeMatrix(locations)
    memberToIndex = {id(m): i + 1 for i, m in enumerate(members)}

    allRoutes = []

    def processWedges(wedges, vehiclesMap, includeInner=False):
        for wedge, vehiclesList in vehiclesMap.items():
            if stopFlag.value:
                return None

            if not vehiclesList:
                continue

            wedgeMembers = wedges[wedge]["members"]

            optionalMembers = []
            if includeInner:
                sliceAngle = innerAngle / outerSplits
                centerAngle = (wedge + 0.5) * sliceAngle

                halfWindow = 45

                start = (centerAngle - halfWindow) % 360
                end = (centerAngle + halfWindow) % 360

                def inWindow(b):
                    if start < end:
                        return start <= b <= end
                    else:
                        return b >= start or b <= end
                    
                innerIdx = wedge // outerSplits
                numFans = len(innerWedges)

                candidateIndices = [
                    innerIdx,
                    (innerIdx - 1) % numFans,
                    (innerIdx + 1) % numFans
                ]

                for idx in candidateIndices:
                    for m in innerWedges[idx]["members"]:
                        if inWindow(m["bearing"]):
                            optionalMembers.append(m)

            if not wedgeMembers and not optionalMembers:
                continue

            distanceMatrix, timeMatrix = sliceMatrixWedge(
                fullDistanceMatrix,
                fullTimeMatrix,
                wedgeMembers=wedgeMembers + optionalMembers,
                memberToIndex=memberToIndex
            )

            routes, times, nodeToMember, leftover = computeRoutes(
                wedgeMembers,
                optionalMembers,
                depot,
                vehiclesList,
                distanceMatrix=distanceMatrix,
                timeMatrix=timeMatrix
            )

            allRoutes.append({
                "routes": routes,
                "times": times,
                "nodeToMember": nodeToMember,
                "vehicles": vehiclesList,
            })

            if includeInner:
                for m in optionalMembers:
                    if id(m) in leftover:
                        continue  # not used, keep it

                    innerWedge = innerWedges[int(m["bearing"] // innerAngle)]
                    innerWedge["members"].remove(m)
                    innerWedge["count"] -= 1

    mergeCityToWedges(cityClusters, depot, outerWedges, innerAngle, outerSplits)
    outerVehicles = calcVehicleWedges(vehicles, outerWedges, stopFlag)
    innerVehicles = calcVehicleWedges(vehicles, innerWedges, stopFlag)

    processWedges(outerWedges, outerVehicles, includeInner=True)
    processWedges(innerWedges, innerVehicles, includeInner=False)

    return allRoutes

def processRouteData(wedgeRoutes, initialTime, stopFlag):
    trips = []
    inboundEndTimes = {}
    outboundEndTimes = {}

    for data in wedgeRoutes:
        if stopFlag.value: return None

        routes = data["routes"]
        vehicles = data["vehicles"]
        times = data["times"]
        nodeToMember = data["nodeToMember"]

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

            firstTrip = vehicleId not in inboundEndTimes
            inboundStartTime = inboundEndTimes.get(
                vehicleId, 
                initialTime + timedelta(seconds=getRandomDelay()))
            inboundTimes, inboundEndTime = computeTimes(route, times, inboundStartTime, skipDepot=firstTrip)
            inboundEndTimes[vehicleId] = inboundEndTime

            noonTime = initialTime.replace(hour=12, minute=0, second=0, microsecond=0)
            outboundStartTime = outboundEndTimes.get(
                vehicleId,
                max(noonTime, inboundEndTime + timedelta(hours=4)) + timedelta(seconds=getRandomDelay())
            )
            outboundTimes, outboundEndTime = computeTimes(route, times, outboundStartTime, reverse=True)
            outboundEndTimes[vehicleId] = outboundEndTime

            for stopNum, node in enumerate(route):
                member = nodeToMember.get(node)

                tripData["members"].append({
                    **member,
                    "stopNum": stopNum+1,

                    # Inbound
                    "homePickupTime": inboundTimes[stopNum],
                    "depotArrivalTime": inboundEndTime,

                    # Outbound
                    "depotDepartTime": outboundStartTime,
                    "homeArrivalTime": outboundTimes[stopNum]
                })

            trips.append(tripData)

    return trips

def generateRoutes(filePath, initialTime, insurance, stopFlag, progressCallback, completionCallback):
    try:
        progressCallback("Retrieving Members...")
        depot, vehicles, members = getMembersFromExcel(filePath, initialTime, insurance, stopFlag)
        if not members:
            raise ValueError("Missing data")

        progressCallback("Setting Wedges...")
        wedgeRoutes = routeByWedges(members, depot, vehicles, stopFlag)

        progressCallback("Processing Routes...")
        routesData = processRouteData(wedgeRoutes, initialTime, stopFlag)

        progressCallback("Plotting Map...")
        mapHtml = plotCoordinatesOnMap(depot, routesData, initialTime, stopFlag)

        progressCallback("Preparing Excel...")
        excelBytes = exportMembersToExcel(routesData, stopFlag)

        completionCallback(mapHtml, excelBytes, error=None)

    except Exception as e:
        traceback.print_exc()
        completionCallback(mapHtml=None, excelBytes=None, error=str(e))