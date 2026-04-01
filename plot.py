import io
import folium

maxWaypoints = 10

def generateGoogleMapsHtml(depot, trip):
    links = []
    
    coords = [(depot[0], depot[1])]
    for member in trip:
        coords.append((member["latitude"], member["longitude"]))

    for i in range(0, len(coords), maxWaypoints):
        batch = coords[i:i + maxWaypoints]

        addresses = []
        for coord in batch:
            lat = coord[0]
            lon = coord[1]
            addresses.append(f"{lat},{lon}")
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

def plotCoordinatesOnMap(depot, routesData, stopFlag):
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
    for trip in routesData:
        if stopFlag.value: return None
        fg = folium.FeatureGroup(
            name=f"{trip['driver']} ({len(trip['members'])}/{trip['capacity']})"
        )

        links = generateGoogleMapsHtml(depot, trip["members"])
        for member in trip["members"]:
            text = (
                f"<strong>{member['name']}</strong><br>"
                f"{trip['driver']} | Stop #{member['stopNum']}<br>"
                f"{links}"
            )

            folium.Marker(
                location=(member["latitude"], member["longitude"]),
                popup=folium.Popup(text, max_width=400),
                icon=folium.Icon(color="blue", icon="home")
            ).add_to(fg)

        fg.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)

    mapFile = io.BytesIO()
    m.save(mapFile, close_file=False)
    mapHtml = mapFile.getvalue().decode('utf-8')

    return mapHtml