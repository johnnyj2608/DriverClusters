import io
import traceback
from excel import getMembersFromExcel, exportMembersToExcel
from cvrp import computeRoutes
from plot import plotCoordinatesOnMap

def processRouteData(members, routes, vehicles, timeMatrix):
    trips = []

    for trip, route in enumerate(routes):
        tripData = {
            "driver": vehicles[trip]["driver"],
            "carId": vehicles[trip]["carId"],
            "capacity": vehicles[trip]["capacity"],
            "members": []
        }

        cumulativeTime = [0]
        totalTime = 0

        # Calculate drive times
        for i in range(1, len(route)):
            prevIdx = route[i - 1]
            currIdx = route[i]

            seconds = timeMatrix[prevIdx][currIdx] if timeMatrix else 0
            totalTime += seconds
            cumulativeTime.append(totalTime)

        for stopNum, idx in enumerate(route):
            if idx == 0:
                continue  # skip depot

            member = members[idx - 1]

            tripData["members"].append({
                **member,
                "stopNum": stopNum,
                "pickup": convertSeconds(cumulativeTime[stopNum]),
                "arrival": convertSeconds(cumulativeTime[-1])
            })

        trips.append(tripData)

    return trips

def convertSeconds(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    time = f"{hours:02d}:{minutes:02d}"

    return time

def cluster(filePath, date, insurance, stopFlag, callback):
    try:
        depot, vehicles, members = getMembersFromExcel(filePath, date, insurance, stopFlag)
        if not members:
            raise ValueError("Missing data")
        
        vehicleCapacities = []
        for vehicle in vehicles:
            capacity = vehicle["capacity"]
            vehicleCapacities.append(capacity)
        
        routes, times = computeRoutes(members, depot, vehicleCapacities)
        routesData = processRouteData(members, routes, vehicles, times)
        m = plotCoordinatesOnMap(depot, routesData)
        e = exportMembersToExcel(routesData)
        print(e)
        
        mapFile = io.BytesIO()
        m.save(mapFile, close_file=False)
        mapHtml = mapFile.getvalue().decode('utf-8')

        callback(mapHtml, error=None)

        # month = str(date.month)
        # day = str(date.day)
        # year = str(date.year % 100)
        # dateStr = f"{month}.{day}.{year}"
        # insuranceStr = insurance.replace(" ", "_")
        # filename = f"{insuranceStr}-{dateStr}.html"
        # m.save(filename)

    except Exception as e:
        print("An error occurred:", str(e))
        traceback.print_exc()
        callback(mapHtml=None, error=str(e))