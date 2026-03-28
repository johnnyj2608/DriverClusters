import io
from excel import getMembersFromExcel, exportMembersToExcel
from cvrp import computeRoutes
from plot import plotCoordinatesOnMap

def calculateDriveTime(route, times):
    cumulativeTime = [0]
    totalTime = 0

    for stopNum in range(1, len(route)):
        prevIdx = route[stopNum - 1]
        currIdx = route[stopNum]
        seconds = times[prevIdx][currIdx] if times else 0
        totalTime += seconds
        cumulativeTime.append(totalTime)

    return cumulativeTime

def cluster(filePath, date, insurance, stopFlag, callback):
    try:
        depot, vehicles, members = getMembersFromExcel(filePath, date, insurance, stopFlag)
        if not members:
            raise ValueError("Missing data")
        
        vehicleCapacities = []
        for vehicle in vehicles:
            capacity = vehicle["capacity"]
            vehicleCapacities.append(capacity)
        
        routes, timeMatrix = computeRoutes(members, depot, vehicleCapacities)

        times = {}
        for i, route in enumerate(routes):
            times[i] = calculateDriveTime(route, timeMatrix)

        m = plotCoordinatesOnMap(members, depot, vehicles, routes, times)

        e = exportMembersToExcel(members, vehicles, routes, times)
        print(e)
        
        map_file = io.BytesIO()
        m.save(map_file, close_file=False)
        mapHtml = map_file.getvalue().decode('utf-8')

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
        callback(mapHtml=None, error=str(e))