from excel import getMembersFromExcel
from cvrp import computeRoutes

def cluster(filePath, date, insurance, stopFlag, callback):
    try:
        members = getMembersFromExcel(filePath, date, insurance, stopFlag)
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

        callback(error=None)

    except Exception as e:
        print("An error occurred:", str(e))
        callback(error=str(e))