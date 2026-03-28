import folium

def plotCoordinatesOnMap(depot, vehicles, members, routes):
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
    for i, route in enumerate(routes):
        memberCount = len(route) - 1    # subtract depot
        fg = folium.FeatureGroup(
            name=f"{vehicles[i]['name']} ({memberCount}/{vehicles[i]['capacity']})"
        )
        for idx in route:
            if idx == 0:
                continue
            member = members[idx - 1]   # route indexes 0 as depot
            folium.Marker(
                location=(member['latitude'], member['longitude']),
                popup=folium.Popup(member['name'], max_width=300),
                icon=folium.Icon(color="blue", icon="home")
            ).add_to(fg)
        fg.add_to(m)

    folium.LayerControl(collapsed=False).add_to(m)
    return m