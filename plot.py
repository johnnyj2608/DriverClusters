import folium
from collections import defaultdict

def plotCoordinatesOnMap(members, filename='map.html'):
    center = [40.650002, -73.949997]    # Depot
    m = folium.Map(location=center, zoom_start=12, tiles='Cartodb Positron')

    grouped = defaultdict(list)

    for member in members:
        key = (member['latitude'], member['longitude'])
        grouped[key].append(member)

    for (lat, lon), group in grouped.items():
        names = [m['name'] for m in group]
        popup_html = "<br>".join(names)

        folium.Marker(
            location=[lat, lon],
            popup=folium.Popup(popup_html, max_width=300),
            icon=folium.Icon(color="blue", icon="info-sign")
        ).add_to(m)

    m.save(filename)
    print(f"Map saved as '{filename}'.")