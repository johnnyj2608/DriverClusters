from excel import getMembersFromExcel
from cvrp import computeRoutes
from plot import plotCoordinatesOnMap

def cluster(filePath, date, insurance, stopFlag, callback):
    try:
        depot, vehicles, members = getMembersFromExcel(filePath, date, insurance, stopFlag)
        if not members:
            raise ValueError("Missing data")
        
        vehicleCapacities = []
        for vehicle in vehicles:
            capacity = vehicle["capacity"]
            vehicleCapacities.append(capacity)
        
        routes = computeRoutes(depot, vehicleCapacities, members)
        m = plotCoordinatesOnMap(depot, members, routes=routes)
        
        month = str(date.month)
        day = str(date.day)
        year = str(date.year % 100)
        dateStr = f"{month}.{day}.{year}"
        insuranceStr = insurance.replace(" ", "_")
        filename = f"{insuranceStr}-{dateStr}.html"
        m.save(filename)

        callback(error=None)

    except Exception as e:
        print("An error occurred:", str(e))
        callback(error=str(e))