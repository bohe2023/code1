import tkinter
from tkinter import ttk
from GlobalVar import setEthernetSpecVer, setSrcMAC, setDstMAC, setSrcIP, setDstIP, setSrcPort, setDstPort, setSomeIPHead, setIgnoreSameMsgcnt, setSaveFilteredLogData
from GlobalVar import getSomeIPHead
from datetime import datetime
from TypeDef import EtherID, etherIdDic

class MessageTypeSelectBox(tkinter.Frame):
    def __init__(self, parent, choices, **kwargs):
        tkinter.Frame.__init__(self, parent, **kwargs)

        self.cbs = []
        self.vars = []
        bg = self.cget("background")
        
        frame1 = tkinter.Frame(self)
        frame1.grid()
        
        scrollbar = tkinter.Scrollbar(frame1)
        scrollbar.pack(side=tkinter.RIGHT, fill=tkinter.Y)
        
        ground = tkinter.Text(frame1, width=40, heigh=20, background=bg, highlightthickness=0, relief="flat")
        ground.pack()

        for choice in choices:
            var = tkinter.IntVar(value=choice)
            self.vars.append(var)
            cb = tkinter.Checkbutton(frame1, variable=var, text="["+format(choice, '#04X')+"] "+choices[choice]['name'],
                                onvalue=choice, offvalue=0xFFFFFFFF,
                                anchor="w", background=bg,
                                relief="flat", highlightthickness=0
            )
            
            #Default Selection status.
            if choice == EtherID.SubscribeMessage.value or choice == EtherID.AllMessageTimeLog.value or choice == EtherID.ExternalLonLatMessage.value or choice == EtherID.DebugEther.value:
                cb.deselect()
            else:
                cb.select()
            
            self.cbs.append(cb)
            ground.window_create("end", window=cb)
            ground.insert("end", "\n")

        ground.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=ground.yview)
        
        parent.protocol( 'WM_DELETE_WINDOW', command_close )
        
        # disable the widget so users can't insert text into it
        ground.configure(state="disabled")

    def getCheckedItems(self):
        values = []
        for var in self.vars:
            value = var.get()
            if value != 0xFFFFFFFF:
                values.append(value)
        return values
    
    def selectAll(self):
        for cb in self.cbs:
            cb.select()
    
    def selectNothing(self):
        for cb in self.cbs:
            cb.deselect()

def command_close(): #do nothing when close button clicked
    pass

def command() :
    global toplevel
    global checklist
    global checkedItems
    global combo1
    global srcMACselected
    global srcMAC
    global dstMACselected
    global dstMAC
    global srcIPselected
    global srcIP
    global dstIPselected
    global dstIP
    global srcPortSelected
    global srcPort
    global dstPortSelected
    global dstPort
    global someipheadSelected
    global ignoreSameMsgcnt
    global saveFilteredLogData
    
    checkedItems = checklist.getCheckedItems()
    etherSpec = combo1.current()
    etherSpecDate = [
        datetime(2030, 12, 31),
        datetime(2021, 4, 21),
        datetime(2020, 12, 25),
        datetime(2020, 9, 30),
        datetime(2020, 9, 4),
        datetime(2020, 8, 28),
        datetime(2020, 6, 16),
        datetime(2020, 4, 14),
        datetime(2020, 3, 31),
        datetime(2020, 3, 19),
        datetime(2020, 3, 18)]
        
    setEthernetSpecVer(etherSpecDate[etherSpec])
    
    setSrcMAC(srcMAC.get()) if (srcMACselected.get() == 1) else setSrcMAC("")
    setDstMAC(dstMAC.get()) if (dstMACselected.get() == 1) else setDstMAC("")
    setSrcIP(srcIP.get()) if (srcIPselected.get() == 1) else setSrcIP("")
    setDstIP(dstIP.get()) if (dstIPselected.get() == 1) else setDstIP("")
    setSrcPort(srcPort.get()) if (srcPortSelected.get() == 1) else setSrcPort("")
    setDstPort(dstPort.get()) if (dstPortSelected.get() == 1) else setDstPort("")
    
    setSomeIPHead(someipheadSelected.get())
    setIgnoreSameMsgcnt(ignoreSameMsgcnt.get())
    setSaveFilteredLogData(saveFilteredLogData.get())
    
    toplevel.quit()
    toplevel.destroy()
    
def command_selectAll() :
    global checklist
    checklist.selectAll()
    
def command_selectNothing() :
    global checklist
    checklist.selectNothing()
    
def showMessageTypeSelectBox(root):
    global toplevel
    global checklist
    global combo1
    global checkedItems
    global srcMACselected
    global srcMAC
    global dstMACselected
    global dstMAC
    global srcIPselected
    global srcIP
    global dstIPselected
    global dstIP
    global srcPortSelected
    global srcPort
    global dstPortSelected
    global dstPort
    global someipheadSelected
    global ignoreSameMsgcnt
    global saveFilteredLogData
    
    row = 1
    checkedItems = []
    toplevel = tkinter.Toplevel(root)
    toplevel.title('Select Target Message Type')

    frame1 = tkinter.Frame(toplevel)
    frame1.grid()
    
    tkinter.Label(frame1, text = "Choose Target Ethernet Spec book").grid(row=row, column=1, columnspan=3)
    row += 1
    
    combo1 = ttk.Combobox(frame1, width=40, values=[
                                        "最新台帳",
                                        "2021/04/21 北米の推奨レーンADAS2.0属性追加",
                                        "2020/12/25 VehicleParameter追加",
                                        "2020/09/30 ADPositionのオフロードフラグ追加",
                                        "2020/09/04 推奨レーンをまとめる対応",
                                        "2020/08/28 GNSS Data fixTypeAug仕様",
                                        "2020/06/16 推奨レーン経路変換状態追加",
                                        "2020/04/14 ADAS2.0属性無効フラグ追加",
                                        "2020/03/31 工事種別追加",
                                        "2020/03/19 ADAS2.0属性追加", 
                                        "2020/03/18 より以前のバージョン"])
    combo1.grid(row=row, column=1, columnspan=3)
    combo1.current(0)
    row += 1
    someipheadSelected = tkinter.IntVar(value=getSomeIPHead())
    tkinter.Checkbutton(frame1, variable=someipheadSelected, text="Include SOME/IP Head", onvalue=1, offvalue=0,
                        anchor="w", relief="flat", highlightthickness=0).grid(row=row, column=1, columnspan=3, sticky="W")
    row += 1
    ignoreSameMsgcnt = tkinter.IntVar(value=1)
    tkinter.Checkbutton(frame1, variable=ignoreSameMsgcnt, text="Ignore same msgCnt", onvalue=1, offvalue=0,
                        anchor="w", relief="flat", highlightthickness=0).grid(row=row, column=1, columnspan=3, sticky="W")
    row += 1
    saveFilteredLogData = tkinter.IntVar(value=0)
    tkinter.Checkbutton(frame1, variable=saveFilteredLogData, text="Save filtered log as pcap file", onvalue=1, offvalue=0,
                        anchor="w", relief="flat", highlightthickness=0).grid(row=row, column=1, columnspan=3, sticky="W")
    row += 1
    tkinter.Label(frame1, text = "<Filter>").grid(row=row, column=1, columnspan=3)
    row += 1
    srcMACselected = tkinter.IntVar(value=0)
    tkinter.Checkbutton(frame1, variable=srcMACselected, text="Src MAC", onvalue=1, offvalue=0,
                        anchor="w", relief="flat", highlightthickness=0).grid(row=row, column=1, sticky="W")
    srcMAC = tkinter.StringVar(value="AA:BB:CC:DD:00:06, AA:BB:CC:DD:10:06, AA:BB:CC:DD:00:0C, AA:BB:CC:DD:10:0C, AA:BB:CC:DD:00:07, AA:BB:CC:DD:00:17, AA:BB:CC:DD:00:03")
    tkinter.Entry(frame1, width=35, textvariable=srcMAC).grid(row=row, column=2, columnspan=2)
    row += 1
    dstMACselected = tkinter.IntVar(value=0)
    tkinter.Checkbutton(frame1, variable=dstMACselected, text="Dst MAC", onvalue=1, offvalue=0,
                        anchor="w", relief="flat", highlightthickness=0).grid(row=row, column=1, sticky="W")
    dstMAC = tkinter.StringVar(value="01:00:5E:32:00:01, 01:00:5E:32:17:01, 01:00:5E:32:19:01, 01:00:5E:32:2A:01, 01:00:5E:32:2B:01, 01:00:5E:32:34:01, 01:00:5E:32:36:01, 01:00:5E:32:39:01, 01:00:5E:32:45:01, 01:00:5E:32:53:01, 01:00:5E:32:62:01, 01:00:5E:32:63:01, 01:00:5E:32:64:01, 01:00:5E:32:67:01, 01:00:5E:32:68:01, AA:BB:CC:DD:00:03, AA:BB:CC:DD:00:04, AA:BB:CC:DD:00:06, AA:BB:CC:DD:00:0A, AA:BB:CC:DD:00:0B, AA:BB:CC:DD:00:0C, AA:BB:CC:DD:00:17, AA:BB:CC:DD:10:06, AA:BB:CC:DD:10:0C, AA:BB:CC:DD:00:03")
    tkinter.Entry(frame1, width=35, textvariable=dstMAC).grid(row=row, column=2, columnspan=2)
    row += 1
    srcIPselected = tkinter.IntVar(value=0)
    tkinter.Checkbutton(frame1, variable=srcIPselected, text="Src IP", onvalue=1, offvalue=0,
                        anchor="w", relief="flat", highlightthickness=0).grid(row=row, column=1, sticky="W")
    srcIP = tkinter.StringVar(value="192.168.60.6, 192.168.50.20, 192.168.11.12, 192.168.12.12, 192.168.18.12, 192.168.19.12, 192.168.50.12, 192.168.14.14, 192.168.14.3")
    tkinter.Entry(frame1, width=35, textvariable=srcIP).grid(row=row, column=2, columnspan=2)
    row += 1
    dstIPselected = tkinter.IntVar(value=0)
    tkinter.Checkbutton(frame1, variable=dstIPselected, text="Dst IP", onvalue=1, offvalue=0,
                        anchor="w", relief="flat", highlightthickness=0).grid(row=row, column=1, sticky="W")
    dstIP = tkinter.StringVar(value="192.168.50.20, 192.168.14.14, 192.168.14.3")
    tkinter.Entry(frame1, width=35, textvariable=dstIP).grid(row=row, column=2, columnspan=2)
    row += 1
    srcPortSelected = tkinter.IntVar(value=0)
    tkinter.Checkbutton(frame1, variable=srcPortSelected, text="Src PORT", onvalue=1, offvalue=0,
                        anchor="w", relief="flat", highlightthickness=0).grid(row=row, column=1, sticky="W")
    srcPort = tkinter.StringVar(value="30491, 30501")
    tkinter.Entry(frame1, width=35, textvariable=srcPort).grid(row=row, column=2, columnspan=2)
    row += 1
    dstPortSelected = tkinter.IntVar(value=0)
    tkinter.Checkbutton(frame1, variable=dstPortSelected, text="Dst PORT", onvalue=1, offvalue=0,
                        anchor="w", relief="flat", highlightthickness=0).grid(row=row, column=1, sticky="W")
    dstPort = tkinter.StringVar(value="30491, 8080")
    tkinter.Entry(frame1, width=35, textvariable=dstPort).grid(row=row, column=2, columnspan=2)
    row += 1
    
    tkinter.Label(frame1, text = "").grid(row=row, column=1, columnspan=3)
    row += 1
    tkinter.Button(frame1, text="Select All", command=command_selectAll).grid(row=row,column=1)
    tkinter.Label(frame1, width=20).grid(row=row,column=2)
    tkinter.Button(frame1, text="Unselect", command=command_selectNothing).grid(row=row,column=3)
    row += 1
    frame1.pack()
    
    checklist = MessageTypeSelectBox(toplevel, etherIdDic, background="white")
    checklist.pack()
    
    tkinter.Button(toplevel, text="Start Analysis", command=command).pack()
    
    toplevel.focus_set()
#     toplevel.overrideredirect(1)
    toplevel.resizable(0,0)
    toplevel.mainloop()
    
    return checkedItems
    
    