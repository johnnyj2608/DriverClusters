import psutil

import pandas as pd
import xlwings as xw

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
# Lock Excel headers

def validateExcelFile(filePath):
    app = xw.App(visible=False)

    try:
        wb = xw.Book(filePath, ignore_read_only_recommended=True)
        insurances = []

        for sheet in wb.sheets:
            for cell, expected in templateHeaders.items():
                if sheet.range(cell).value != expected:
                    print("Invalid template")
                    return []
            insurances.append(sheet.name.capitalize())
                
    except FileNotFoundError:
        print(f"File not found.")
    finally:
        app.quit()

    return insurances

def getMembersFromExcel(filePath, date, insurance, stopFlag):
        app = xw.App(visible=False)

        try:
            wb = xw.Book(filePath, ignore_read_only_recommended=True)
            members = []
            weekday = date.weekday()+1 

            for sheet in wb.sheets:
                if insurance == None or insurance.lower() in sheet.name.lower():
                    dataRange = sheet.range('A1:I1').expand('down').value
                    if not any(isinstance(i, list) for i in dataRange):
                        return []
                    df = pd.DataFrame(dataRange[1:], columns=dataRange[0])
                    df['DoB'] = pd.to_datetime(df['DoB'], errors='coerce')

                    for _, row in df.iterrows():
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
                            writeCoordinate(member['address'], member['city'], member['zip'])

                        if str(weekday) in member['schedule']:
                            members.append(member)
            
        except FileNotFoundError:
            print(f"File not found.")
        finally:
            app.quit()

        return members

def writeCoordinate(address, city, zip_code):
    pass

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