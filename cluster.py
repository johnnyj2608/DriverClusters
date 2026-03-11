from excel import getMembersFromExcel

def cluster(filePath, date, insurance, statusLabel, stopFlag, callback):
    try:
        members = getMembersFromExcel(filePath, date, insurance, stopFlag)
    except Exception as e:
        print("An error occurred:", str(e))
        statusLabel.configure(text=f"Error has occurred", text_color="red")
        statusLabel.update()
    finally:
        callback()