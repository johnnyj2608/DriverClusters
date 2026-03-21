import folium
from collections import defaultdict

def plotCoordinatesOnMap(depot, members, routes=None):
    center = (40.650002, -73.949997)    # NYC
    m = folium.Map(location=center, zoom_start=12, tiles='Cartodb Positron')

    folium.Marker(
        location=depot,
        popup=folium.Popup("<strong>Depot</strong>", max_width=300),
        icon=folium.Icon(color="red", icon="star")
    ).add_to(m)

    grouped = defaultdict(list)
    for member in members:
        key = (member['latitude'], member['longitude'])
        grouped[key].append(member)

    for (lat, lon), group in grouped.items():
        names = [m['name'] for m in group]
        popup_html = "<br>".join(names)

        folium.Marker(
            location=(lat, lon),
            popup=folium.Popup(popup_html, max_width=300),
            icon=folium.Icon(color="blue", icon="home")
        ).add_to(m)

    return m