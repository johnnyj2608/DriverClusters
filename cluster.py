from excel import getMembersFromExcel

def cluster(filePath, date, insurance, stopFlag, callback):
    try:
        members = getMembersFromExcel(filePath, date, insurance, stopFlag)
        if not members:
            raise ValueError("Missing data")

        print(members)
        callback(error=None)

    except Exception as e:
        print("An error occurred:", str(e))
        callback(error=str(e))