import folium

def plotCoordinatesOnMap(members):
    if len(members) > 0:
        avgLat = sum(member['latitude'] for member in members) / len(members)
        avgLon = sum(member['longitude'] for member in members) / len(members)
        m = folium.Map(location=[avgLat, avgLon], zoom_start=12, tiles='Cartodb Positron')
    else:
        m = folium.Map(location=[40.7128, -74.0060], zoom_start=12, tiles='Cartodb Positron')

    for member in members:
        folium.Marker(
            location=[member['latitude'], member['longitude']],
            popup=folium.Popup(f"<strong>{member['name']}</strong>", max_width=300),
            icon=folium.Icon(color="blue", icon="info-sign")
        ).add_to(m)

    m.save('membersMap.html')
    print("Map saved as 'membersMap.html'. Open it in a browser.")