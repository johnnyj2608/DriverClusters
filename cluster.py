from excel import getMembersFromExcel
from cvrp import computeRoutes
from plot import plotCoordinatesOnMap

def cluster(filePath, date, insurance, stopFlag, callback):
    try:
        depot, members = getMembersFromExcel(filePath, date, insurance, stopFlag)
        if not members:
            raise ValueError("Missing data")
        
        routes = computeRoutes(members, vehicleSize=4)
        
        print("Vehicle Routes")
        for vehicleId, route in enumerate(routes):
            routeMembers = []
            
            for idx in route:
                if idx != 0:
                    routeMembers.append(members[idx-1]['name'])
                
            routeStr = " → ".join(routeMembers)
            print(f"Vehicle {vehicleId+1} route: {routeStr}")

        m = plotCoordinatesOnMap(depot, members)
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