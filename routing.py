def getRouteMemberData(trip, route, members, vehicles, times):
    data = []
    carId = vehicles[trip]["carId"]
    driver = vehicles[trip]["driver"]
    
    for stopNum, idx in enumerate(route):
        if idx == 0:
            continue    # Depot

        member = members[idx - 1]
        pickupTime = times[trip][stopNum]
        arrivalTime = times[trip][-1]

        data.append({
            "member": member,
            "carId": carId,
            "driver": driver,
            "stopNum": stopNum,
            "pickup": pickupTime,
            "arrival": arrivalTime
        })
    
    return data

def convertSeconds(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    time = f"{hours:02d}:{minutes:02d}"

    return time