import traceback
import random
from datetime import timedelta
from utils import sliceMatrixWedge, computeTimes
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
    innerRadius, innerAngle, outerSplits = 2000, 90, 3
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

            routes, times, assigned, leftover = computeRoutes(
                wedgeMembers,
                optionalMembers,
                depot,
                vehiclesList,
                distanceMatrix=distanceMatrix,
                timeMatrix=timeMatrix
            )

            allRoutes.append({
                "members": assigned,
                "routes": routes,
                "times": times,
                "vehicles": vehiclesList
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
            
            randomDelay = random.randint(0, 5)
            inboundStartTime = inboundEndTimes.get(
                vehicleId, 
                initialTime + timedelta(minutes=randomDelay))
            inboundTimes, inboundEndTime = computeTimes(route, times, inboundStartTime, reverse=False)
            inboundEndTimes[vehicleId] = inboundEndTime

            randomDelay = random.randint(0, 5)
            noonTime = initialTime.replace(hour=12, minute=0, second=0, microsecond=0)
            outboundStartTime = outboundEndTimes.get(
                vehicleId,
                max(noonTime, inboundEndTime + timedelta(hours=4)) + timedelta(minutes=randomDelay)
            )
            outboundTimes, outboundEndTime = computeTimes(route, times, outboundStartTime, reverse=True)
            outboundEndTimes[vehicleId] = outboundEndTime

            for stopNum, idx in enumerate(route):
                if idx == 0:  # skip depot
                    continue

                member = members[idx - 1]

                tripData["members"].append({
                    **member,
                    "stopNum": stopNum,

                    # Inbound
                    "homePickupTime": inboundTimes[stopNum],
                    "depotArrivalTime": inboundEndTime,

                    # Outbound
                    "depotDepartTime": outboundStartTime,
                    "homeArrivalTime": outboundTimes[stopNum]
                })

            trips.append(tripData)

    return trips

def generateRoutes(filePath, initialTime, insurance, statusLabel, stopFlag, callback):
    try:
        statusLabel.configure(text=f"Retrieving Members...")
        statusLabel.update() 
        depot, vehicles, members = getMembersFromExcel(filePath, initialTime, insurance, stopFlag)
        if not members:
            raise ValueError("Missing data")
        
        statusLabel.configure(text=f"Setting Wedges...")
        statusLabel.update()
        wedgeRoutes = routeByWedges(members, depot, vehicles, stopFlag)

        statusLabel.configure(text=f"Processing Data...")
        statusLabel.update()
        routesData = processRouteData(wedgeRoutes, initialTime, stopFlag)

        statusLabel.configure(text=f"Plotting Map...")
        statusLabel.update()
        mapHtml = plotCoordinatesOnMap(depot, routesData, initialTime, stopFlag)

        statusLabel.configure(text=f"Preparing Excel...")
        statusLabel.update()
        excelBytes = exportMembersToExcel(routesData, stopFlag)

        callback(mapHtml, excelBytes, error=None)

    except Exception as e:
        print("An error occurred:", str(e))
        traceback.print_exc()
        callback(mapHtml=None, excelBytes=None, error=str(e))