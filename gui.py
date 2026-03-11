import os
import time
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

        self.root.geometry(self.centerWindow(self.root, 400, 500, self.root._get_window_scaling()))
        self.frame = ctk.CTkFrame(master=self.root)
        self.frame.pack(pady=20, padx=40, fill="both", expand=True)
        self.frame.grid_columnconfigure(0, weight=1)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self.titleLabel = ctk.CTkLabel(master=self.frame, text="Driver Clusters", font=(None, 25, "bold"))
        self.titleLabel.grid(row=0, column=0, pady=12, padx=10, sticky="ew")

        self.initBrowseFrame(row=1)
        self.initDateFrame(row=2)
        self.initInsuranceFrame(row=3)
        self.initClusterFrame(row=4)
        self.initButtonFrame(row=5)

        self.statusLabel = ctk.CTkLabel(master=self.frame, text="")
        self.statusLabel.grid(row=6, column=0, pady=0, padx=10)     # Completion %

    def initBrowseFrame(self, row):
        self.browseFrame = ctk.CTkFrame(master=self.frame, fg_color="gray17")
        self.browseFrame.grid(row=row, column=0, pady=6, padx=10)
        self.browseFrame.grid_columnconfigure(0, weight=1)

        self.folderLabel = ctk.CTkLabel(master=self.browseFrame, text="No Excel file selected")
        self.folderLabel.grid(row=0, column=0, pady=0, padx=10)

        self.browseButton = ctk.CTkButton(master=self.browseFrame, text="Select Excel file", command=self.browseFolder)
        self.browseButton.grid(row=1, column=0, pady=(0, 6), padx=10)

    def initDateFrame(self, row):
        self.dateFrame = ctk.CTkFrame(master=self.frame, fg_color="gray17")
        self.dateFrame.grid(row=row, column=0, columnspan=3, pady=6, padx=10)
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

    def initInsuranceFrame(self, row):
        self.insuranceFrame = ctk.CTkFrame(master=self.frame, fg_color="gray17")
        self.insuranceFrame.grid(row=row, column=0, pady=6, padx=10)
        self.insuranceFrame.grid_columnconfigure(0, weight=1)
        
        self.insuranceLabel = ctk.CTkLabel(master=self.insuranceFrame, text="Insurance")
        self.insuranceLabel.grid(row=0, column=0, pady=0, padx=10, sticky="ew")

        self.insuranceCombo = ctk.CTkComboBox(master=self.insuranceFrame, values=list([]), width=150, state="disabled")
        self.insuranceCombo.grid(row=1, column=0, pady=0, padx=10, sticky="ew")

    def initClusterFrame(self, row):
        self.clusterFrame = ctk.CTkFrame(master=self.frame, fg_color="gray17")
        self.clusterFrame.grid(row=row, column=0, pady=6, padx=10)
        self.clusterFrame.grid_columnconfigure(1, weight=1)

        self.clusterLabel = ctk.CTkLabel(master=self.clusterFrame, text="Grouping")
        self.clusterLabel.grid(row=0, column=0, columnspan=3, pady=0, padx=10, sticky="ew")

        self.clusterVar = ctk.StringVar(value="Size")

        self.clusterEntry = ctk.CTkEntry(master=self.clusterFrame, width=50)
        self.clusterEntry.grid(row=1, column=1, columnspan=1, pady=0, padx=1)
        self.clusterEntry.configure(validate="key", validatecommand=(self.frame.register(self.validateYear), "%P"), state="disabled")

        self.sizeRadio = ctk.CTkRadioButton(
            master=self.clusterFrame, 
            text="Size", 
            variable=self.clusterVar, 
            value="Size",
            radiobutton_height=20,
            radiobutton_width=20,
            state="disabled",
        )
        self.sizeRadio.grid(row=1, column=0, columnspan=1,  pady=0, padx=5, sticky="e")

        self.driverRadio = ctk.CTkRadioButton(
            master=self.clusterFrame, 
            text="Drivers", 
            variable=self.clusterVar, 
            value="Drivers",
            radiobutton_height=20,
            radiobutton_width=20,
            state="disabled",
        )
        self.driverRadio.grid(row=1, column=2, columnspan=1, pady=0, padx=5, sticky="w")

    def initButtonFrame(self, row):
        self.buttonFrame = ctk.CTkFrame(master=self.frame, fg_color="gray17")
        self.buttonFrame.grid(row=row, column=0, pady=6, padx=10)
        self.buttonFrame.grid_columnconfigure(0, weight=1)

        self.calculateButton = ctk.CTkButton(master=self.buttonFrame, text="Calculate", command=self.calculate, state="disabled")
        self.calculateButton.grid(row=0, column=0, pady=(6, 6), padx=10)

        # Second button: Click to download cluster map / excel of pickup times and group

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

            self.insuranceCombo.configure(values=insurances)
            self.insuranceCombo.set(insurances[0])

            self.clusterEntry.delete(0, "end")
            self.clusterEntry.insert(0, "7")
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
        return val == "" or (val.isdigit() and len(val) <= 2)

    def validateDay(self, val):
        return val == "" or (val.isdigit() and len(val) <= 2)

    def validateYear(self, val):
        return val == "" or (val.isdigit() and len(val) <= 4)

    def disableUserActions(self):
        self.browseButton.configure(state="disabled")

        self.monthEntry.configure(state="disabled")
        self.dayEntry.configure(state="disabled")
        self.yearEntry.configure(state="disabled")
        self.datePickerButton.configure(state="disabled")

        self.insuranceCombo.configure(state="disabled")
        self.clusterEntry.configure(state="disabled")
        self.sizeRadio.configure(state="disabled")
        self.driverRadio.configure(state="disabled")
        self.calculateButton.configure(state="disabled")

    def enableUserActions(self):
        self.browseButton.configure(state="normal")

        self.monthEntry.configure(state="normal")
        self.dayEntry.configure(state="normal")
        self.yearEntry.configure(state="normal")
        self.datePickerButton.configure(state="normal")

        self.insuranceCombo.configure(state="normal")
        self.clusterEntry.configure(state="normal")
        self.sizeRadio.configure(state="normal")
        self.driverRadio.configure(state="normal")
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

        month = self.monthEntry.get()
        day = self.dayEntry.get()
        year = self.yearEntry.get()

        thread = Thread(target = cluster, args=(
            self.folderLabel.cget("text"),
            datetime(int(year), int(month), int(day)),
            self.insuranceCombo.get(),
            self.statusLabel,
            self.stopFlag,
            self.clusterComplete))
        
        thread.start()

    def clusterComplete(self):
        self.runningFlag = False
        self.stopFlag.value = False
        self.enableUserActions()
        self.calculateButton.configure(text="Automate", fg_color='#1f538d', hover_color='#14375e')

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

    def centerWindow(self, Screen: ctk, width: int, height: int, scale_factor: float = 1.0):
        screen_width = Screen.winfo_screenwidth()
        screen_height = Screen.winfo_screenheight()
        x = int(((screen_width/2) - (width/2)) * scale_factor)
        y = int(((screen_height/2) - (height/1.5)) * scale_factor)
        return f"{width}x{height}+{x}+{y}"

    def run(self):
        self.root.mainloop()