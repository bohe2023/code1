'''
Created on 2024/04/18

@author: AD2Gen2-19
'''
import tkinter
from tkinter import ttk, messagebox, filedialog
import psutil

def select():
    global root
    global combo1var
    global interfaceList
    global selectedDevice
    
    selectedDevice = combo1var.get()
    
    if not selectedDevice in interfaceList:
        messagebox.showwarning(title='wrong interface name', message='Not exist interface name')
        return
    
    root.quit()
    root.destroy()
    
def cancel():
    global root   
    root.quit()
    root.destroy()
    
def logFileSelect():
    global root
    global selectedLogfile
    
    typ = [('Select Log Files','*.pcapng;*.pcap;*.blf;*.asc')]
    fileList = list(filedialog.askopenfilenames(parent=root,title='Choose log files',filetypes = typ))
    if len(fileList) > 0:
        selectedLogfile = fileList
        root.quit()
        root.destroy()
        
def showEthernetDeviceSelectBox(defaultSelectedDevice = '', defaultSavePCAPlog = False):
    global root
    global combo1var
    global interfaceList
    global selectedDevice
    global selectedLogfile
    selectedDevice = ''
    selectedLogfile = None
    
    root = tkinter.Tk()    
    row = 1
    root.title('Select Mirroring Ethernet Interface')

    frame1 = tkinter.Frame(root)
    frame1.grid()
    
    tkinter.Button(frame1, width=20, text="[ Replay with log file ]", command=logFileSelect).grid(row=row, column=2, columnspan=1, padx=5, pady=5)
    row += 1
    
    tkinter.Label(frame1, width=60, text = "Choose Interface").grid(row=row, column=1, columnspan=2)
    row += 1
    
    addrs = psutil.net_if_addrs()
    interfaceList = list(addrs.keys())
    
    if len(interfaceList) > 0 and defaultSelectedDevice == '':
        defaultSelectedDevice = interfaceList[0]

    combo1var = tkinter.StringVar(value=defaultSelectedDevice)
    ttk.Combobox(frame1, width=30, font=('Verdana', 12, 'bold'), values=interfaceList, textvariable=combo1var).grid(row=row, column=1, columnspan=2)
    row += 1
    
    savePCAPlog = tkinter.IntVar(value=defaultSavePCAPlog)
    tkinter.Checkbutton(frame1, variable=savePCAPlog, text="Save capture packets as pcap", onvalue=1, offvalue=0,
                        anchor="w", relief="flat", highlightthickness=0).grid(sticky="W", row=row, column=1, columnspan=2, padx=35, pady=5)
    row += 1
    
    tkinter.Button(frame1, width=20, height=2, text="[ Select ]", command=select).grid(row=row, column=1, columnspan=1, padx=5, pady=5)
    tkinter.Button(frame1, width=20, height=2, text="[ Cancel ]", command=cancel).grid(row=row, column=2, columnspan=1, padx=5, pady=5)
    
    frame1.pack()
    
    root.focus_set()
    root.resizable(0,0)
    root.mainloop()
    
    return (selectedDevice, selectedLogfile, savePCAPlog.get())