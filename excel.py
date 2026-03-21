import psutil

import pandas as pd
import xlwings as xw
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

def getMembersFromExcel(filePath, date, insurance, stopFlag):
        app = xw.App(visible=False)

        try:
            wb = xw.Book(filePath, ignore_read_only_recommended=True)
            members = []
            weekday = date.weekday()+1 

            setup = wb.sheets['Setup']
            lat = setup.range("A5").value
            lon = setup.range("B5").value
            sheet = wb.sheets[insurance]

            dataRange = sheet.range('A1:I1').expand('down').value
            if not any(isinstance(i, list) for i in dataRange):
                return []
            df = pd.DataFrame(dataRange[1:], columns=dataRange[0])
            df['DoB'] = pd.to_datetime(df['DoB'], errors='coerce')
            df = df.replace({float('nan'): None})

            mandatory_fields = ['ID', 'Name', 'DoB', 'Schedule', 'Address', 'City', 'Zip Code']
            if df[mandatory_fields].isna().any().any():
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

                if str(weekday) in member['schedule']:
                    members.append(member)
            
            wb.save() 
            
        except FileNotFoundError:
            print(f"File not found.")
        finally:
            app.quit()

        return (lat, lon), members

geolocator = Nominatim(user_agent="driverclusters_app")
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

def writeCoordinate(address, city, zip_code):
    try:
        full_address = f"{address}, {city}, {zip_code}"
        location = geocode(full_address)

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