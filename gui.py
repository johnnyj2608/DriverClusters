import os
import time
import webbrowser
import tempfile
from datetime import datetime, timedelta
from threading import Thread

import customtkinter as ctk
from customtkinter import filedialog , CTkToplevel
from tkcalendar import Calendar
from PIL import Image

from excel import validateExcelFile, ifExcelFileOpen
from cluster import cluster

class ProcessStop:
    def __init__(self):
        self.value = False

class ClusterGUI:
    def __init__(self, datePickerIcon):
        self.datePickerIcon = datePickerIcon
        self.root = ctk.CTk()
        self.root.title("Driver Clusters")
        self.stopFlag = ProcessStop()
        self.runningFlag = False
        self.members = []
        self.map = None
        self.excel = None

        self.root.geometry(self.centerWindow(self.root, 400, 525, self.root._get_window_scaling()))
        self.frame = ctk.CTkFrame(master=self.root)
        self.frame.pack(pady=20, padx=40, fill="both", expand=True)
        self.frame.grid_columnconfigure(0, weight=1)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.titleLabel = ctk.CTkLabel(master=self.frame, text="Driver Clusters", font=(None, 25, "bold"))
        self.titleLabel.grid(row=0, column=0, pady=12, padx=10, sticky="ew")

        self.initBrowseFrame(row=1)
        self.initDateFrame(row=2)
        self.initTimeFrame(row=3)
        self.initInsuranceFrame(row=4)
        self.initButtonFrame(row=5)

        self.statusLabel = ctk.CTkLabel(master=self.frame, text="")
        self.statusLabel.grid(row=6, column=0, pady=0, padx=10)     # Completion %

    def initBrowseFrame(self, row):
        self.browseFrame = ctk.CTkFrame(master=self.frame, fg_color="gray17")
        self.browseFrame.grid(row=row, column=0, pady=4, padx=10)
        self.browseFrame.grid_columnconfigure(0, weight=1)

        self.folderLabel = ctk.CTkLabel(master=self.browseFrame, text="No Excel file selected")
        self.folderLabel.grid(row=0, column=0, pady=0, padx=10)

        self.browseButton = ctk.CTkButton(master=self.browseFrame, text="Select Excel file", command=self.browseFolder)
        self.browseButton.grid(row=1, column=0, pady=0, padx=10)

    def initDateFrame(self, row):
        self.dateFrame = ctk.CTkFrame(master=self.frame, fg_color="gray17")
        self.dateFrame.grid(row=row, column=0, columnspan=3, pady=4, padx=10)
        self.dateFrame.grid_columnconfigure((0, 4), weight=1)

        self.dateLabel = ctk.CTkLabel(master=self.dateFrame, text="Date")
        self.dateLabel.grid(row=0, column=0, columnspan=5, pady=0, padx=10, sticky="ew")

        self.monthEntry = ctk.CTkEntry(master=self.dateFrame, width=30)
        self.monthEntry.grid(row=1, column=0, pady=0, padx=1, sticky="e")
        self.monthEntry.configure(validate="key", validatecommand=(self.frame.register(self.validateMonth), "%P"), state="disabled")

        self.dayEntry = ctk.CTkEntry(master=self.dateFrame, width=30)
        self.dayEntry.grid(row=1, column=1, pady=0, padx=1, sticky="e")
        self.dayEntry.configure(validate="key", validatecommand=(self.frame.register(self.validateDay), "%P"), state="disabled")

        self.yearEntry = ctk.CTkEntry(master=self.dateFrame, width=45)
        self.yearEntry.grid(row=1, column=2, pady=0, padx=1, sticky="e")
        self.yearEntry.configure(validate="key", validatecommand=(self.frame.register(self.validateYear), "%P"), state="disabled")

        img = ctk.CTkImage(dark_image=Image.open(self.datePickerIcon))
        self.datePickerButton = ctk.CTkButton(
            master=self.dateFrame, 
            image=img, 
            text="", 
            command=lambda: self.toggleCalendar(),
            width=32, 
            height=32, 
            state="disabled"
        )
        self.datePickerButton.grid(row=1, column=4, pady=0, padx=(5, 10), sticky="w")

    def initTimeFrame(self, row):
        self.timeFrame = ctk.CTkFrame(master=self.frame, fg_color="gray17")
        self.timeFrame.grid(row=row, column=0, pady=4, padx=10)
        self.timeFrame.grid_columnconfigure((0, 2), weight=1)

        self.timeLabel = ctk.CTkLabel(master=self.timeFrame, text="Start Time")
        self.timeLabel.grid(row=0, column=0, columnspan=3, pady=0, padx=10, sticky="ew")

        self.hourEntry = ctk.CTkEntry(master=self.timeFrame, width=40)
        self.hourEntry.grid(row=1, column=0, pady=0, padx=1, sticky="e")
        self.hourEntry.configure(validate="key", validatecommand=(self.frame.register(self.validateHour), "%P"), state="disabled")

        self.minuteEntry = ctk.CTkEntry(master=self.timeFrame, width=40)
        self.minuteEntry.grid(row=1, column=1, pady=0, padx=1, sticky="w")
        self.minuteEntry.configure(validate="key", validatecommand=(self.frame.register(self.validateMinute), "%P"), state="disabled")

        self.ampmSwitch = ctk.CTkSegmentedButton(
            master=self.timeFrame,
            values=["AM", "PM"],
            state="disabled"
        )
        self.ampmSwitch.grid(row=1, column=2, pady=0, padx=1)

    def initInsuranceFrame(self, row):
        self.insuranceFrame = ctk.CTkFrame(master=self.frame, fg_color="gray17")
        self.insuranceFrame.grid(row=row, column=0, pady=4, padx=10)
        self.insuranceFrame.grid_columnconfigure(0, weight=1)
        
        self.insuranceLabel = ctk.CTkLabel(master=self.insuranceFrame, text="Insurance")
        self.insuranceLabel.grid(row=0, column=0, pady=0, padx=10, sticky="ew")

        self.insuranceCombo = ctk.CTkComboBox(master=self.insuranceFrame, values=list([]), width=150, state="disabled")
        self.insuranceCombo.grid(row=1, column=0, pady=0, padx=10, sticky="ew")

    def initButtonFrame(self, row):
        self.buttonFrame = ctk.CTkFrame(master=self.frame, fg_color="gray17")
        self.buttonFrame.grid(row=row, column=0, pady=4, padx=10)
        self.buttonFrame.grid_columnconfigure(0, weight=1)

        self.calculateButton = ctk.CTkButton(master=self.buttonFrame, text="Calculate", command=self.calculate, state="disabled")
        self.calculateButton.grid(row=0, column=0, pady=4, padx=10)

        self.mapButton = ctk.CTkButton(master=self.buttonFrame, text="Open Map", command=self.openMap, state="disabled")
        self.mapButton.grid(row=1, column=0, pady=4, padx=10)

        self.excelButton = ctk.CTkButton(master=self.buttonFrame, text="Download Excel", command=self.downloadExcel, state="disabled")
        self.excelButton.grid(row=2, column=0, pady=4, padx=10)

    def browseFolder(self):
        self.filePath = filedialog.askopenfilename(title="Select a File", filetypes=[("Excel files", "*.xlsx")])
        insurances = validateExcelFile(self.filePath)
        if self.filePath and insurances:
            self.enableUserActions()
            fileName = os.path.basename(self.filePath)
            self.folderLabel.configure(text=fileName, text_color="gray84")

            today = datetime.now()
            
            self.monthEntry.delete(0, "end")
            self.monthEntry.insert(0, today.month)

            self.dayEntry.delete(0, "end")
            self.dayEntry.insert(0, today.day)

            self.yearEntry.delete(0, "end")
            self.yearEntry.insert(0, today.year)

            self.hourEntry.delete(0, "end")
            self.hourEntry.insert(0, "7")

            self.minuteEntry.delete(0, "end")
            self.minuteEntry.insert(0, "00")
            self.ampmSwitch.set("AM")

            self.insuranceCombo.configure(values=insurances)
            self.insuranceCombo.set(insurances[0])
        else:
            self.folderLabel.configure(text="No members in template", text_color="red")
            self.disableUserActions()
            self.browseButton.configure(state="normal")

    def toggleCalendar(self):
        calendarWindow = CTkToplevel()
        calendarWindow.title('Choose date')
        calendarWindow.geometry('300x200')
        calendarWindow.grab_set()
        calendarWindow.attributes("-topmost", True)

        x = self.root.winfo_rootx()
        buttonWidget = self.datePickerButton
        y = buttonWidget.winfo_rooty() + buttonWidget.winfo_height()

        calendarWindow.geometry(f'+{x}+{y}')
        
        self.cal = Calendar(calendarWindow, 
                       selectmode="day", 
                       date_pattern="m/d/y", 
                       firstweekday="sunday",
                       font=("Arial", 14),
                       showweeknumbers=False)
        self.cal.grid(row=0, column=0, sticky="nswe")

        calendarWindow.grid_columnconfigure(0, weight=1)
        calendarWindow.grid_rowconfigure(0, weight=1)

        self.cal.bind("<<CalendarSelected>>", self.dateSelected)
        try:
            month = int(self.monthEntry.get())
            day = int(self.dayEntry.get())
            year = int(self.yearEntry.get())
            date = datetime(year, month, day)
        except ValueError:
            return False, "Date does not exist"
        self.cal.selection_set(date.date())
        return

    def dateSelected(self, event=None):
        selectedDate = self.cal.get_date()
        month, day, year = selectedDate.split('/')

        self.monthEntry.delete(0, "end")
        self.monthEntry.insert(0, month)

        self.dayEntry.delete(0, "end")
        self.dayEntry.insert(0, day)

        self.yearEntry.delete(0, "end")
        self.yearEntry.insert(0, year)

        self.cal.grid_remove()
        self.cal.master.destroy()

    def validateMonth(self, val):
        if val == "":
            return True
        if val.isdigit() and 1 <= int(val) <= 12:
            return True
        return False

    def validateDay(self, val):
        if val == "":
            return True
        if val.isdigit() and 1 <= int(val) <= 31:
            return True
        return False

    def validateYear(self, val):
        if val == "":
            return True
        if val.isdigit() and 1900 <= int(val) <= 9999:
            return True
        return False
    
    def validateHour(self, val):
        if val == "":
            return True
        if val.isdigit() and 1 <= int(val) <= 12:
            return True
        return False
    
    def validateMinute(self, val):
        if val == "":
            return True
        if val.isdigit() and 0 <= int(val) <= 59:
            return True
        return False

    def disableUserActions(self):
        self.browseButton.configure(state="disabled")

        self.monthEntry.configure(state="disabled")
        self.dayEntry.configure(state="disabled")
        self.yearEntry.configure(state="disabled")
        self.datePickerButton.configure(state="disabled")

        self.hourEntry.configure(state="disabled")
        self.minuteEntry.configure(state="disabled")
        self.ampmSwitch.configure(state="disabled")

        self.insuranceCombo.configure(state="disabled")
        self.calculateButton.configure(state="disabled")

    def enableUserActions(self):
        self.browseButton.configure(state="normal")

        self.monthEntry.configure(state="normal")
        self.dayEntry.configure(state="normal")
        self.yearEntry.configure(state="normal")
        self.datePickerButton.configure(state="normal")

        self.hourEntry.configure(state="normal")
        self.minuteEntry.configure(state="normal")
        self.ampmSwitch.configure(state="normal")

        self.insuranceCombo.configure(state="normal")
        self.calculateButton.configure(state="normal")

    def calculate(self):
        if self.runningFlag:
            self.stopFlag.value = True
            self.calculateButton.configure(text="Stopping...")
            return
        
        if ifExcelFileOpen(self.folderLabel.cget("text")):
            self.statusLabel.configure(text="Must close selected Excel file", text_color="red")
            return

        self.runningFlag = True
        self.calculateButton.configure(text="Stop", fg_color='#800000', hover_color='#98423d')
        self.statusLabel.configure(text="", text_color="gray84")
        self.disableUserActions()
        self.calculateButton.configure(state="normal")  

        self.startTime = time.time()

        month = int(self.monthEntry.get())
        day = int(self.dayEntry.get())
        year = int(self.yearEntry.get())
        
        hour = int(self.hourEntry.get())
        minute = int(self.minuteEntry.get())
        ampm = self.ampmSwitch.get()

        if ampm == "PM" and hour != 12:
            hour += 12
        elif ampm == "AM" and hour == 12:
            hour = 0

        thread = Thread(target = cluster, args=(
            self.folderLabel.cget("text"),
            datetime(year, month, day, hour, minute),
            self.insuranceCombo.get(),
            self.statusLabel,
            self.stopFlag,
            self.clusterComplete))
        
        thread.start()

    def clusterComplete(self, mapHtml, excelBytes, error=None):
        self.runningFlag = False
        self.stopFlag.value = False
        self.enableUserActions()
        self.calculateButton.configure(text="Calculate", fg_color='#1f538d', hover_color='#14375e')

        if error:
            self.statusLabel.configure(text=f"Error: {error}", text_color="red")
            self.statusLabel.update()
            return
        
        if mapHtml:
            self.map = mapHtml
            self.mapButton.configure(state="normal")

        if excelBytes:
            self.excel = excelBytes
            self.excelButton.configure(state="normal")

        elapsedTime = time.time() - self.startTime
        elapsedTime = timedelta(seconds=int(elapsedTime))
        parts = []
         
        if elapsedTime.seconds >= 3600:
            hours = elapsedTime.seconds // 3600
            parts.append(f"{hours}h")

        if elapsedTime.seconds >= 60:
            minutes = (elapsedTime.seconds // 60) % 60
            parts.append(f"{minutes}m")

        seconds = elapsedTime.seconds % 60
        parts.append(f"{seconds}s")

        formattedTime = " ".join(parts)

        self.statusLabel.configure(text="Completed in "+formattedTime)
        self.statusLabel.update()

    def openMap(self):
        if self.map:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".html") as temp_file:
                temp_file.write(self.map.encode('utf-8'))
                temp_file.close() 
                webbrowser.open(f"file://{temp_file.name}")

    def downloadExcel(self):
        if self.excel:

            insurance = self.insuranceCombo.get()
            month = self.monthEntry.get()
            day = self.dayEntry.get()
            year = self.yearEntry.get()
            filename = f"{insurance}_{month}-{day}-{year}.xlsx"
            
            file_path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel files", "*.xlsx")],
                initialfile=filename,
                title="Save Excel File"
            )
            if file_path:
                self.excel.seek(0)
                with open(file_path, "wb") as f:
                    f.write(self.excel.read())

    def centerWindow(self, Screen: ctk, width: int, height: int, scale_factor: float = 1.0):
        screen_width = Screen.winfo_screenwidth()
        screen_height = Screen.winfo_screenheight()
        x = int(((screen_width/2) - (width/2)) * scale_factor)
        y = int(((screen_height/2) - (height/1.5)) * scale_factor)
        return f"{width}x{height}+{x}+{y}"

    def run(self):
        self.root.mainloop()