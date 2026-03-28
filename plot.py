import folium
from routing import getRouteMemberData, convertSeconds

maxWaypoints = 10

def generateGoogleMapsHtml(depot, members, route):
    links = []
    memberIndexes = []

    for i in route:
        if i != 0:
            memberIndexes.append(i)

    for i in range(0, len(memberIndexes), maxWaypoints):
        batch = memberIndexes[i:i + maxWaypoints]
        addresses = [f"{depot[0]},{depot[1]}"]
        
        for idx in batch:
            member = members[idx - 1]
            addresses.append(f"{member['latitude']},{member['longitude']}")

        url = "https://www.google.com/maps/dir/" + "/".join(addresses)
        links.append(url)

    linksHtml = ""
    for i, link in enumerate(links):
        if len(links) > 1:
            text = f"Google Maps ({i+1}/{len(links)})"
        else:
            text = "Google Maps"
        
        if linksHtml:
            linksHtml += "<br>"
        linksHtml += f'<a href="{link}" target="_blank">{text}</a>'

    return linksHtml

def plotCoordinatesOnMap(members, depot, vehicles, routes, times):
    center = (40.650002, -73.949997)    # NYC
    m = folium.Map(location=center, zoom_start=12, tiles=None)
    folium.TileLayer('CartoDB Positron', control=False).add_to(m)

    # Depot marker
    folium.Marker(
        location=depot,
        popup=folium.Popup("<strong>Depot</strong>", max_width=300),
        icon=folium.Icon(color="red", icon="star")
    ).add_to(m)

    # Member markers
    for trip, route in enumerate(routes):
        routeData = getRouteMemberData(trip, route, members, vehicles, times)
        memberCount = len(route) - 1    # subtract depot
        fg = folium.FeatureGroup(
            name=f"{vehicles[trip]['driver']} ({memberCount}/{vehicles[trip]['capacity']})"
        )
        for item in routeData:
            member = item['member']
            stopNum = item['stopNum']
            totalSeconds = item['pickup']

            time = convertSeconds(totalSeconds)

            links = generateGoogleMapsHtml(depot, members, route)
            text = (
                f"<strong>{member['name']}</strong><br>"
                f"{vehicles[trip]['driver']} | Stop #{stopNum}<br>"
                f"Time: {time}<br>"
                f"{links}"
            )

            folium.Marker(
                location=(member['latitude'], member['longitude']),
                popup=folium.Popup(text, max_width=400),
                icon=folium.Icon(color="blue", icon="home")
            ).add_to(fg)
        fg.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    return m