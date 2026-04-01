import io
import psutil
import pandas as pd
import xlwings as xw
import openpyxl  # needed for pandas to_excel
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim

templateHeaders = {
    "A1": "ID",
    "B1": "Name",
    "C1": "DoB",
    "D1": "Schedule",
    "E1": "Address",
    "F1": "City",
    "G1": "Zip Code",
    "H1": "Latitude",
    "I1": "Longitude"
}

def validateExcelFile(filePath):
    app = xw.App(visible=False)

    try:
        wb = xw.Book(filePath, ignore_read_only_recommended=True)
        insurances = []

        if not handleSetupSheet(wb):
            raise ValueError("Missing or invalid Setup sheet")

        for sheet in wb.sheets:
            if sheet.name.strip().lower() == "setup":
                continue

            for cell, expected in templateHeaders.items():
                if sheet.range(cell).value != expected:
                    raise ValueError(f"Invalid template in sheet '{sheet.name}'")
            insurances.append(sheet.name.capitalize())
                
    except Exception as e:
        print(f"Error: {e}")
        return []
    finally:
        app.quit()

    return insurances

def handleSetupSheet(wb):
    try:
        setup = wb.sheets['Setup']
    except KeyError:
        print("Missing 'Setup' sheet in Excel file.")
        return False
    
    lat = setup.range("A5").value
    lon = setup.range("B5").value

    if not lat or not lon:
        address = setup.range("B2").value
        city = setup.range("B3").value
        zip = str(int(setup.range("B4").value))

        if not address or not city or not zip:
            return False

        latitude, longitude = writeCoordinate(address, city, zip)
        setup.range("A5").value = latitude
        setup.range("B5").value = longitude
        print(f"Setup coordinates written: {latitude}, {longitude}")

        wb.save()
    return True

def getSettingsFromExcel(wb):
    setup = wb.sheets['Setup']
    lat = setup.range("A5").value
    lon = setup.range("B5").value

    if lat is None or lon is None:
        raise ValueError("Depot coordinates missing")
    
    depot = (lat, lon)

    cars = setup.range("A9:C9").expand("down").value
    vehicles = []
    for row in cars:
        if not all(row[i] for i in range(3)):
            continue

        try:
            carId = row[0]
            if isinstance(carId, float) and carId.is_integer():
                carId = str(int(carId))
            else:
                carId = str(carId).strip()

            vehicle = {
                "carId": carId,
                "driver": str(row[1]).strip(),
                "capacity": int(row[2])
            }
            vehicles.append(vehicle)
        except:
            continue

    if not vehicles:
        raise ValueError("No vehicle data found in Setup sheet")

    return depot, vehicles

def getMembersFromExcel(filePath, date, insurance, stopFlag):
        app = xw.App(visible=False)
        modified = False

        try:
            wb = xw.Book(filePath, ignore_read_only_recommended=True)
            members = []
            weekday = date.weekday()+1 

            depot, vehicles = getSettingsFromExcel(wb)
            sheet = wb.sheets[insurance]

            dataRange = sheet.range('A1:I1').expand('down').value
            if not any(isinstance(i, list) for i in dataRange):
                return []
            df = pd.DataFrame(dataRange[1:], columns=dataRange[0])
            df['DoB'] = pd.to_datetime(df['DoB'], errors='coerce')
            df = df.replace({float('nan'): None})

            mandatoryFields = ['ID', 'Name', 'DoB', 'Schedule', 'Address', 'City', 'Zip Code']
            if df[mandatoryFields].isna().any().any():
                print("Missing mandatory data somewhere. Stopping early.")
                return []

            for idx, row in df.iterrows():
                if stopFlag.value: return []
                member = {
                    'id': str(int(row['ID'])),
                    'name': row['Name'],
                    'birthDate': row['DoB'],
                    'schedule': str(row['Schedule']),
                    'address': row['Address'],
                    'city': row['City'],
                    'zip': str(int(row['Zip Code'])),
                    'latitude': row['Latitude'],
                    'longitude': row['Longitude'],
                }
                if member['latitude'] == None or member['longitude'] == None:
                    lat, lon = writeCoordinate(member['address'], member['city'], member['zip'])
                    member['latitude'], member['longitude'] = lat, lon
                    sheet.range(f"H{idx+2}").value = lat
                    sheet.range(f"I{idx+2}").value = lon
                    modified = True

                if str(weekday) in member['schedule']:
                    members.append(member)
            
            if modified:
                wb.save() 
            
        except FileNotFoundError:
            print(f"File not found.")
        finally:
            app.quit()

        return depot, vehicles, members
        
def exportMembersToExcel(routesData, stopFlag):
    data = []

    for trip in routesData:
        if stopFlag.value: return None
        driver = trip["driver"]
        carId = trip["carId"]

        for member in trip["members"]:
            data.append({
                "ID": member.get("id"),
                "Name": member.get("name"),
                "Birth Date": member.get("birthDate"),
                "Schedule": member.get("schedule"),
                "Address": member.get("address"),
                "City": member.get("city"),
                "Zip": member.get("zip"),
                "Car": carId,
                "Driver": driver,
                "Pickup": member.get("pickup"),
                "Arrival": member.get("arrival"),
            })

    df = pd.DataFrame(data)
    df["ID"] = pd.to_numeric(df["ID"], errors="coerce")
    df = df.sort_values(by="ID")
    df["Birth Date"] = pd.to_datetime(df["Birth Date"], errors="coerce").dt.date
    df["Zip"] = df["Zip"].astype(str).str.zfill(5)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False)
    
    output.seek(0)
    return output

geolocator = Nominatim(user_agent="driverclusters_app")
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

def writeCoordinate(address, city, zip):
    try:
        fullAddress = f"{address}, {city}, {zip}"
        location = geocode(fullAddress)

        if location:
            return location.latitude, location.longitude
        else:
            return None, None
    except:
        return None, None

def ifExcelFileOpen(excelFile):
    for proc in psutil.process_iter():
        try:
            if 'EXCEL.EXE' in proc.name():
                for item in proc.open_files():
                    if excelFile.lower() in item.path.lower():
                        return True
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return False