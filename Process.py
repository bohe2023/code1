import os
import shutil
import traceback
import tkinter
import json
from tkinter import filedialog, messagebox
import dpkt,socket
import subprocess
from Logger import loadLogger, initLogger
from datetime import datetime
from multiprocessing import Process, cpu_count, Manager, Queue
from MessageTypeSelectBox import showMessageTypeSelectBox
from ExcelFileCtrl import openExcelFile, MyWorkSheet
from MessageType import initMessage, analyzeMessage, ProfileMessage
from TypeDef import CommonHeader, EtherID, getEtherIdDic, etherIdDic, isEthMessageIncluded, isCANmessageIncluded, getGrouppingMessage, isGrouppingMessage
from GlobalVar import getResource, setResource, getSrcMAC, getDstMAC, getSrcIP, getDstIP, getSrcPort, getDstPort, getSomeIPHead, getSaveFilteredLogData
from PCAPLoader import TCPStream, getTcpPackets, getUdpPackets, getCANFramePacket, IPdic, getSomeipListup, initPCAPLoader
from time import sleep
from dpkt.compat import compat_ord
from BLF_Eethernet import BLFEtherReader
from ACSCanReader import ACSCanReader
import itertools

# import tracemalloc
# import linecache
# 
# def displayMemory(snapshot, key_type='lineno', limit=10):
#     snapshot = snapshot.filter_traces((
#         tracemalloc.Filter(False, "<frozen importlib._bootstrap>"),
#         tracemalloc.Filter(False, "<unknown>"),
#     ))
#     top_stats = snapshot.statistics(key_type)
# 
#     print("Top %s lines" % limit)
#     for index, stat in enumerate(top_stats[:limit], 1):
#         frame = stat.traceback[0]
#         # replace "/path/to/module/file.py" with "module/file.py"
#         filename = os.sep.join(frame.filename.split(os.sep)[-2:])
#         print("#%s: %s:%s: %.1f KiB"
#               % (index, filename, frame.lineno, stat.size / 1024))
#         line = linecache.getline(frame.filename, frame.lineno).strip()
#         if line:
#             print('    %s' % line)
# 
#     other = top_stats[limit:]
#     if other:
#         size = sum(stat.size for stat in other)
#         print("%s other: %.1f KiB" % (len(other), size / 1024))
#     total = sum(stat.size for stat in top_stats)
#     print("Total allocated size: %.1f KiB" % (total / 1024))

class Structure:
    pass

def showGUI(title):
    global root
    global label2
    global coreLabel
    
    root = tkinter.Tk()
    root.title('ADASIS PCAP Analyzer')
    # root.geometry('200x20')
    frame1 = tkinter.Frame(root)
    frame1.grid()
    
    label1 = tkinter.Label(
        frame1,
        text=title,
        background='#0000aa',
        foreground='#ffffff',
        width=10)
    label1.grid(row=1,column=1)
    
    label2 = tkinter.Label(
        frame1,
        text='Log file select',
        background='#ffffff',
        width=40)
    label2.grid(row=1,column=2)
    
    coreLabel = []
    for i in range(cpu_count()):
        label = tkinter.Label(
            frame1,
            text='Core ' + str(i),
            background='#bbbbff',
            width=10)
        label.grid(row=i+2,column=1)
                
        label = tkinter.Label(
            frame1,
            text='wait...',
            background='#ffffff',
            anchor="w", 
            width=40)
        coreLabel.append(label)
        label.grid(row=i+2,column=2)
    
def makeWorkSheet(messageID, name):
    etherIDinfo = getEtherIdDic(messageID)
    if etherIDinfo == None:
        return None
    
    if 'useMultiLine' in etherIDinfo:
        useMultiLine = etherIDinfo['useMultiLine']
    else:
        useMultiLine = False
    if 'useMacro' in etherIDinfo:
        useMacro = etherIDinfo['useMacro']
    else:
        useMacro = False
    if 'outputCSV' in etherIDinfo:
        outputCSV = etherIDinfo['outputCSV']
    else:
        outputCSV = False

    # csvのみ出力し、エクセルファイル(.xlsm or .xlsx)を出力させないための設定。すべてのメッセージに対して適用。
    outputCSV = True
    useMacro = False
    outputOnlyCSV = True

    worksheetInfo = Structure()
    worksheetInfo.workbook = openExcelFile(name, useMultiLine, useMacro, outputOnlyCSV)
    worksheetInfo.worksheet = worksheetInfo.workbook.add_worksheet('Sheet1', MyWorkSheet)
    worksheetInfo.worksheet.init(name, worksheetInfo.workbook, useMultiLine, useMacro, outputCSV)
    worksheetInfo.currentRow = 0
    worksheetInfo.currentCol = 0
    return worksheetInfo

def logFileAnalyze(fileList = None, targetMessageID = None, outputFolder = None):
    mergeFile = False
    if fileList == None:
        typ = [('Select Log Files','*.pcapng;*.pcap;*.blf;*.asc')] 
        fileList = list(filedialog.askopenfilenames(parent=root,title='Choose log files',filetypes = typ))

        if len(fileList) == 0:
            return
        elif len(fileList) > 1:
            MsgBox = messagebox.askquestion ('Multiple Files','Is this continous log files ?',icon = 'question')
            if MsgBox == 'yes':
                mergeFile = True
                
    elif type(fileList) == type([]):
        mergeFile = True
        if len(fileList) == 0:
            return
    
    else:
        print('Invalid log file list')
        return
    
    fileList.sort()
    
    if targetMessageID == None:
        targetMessageID = showMessageTypeSelectBox(root)
    elif type(targetMessageID) != type([]):
        print('Invalid targetMessageID list')
        return
    
    if outputFolder == None:
        try:
            os.mkdir("result")
        except FileExistsError:
            pass
        except Exception as e:
            messagebox.showerror(title="Error", message="<Cannot create result folder> : \n{}".format(e))
            return
        os.chdir("result/")
    else:
        try:
            os.mkdir(outputFolder)
        except FileExistsError:
            pass
        os.chdir(outputFolder)

    #個々の入力ファイルに対応する個々の出力ファイルを作成する。元の仕様では、コマンドラインで複数のファイル(ファイルリスト)を入力すると、出力ファイルは1つにまとめられるが、そうしないようにする
    mergeFile = False 
    logFileAnalyze_(fileList, targetMessageID, outputFolder, mergeFile, isEthMessageIncluded(targetMessageID), isCANmessageIncluded(targetMessageID))
#     if isEthMessageIncluded(targetMessageID):
#         print('<Ether Message Analyze Step>')
#         logFileAnalyze_(fileList, targetMessageID, outputFolder, mergeFile, True, False)
#     if isCANmessageIncluded(targetMessageID):
#         print('<CAN Message Analyze Step>')
#         logFileAnalyze_(fileList, targetMessageID, outputFolder, mergeFile, False, True)

def logFileAnalyze_(fileList = None, targetMessageID = None, outputFolder = None, mergeFile = False, etherAnalyze = True, canAnalyze = True):
    # for GUI
    global root
    global label2
    global coreLabel
        
    # for MultiProcess Resource
    params = {}
    params['filter_srcMAC'] = getSrcMAC()
    params['filter_dstMAC'] = getDstMAC()
    params['filter_srcIP'] = getSrcIP()
    params['filter_dstIP'] = getDstIP()
    params['filter_srcPort'] = getSrcPort()
    params['filter_dstPort'] = getDstPort()
    params['someipmode'] = getSomeIPHead()
    saveFilteredLogData = getSaveFilteredLogData()
    params['saveFilteredLogData'] = saveFilteredLogData
    
    params['fileList'] = fileList
    params['targetMessageID'] = targetMessageID
    params['etherAnalyze'] = etherAnalyze
    params['canAnalyze'] = canAnalyze
    params['timeStamp'] = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')
    
    # for shared data (low speed. so, just only use sharing data between multiProcess)
    manager = Manager()
    params['completeFlag'] = manager.dict()
    params['messageNowOnProc'] = manager.dict()
    params['processMessage'] = manager.dict()
    params['messageSheetList'] = manager.dict()
    params['totalReadFrames'] = manager.dict()
    for file in fileList:
        params['messageNowOnProc'][file] = False
    
    # GUI が初期化されていない状態（コマンドライン実行など）の場合に備えて、
    # GUI ウィジェットを参照する処理を安全に行えるようにしておく。
    # coreLabel/label2/root が未定義の場合は None をセットし、
    # 後続の処理では存在チェックを行った上で GUI 更新を行う。
    if 'coreLabel' not in globals() or coreLabel is None:
        coreLabel = []
    if 'label2' not in globals():
        label2 = None
    if 'root' not in globals():
        root = None

    # FileRead MultiProc start
    procList = []
    for i in range(cpu_count()):
        params['completeFlag'][i] = False
        params['processMessage'][i] = 'wait...'
        params['totalReadFrames'][i] = 0
        try:
            procQueue = Queue()
            p = Process(target=multiProcessReadFile, name='fileReader', args=[i, getResource(), params, procQueue])
            p.start()
        except Exception as e:
            params['processMessage'][i] = 'error'
            p = None
            procQueue = None
        procList.append([p, procQueue])
    
    while True:
        stillAlive = False
        sumReadFramesCnt = 0
        for i in range(cpu_count()):
            if i >= len(coreLabel):
                # GUI が存在しない（またはコア数分のラベルが無い）場合でも
                # 例外なく処理を続行できるようにする。
                pass
            else:
                coreLabel[i].configure(text=params['processMessage'][i])
            sumReadFramesCnt += params['totalReadFrames'][i]
            #if procList[i][0] != None and procList[i][0].is_alive():
            if procList[i][0] != None and params['completeFlag'][i] == False:
                stillAlive = True
        if label2 is not None:
            label2.configure(text=str(sumReadFramesCnt) + " frames...")
        if stillAlive == False:
            break
        if root is not None:
            root.update()
        sleep(0.1)
        
    logFileTimeDiff_ts_groupByFile = {}
    totalFrameCount_groupByFile = {}
    messageDataList_groupByFile = {}
    messageLogTimeList_groupByFile = {}
    messageLogIndexList_groupByFile = {}
    messageLogIDList_groupByFile = {}
    messageFromList_groupByFile = {}
    messageToList_groupByFile = {}
    SomeipListup_groupByFile = {}
    for p, procQueue in procList:
        logFileTimeDiff_ts_groupByFile.update(procQueue.get())
        totalFrameCount_groupByFile.update(procQueue.get())
        messageDataList_groupByFile.update(procQueue.get())
        messageLogTimeList_groupByFile.update(procQueue.get())
        messageLogIndexList_groupByFile.update(procQueue.get())
        messageLogIDList_groupByFile.update(procQueue.get())
        messageFromList_groupByFile.update(procQueue.get())
        messageToList_groupByFile.update(procQueue.get())
        SomeipListup_groupByFile.update(procQueue.get())
        p.join()
    
    logger = None           
    #continouslogfiles=False:個々の入力ファイルに対応する個々の出力ファイルを作成する。元の仕様では、コマンドラインで複数のファイル(ファイルリスト)を入力すると、出力ファイルは1つにまとめられるが、そうしないようにする
    continouslogfiles = False        
    try:    
        for fileIndex, file in enumerate(fileList):
            fileName = os.path.basename(file)
            fileName = fileName[:fileName.rfind('.')]
            if fileIndex == 0 or mergeFile == False:
                # if outputFolder == None:
                if not continouslogfiles:
                    try:
                        os.mkdir(fileName)
                    except FileExistsError:
                        pass
                    os.chdir(fileName + "/")
                    
                logger = initLogger('log.txt', forMultiProcess = True)
                readIndex = 0
                messageDataList = {}
                messageLogTimeList = {}
                messageLogIndexList = {}
                messageLogIDList = {}
                messageFromList = {}
                messageToList = {}
                logFileTimeDiff_ts = []
                for etherId in etherIdDic:
                    messageDataList[etherId] = []
                    messageLogTimeList[etherId] = []
                    messageLogIndexList[etherId] = []
                    messageLogIDList[etherId] = []
                    messageFromList[etherId] = []
                    messageToList[etherId] = []

            if os.path.isfile('../log_read(' + fileName + ').txt'):
                logger.logPrint('(read) ' + fileName)
                with open('../log_read(' + fileName + ').txt', "r") as infile:
                    readLog = infile.read().split(',')[3:]
                    if len(readLog) > 0:
                        logger.logPrint(readLog)   
                os.remove('../log_read(' + fileName + ').txt')
            logger.logPrintWithConsol('Analyzed {} frames in "{}"'.format(totalFrameCount_groupByFile[file], fileName))
            logger.flush()
            
            if saveFilteredLogData == True:
                if os.path.isfile('../' + params['timeStamp'] + '-' + fileName + '.pcap'):
                    shutil.move('../' + params['timeStamp'] + '-' + fileName + '.pcap', fileName + '.pcap')
                if (fileIndex == len(fileList)-1) and mergeFile == True:
                    try:
                        try:
                            subprocess.run('"C:/Program Files/Wireshark/mergecap" -w EtherLog-merge.pcapng ' + '*.pcap')
                        except:
                            subprocess.run('mergecap -w EtherLog-merge.pcapng ' + '*.pcap')
                    except Exception as e:
                        logger.errLog("cannot run mergecap. please confirm path. (Error:{})".format(e))
                  
            for etherId in etherIdDic:
                if etherId == EtherID.ServiceID.value:
                    messageDataList[etherId] += SomeipListup_groupByFile[file].values()
                else:
                    messageDataList[etherId] += messageDataList_groupByFile[file][etherId]
                    messageLogTimeList[etherId] += messageLogTimeList_groupByFile[file][etherId]
                    modifyMessageLogIndexList = messageLogIndexList_groupByFile[file][etherId]
                    for i in range(len(modifyMessageLogIndexList)):
                        modifyMessageLogIndexList[i] += readIndex
                    messageLogIndexList[etherId] += modifyMessageLogIndexList
                    messageLogIDList[etherId] += messageLogIDList_groupByFile[file][etherId]
                    messageFromList[etherId] += messageFromList_groupByFile[file][etherId]
                    messageToList[etherId] += messageToList_groupByFile[file][etherId]
            for i in range(len(logFileTimeDiff_ts_groupByFile[file])):
                logFileTimeDiff_ts_groupByFile[file][i][0] += readIndex
            logFileTimeDiff_ts += logFileTimeDiff_ts_groupByFile[file]            
            
            del messageDataList_groupByFile[file]
            del messageLogTimeList_groupByFile[file]
            del messageLogIndexList_groupByFile[file]
            del messageLogIDList_groupByFile[file]
            del messageFromList_groupByFile[file]
            del messageToList_groupByFile[file]
            del SomeipListup_groupByFile[file]
            del logFileTimeDiff_ts_groupByFile[file]
            readIndex += totalFrameCount_groupByFile[file]
            
            if (fileIndex == len(fileList)-1) or (mergeFile == False):    
                # ************ MultiProcessing ************
                # for MultiProcess Resource
                paramsForAnalyze = {}
                
                # for shared data (low speed. so, just only use sharing data between multiProcess)
                manager = Manager()
                paramsForAnalyze['processMessage'] = manager.dict()
                for cpuIndex in range(cpu_count()):
                    paramsForAnalyze['processMessage'][cpuIndex] = 'wait...'
                paramsForAnalyze['logFileTimeDiff_ts'] = logFileTimeDiff_ts
                    
                # Input data distribution
                distributionCount = 0
                for etherId in etherIdDic:
                    if etherId != EtherID.AllMessageTimeLog.value:
                        distributionCount += len(messageDataList[etherId])
                logger.logPrintWithConsol('Total message count selected output : {}'.format(distributionCount))
                if EtherID.AllMessageTimeLog.value in targetMessageID:
                    distributionCount = int(distributionCount / (cpu_count() - 1))
                else:
                    distributionCount = int(distributionCount / cpu_count())
                
                # MultiProc start
                logger.logPrintWithConsol('Now on data distributing...')
                procList = []
                keyList = [[len(messageDataList[etherId]), etherId] for etherId in etherIdDic]
                keyList = sorted(keyList, reverse=True)
                logger.flush()
                
                cpuIndex = 0
                outputList = []
                outputListSize = []
                for _ in range(cpu_count()):
                    outputList.append([])
                    outputListSize.append(0)
                for keyListIndex, (count, etherId) in enumerate(keyList):
                    if count > 0 and etherId in messageDataList:
                        if (outputListSize[cpuIndex] < distributionCount) or (cpuIndex == cpu_count()-1):
                            groupIndex = isGrouppingMessage(etherId)
                            if groupIndex != False:
                                groupList = getGrouppingMessage(groupIndex)
                                for sub_keyListIndex, (sub_count, sub_etherId) in enumerate(keyList):
                                    if sub_count > 0 and sub_etherId in groupList:
                                        outputList[cpuIndex].append(sub_etherId)
                                        outputListSize[cpuIndex] += sub_count
                                        keyList[sub_keyListIndex][0] = 0
                            else:
                                outputList[cpuIndex].append(etherId)
                                outputListSize[cpuIndex] += count
                                keyList[keyListIndex][0] = 0
                            
                            if (outputListSize[cpuIndex] >= distributionCount) and cpuIndex != cpu_count()-1:
                                cpuIndex += 1
                
                for cpuIndex in range(cpu_count()):
                    paramsForAnalyze['messageDataList'] = []
                    for etherId in outputList[cpuIndex]:
                        paramsForAnalyze['messageDataList'] += list(zip(
                            messageLogTimeList[etherId] if len(messageLogTimeList[etherId]) > 0 else itertools.repeat(0), 
                            itertools.repeat(etherId), 
                            messageDataList[etherId], 
                            messageLogIndexList[etherId] if len(messageLogIndexList[etherId]) > 0 else itertools.repeat(0), 
                            messageLogIDList[etherId] if len(messageLogIDList[etherId]) > 0 else itertools.repeat(etherId), 
                            messageFromList[etherId] if len(messageFromList[etherId]) > 0 else itertools.repeat(''), 
                            messageToList[etherId] if len(messageToList[etherId]) > 0 else itertools.repeat('')))
                        del messageDataList[etherId]
                        del messageLogTimeList[etherId]
                        del messageLogIndexList[etherId]
                        del messageLogIDList[etherId]
                        del messageFromList[etherId]
                        del messageToList[etherId]
                    try:
                        paramsForAnalyze['messageDataList'] = sorted(paramsForAnalyze['messageDataList'])
                    except Exception as e:
                        pass # Service IDのように、timestampがないメッセージはソートできずエラーとなるため
                    try:
                        p = Process(target=multiProcessAnalyzePacket, name='packetAnalyzer', args=[cpuIndex, getResource(), paramsForAnalyze])
                        p.start()
                    except Exception as e:
                        paramsForAnalyze['processMessage'][cpuIndex] = 'error'
                        logger.errLog("<Process Start Error> core:{0}, Error:{1}".format(cpuIndex, e))
                        logger.errLog(traceback.format_exc())
                        p = None
                    procList.append(p)
                
                while True:
                    stillAlive = False
                    for cpuIndex in range(cpu_count()):
                        coreLabel[cpuIndex].configure(text=paramsForAnalyze['processMessage'][cpuIndex])
                        if procList[cpuIndex] != None and procList[cpuIndex].is_alive():
                            stillAlive = True
                    if stillAlive == False:
                        break
                    root.update()
                    sleep(0.1)
                
                for p in procList:
                    if p != None: p.join()
                # ************ MultiProcessing ************
        
                logger.close()
                logger = None
                
                # subprocess.run('explorer {}'.format(os.curdir))
                # if outputFolder == None:
                if not continouslogfiles:
                    os.chdir("..")
                
    except Exception as e:
        if logger != None:
            logger.errLog("<Process Error> Error:{}".format(e))
            logger.errLog(traceback.format_exc())
        
    # All log files analyze complete.
    if logger != None:
        logger.close()
    label2.configure(text='Complete')
    root.update()

def multiProcessReadFile(cpuID, resource, params, procQueue):
    initMessage()
    setResource(resource) #変数共有のため
    
    filter_srcMAC = params['filter_srcMAC']
    filter_dstMAC = params['filter_dstMAC']
    filter_srcIP = params['filter_srcIP']
    filter_dstIP = params['filter_dstIP']
    filter_srcPort = params['filter_srcPort']
    filter_dstPort = params['filter_dstPort']
    someipmode = params['someipmode']
    saveFilteredLogData = params['saveFilteredLogData']
        
    fileList = params['fileList']
    targetMessageID = params['targetMessageID']
    etherAnalyze = params['etherAnalyze']
    canAnalyze = params['canAnalyze']
    timeStampSTR = params['timeStamp']
    
    totalFrameCount = {}
    messageDataList = {}
    messageLogTimeList = {}
    messageLogIndexList = {}
    messageLogIDList = {}
    messageFromList = {}
    messageToList = {}
    SomeipListup = {}
    prevTotalReadIndex = 0
    logFileTimeDiff_ts = {}
    
    for file in fileList:
        if params['messageNowOnProc'][file] == False:
            resource['mutex'].acquire()
            if params['messageNowOnProc'][file] == False:
                params['messageNowOnProc'][file] = True
                resource['mutex'].release()
            else:
                resource['mutex'].release()
                continue
        else:
            continue

        fileName = os.path.basename(file)
        fileName = fileName[:fileName.rfind('.')]
        params['processMessage'][cpuID] = 'Read "{}"'.format(fileName)
        readIndex = 0
        oldTimeTs = 0
        firstGNSStime = None
        logFileTimeDiff_ts[file] = [[0,0]] #index , ts
        messageDataList[file] = {}
        messageLogTimeList[file] = {}
        messageLogIndexList[file] = {}
        messageLogIDList[file] = {}
        messageFromList[file] = {}
        messageToList[file] = {}
        SomeipListup[file] = {}
        for etherId in etherIdDic:
            messageDataList[file][etherId] = []
            messageLogTimeList[file][etherId] = []
            messageLogIndexList[file][etherId] = []
            messageLogIDList[file][etherId] = []
            messageFromList[file][etherId] = []
            messageToList[file][etherId] = []
        
        logger = initLogger('log_read(' + fileName + ').txt', forMultiProcess = False)
        
        if etherAnalyze == True and ((EtherID.ServiceID.value in targetMessageID) or (EtherID.SubscribeMessage.value in targetMessageID)):
            #全まとめログ出力時のみ、Subscribe分析を出力する。
            initPCAPLoader(True)
        else:
            initPCAPLoader(False)
        
        if saveFilteredLogData == True:
            pcapWriter = dpkt.pcap.Writer(open(timeStampSTR + '-' + fileName + '.pcap', 'wb'))
            
        expName = file[file.rfind('.')+1:]
        if expName.lower() == "pcapng":
            if etherAnalyze == False and canAnalyze == True:
                continue
            reader = dpkt.pcapng.Reader(open(file,'rb'))
        elif expName.lower() == "pcap":
            if etherAnalyze == False and canAnalyze == True:
                continue
            reader = dpkt.pcap.Reader(open(file,'rb'))
        elif expName.lower() == "blf":
            reader = BLFEtherReader(open(file,'rb'), etherAnalyze, canAnalyze)
        elif expName.lower() == "asc":
            if etherAnalyze == True and canAnalyze == False:
                continue
            reader = ACSCanReader(open(file))
        else:
            print('Unknown file format')
            break
        
        tcpstream = {}
    #             tracemalloc.start()
        
        try:
            for ts, buf in reader:
                readIndex += 1
    #                     if readIndex < 541000:
    #                         continue
    #                     if readIndex > 1:
    #                         break
    #                     if readIndex == 8469:
    #                         print('here')
                
                if firstGNSStime != None and (ts < oldTimeTs-10 or ts > oldTimeTs+10): #10秒以上飛んだtsが来た場合
                    logFileTimeDiff_ts[file].append([readIndex, 0])
                    firstGNSStime = None
                oldTimeTs = ts
                
                if readIndex & 0xFFF == 0:
                    params['totalReadFrames'][cpuID] = prevTotalReadIndex + readIndex
                
                if ts > 9000000000:
                    logger.errLog("file:{}, FilelogIndex:{}, Abnormal Ethernet Timestamp. something data broken".format(fileName, readIndex))
                
                try:
                    if canAnalyze == True and buf[0:4] == b'\xFF\x0C\xAF\x00': #CANフレーム。（独自の識別子をBLF_Ethernetコード上でつけた）
                        fromInfo = ''
                        toInfo = ''
                        fromECM = ''
                        toECM = ''
                        packets = getCANFramePacket(buf[4:])
                    
                    elif etherAnalyze == True: #Ethernet
                        if saveFilteredLogData == True and ts < 9000000000:
                            pcapWriter.writepkt(buf, ts)
                            
                        L2_layer = dpkt.ethernet.Ethernet(buf)
                        if type(L2_layer.data) != dpkt.ip.IP:
                            continue
                        
                        srcMAC = ':'.join('%02x' % compat_ord(b) for b in L2_layer.src).upper()
                        dstMAC = ':'.join('%02x' % compat_ord(b) for b in L2_layer.dst).upper()
                        
                        if len(filter_srcMAC) > 0:
                            if not(srcMAC in filter_srcMAC):
                                continue
                            
                        if len(filter_dstMAC) > 0:
                            if not(dstMAC in filter_dstMAC):
                                continue
                            
                        L3_layer = L2_layer.data
                        if type(L3_layer) != dpkt.ip.IP: #ipv4
                            continue
                
                        src = socket.inet_ntoa( L3_layer.src )
                        to  = socket.inet_ntoa( L3_layer.dst )
                        
                        if str(src) == "0.0.0.0": #DHCP
                            continue
                        
                        if len(filter_srcIP) > 0:
                            if not(str(src) in filter_srcIP):
                                continue
                            
                        if len(filter_dstIP) > 0:
                            if not(str(to) in filter_dstIP):
                                continue
                            
                        L4_layer = L3_layer.data
                        if (type(L4_layer) != dpkt.tcp.TCP and type(L4_layer) != dpkt.udp.UDP):
                            continue
                        
                        if len(filter_srcPort) > 0:
                            if not(L4_layer.sport in filter_srcPort):
                                continue
                            
                        if len(filter_dstPort) > 0:
                            if not(L4_layer.dport in filter_dstPort):
                                continue
                        
                        # TCPのseq制御のためには、SYNパケット必要なので、0 lengthメッセージを無視してはいけない。
                        #if len(L4_layer.data) == 0:
                        #    continue
                        
                        fromInfo = "{0}({1}):{2}".format(src,srcMAC,L4_layer.sport)
                        toInfo = "{0}({1}):{2}".format(to,dstMAC,L4_layer.dport)
                        fromECM = IPdic.get(src, 'Unknown')
                        toECM = IPdic.get(to, 'Unknown')
                    
                        # ***********************************************
                        # *************** パケットpayload抽出****************
                        # ***********************************************
                        if type(L4_layer) == dpkt.udp.UDP:
                            #print("L4_layer.data : ")
                            #for i in range(0,len(L4_layer.data),16):
                            #    print(['{:02X} '.format(x) for x in L4_layer.data[i:i+16]])
                                
                            (packets, _) = getUdpPackets(L4_layer.data, someipmode, readIndex, ts, fromInfo, toInfo)
                
                        else:
                            if not(toInfo in tcpstream):
                                tcpstream[toInfo] = TCPStream()
                                
                            if tcpstream[toInfo].recv(L4_layer, ts) == 0:
                                continue
                            
                            #print("tcpDataBuf : ")
                            #for i in range(0,len(tcpDataBuf[toInfo]),16):
                            #    print(['{:02X} '.format(x) for x in tcpDataBuf[toInfo][i:i+16]])
                
                            # separate and remains into tcpDataBuf                           
                            (packets, remains) = getTcpPackets(tcpstream[toInfo].get(), someipmode, readIndex, ts, fromInfo, toInfo)
                            tcpstream[toInfo].setRemains(remains)              
    
                    # ***********************************************
                    # **************** メッセージ処理開始 ****************
                    # ***********************************************
                    for packet in packets:
                        messageID = packet.header.ID
                        if firstGNSStime == None and messageID == EtherID.GNSSDataMessage.value:
                            message = analyzeMessage(readIndex, datetime.fromtimestamp(ts), messageID, packet.dat)
                            if message != None and message.year != 0xFFFF:
                                firstGNSStime = datetime(message.year, message.month, message.day, message.hour, message.min, message.sec)
                                logFileTimeDiff_ts[file][-1][1] = datetime.timestamp(firstGNSStime) - ts
                             
                        if messageID in etherIdDic:
                            if messageID in targetMessageID:
                                messageDataList[file][messageID].append(packet.dat)
                                messageLogTimeList[file][messageID].append(ts)
                                messageLogIndexList[file][messageID].append(readIndex)
                                if (EtherID.AllMessageTimeLog.value in targetMessageID) and (messageID != EtherID.SubscribeMessage.value):
                                    messageDataList[file][EtherID.AllMessageTimeLog.value].append(packet.dat)
                                    messageLogTimeList[file][EtherID.AllMessageTimeLog.value].append(ts)
                                    messageLogIndexList[file][EtherID.AllMessageTimeLog.value].append(readIndex)
                                    #From,To情報および、各メッセージのID一覧は、全体時系列ログにのみ表示
                                    messageLogIDList[file][EtherID.AllMessageTimeLog.value].append(messageID)
                                    messageFromList[file][EtherID.AllMessageTimeLog.value].append(fromInfo)
                                    messageToList[file][EtherID.AllMessageTimeLog.value].append(toInfo)
                        else:
                            #logger.logPrint("Unknown Common Header : {0} (logIndex = {1})".format(hex(messageID), str(readIndex)))
                            #logger.logPrint(str([str(hex(char)) for char in packet.dat]))
                            pass
                        
                except Exception as e: # file read プロセスレベルではまだログファイルが作られてない
                    logger.errLog("FilelogIndex:{0}, from:{1}, to:{2}, Error:{3}".format(readIndex, fromECM, toECM, e))
                    logger.errLog(traceback.format_exc())
                    
    #                     snapshot = tracemalloc.take_snapshot()
    #                     displayMemory(snapshot)
    
        
            SomeipListup[file] = getSomeipListup()
        except Exception as e: # file read プロセスレベルではまだログファイルが作られてない
            logger.errLog("<Process Error> FilelogIndex:{0}, Error:{1}".format(readIndex, e))
            logger.errLog(traceback.format_exc())
            
        del reader # memory management
        prevTotalReadIndex += readIndex
        totalFrameCount[file] = readIndex
        if saveFilteredLogData == True:
            pcapWriter.close()
    
    params['processMessage'][cpuID] = 'wait for pipe'
    params['completeFlag'][cpuID] = True
    procQueue.put(logFileTimeDiff_ts)
    procQueue.put(totalFrameCount)
    procQueue.put(messageDataList)
    procQueue.put(messageLogTimeList)
    procQueue.put(messageLogIndexList)
    procQueue.put(messageLogIDList) #only for AllMessageSummery
    procQueue.put(messageFromList) #only for AllMessageSummery
    procQueue.put(messageToList) #only for AllMessageSummery
    procQueue.put(SomeipListup) #Subscribe Info
    params['processMessage'][cpuID] = 'complete'

def multiProcessAnalyzePacket(cpuID, resource, params):
    initMessage()
    setResource(resource) #変数共有のため
    logger = loadLogger()
    
    adjustTimeTsList = params['logFileTimeDiff_ts']
    messageSheetDic = {}
    lastMessageDic = {}
    totalCount = len(params['messageDataList'])
    analyzeSummary = False
    
    adjustTimeTsList_i = 0
    adjustTimeTsList_nextLogIndex = adjustTimeTsList[0][0] 
    adjustTimeTs = 0
    
    ##### Target Message List Output Process Start #####
    for i, (messageLogTime, etherId, data, messageLogIndex, messageID, messageFrom, messageTo) in enumerate(params['messageDataList']):
        if not etherId in messageSheetDic:
            messageSheetDic[etherId] = makeWorkSheet(etherId, getEtherIdDic(etherId)['name'])
        messageSheet = messageSheetDic[etherId]
        
        if etherId == EtherID.AllMessageTimeLog.value:
            logger.disableLogger()
            analyzeSummary = True
            try:
                if i & 0xFF == 0:
                    params['processMessage'][cpuID] = '(' + str(i) + '/' + str(totalCount) + ')' + getEtherIdDic(etherId)['name']
                    
                if adjustTimeTsList_nextLogIndex != None and messageLogIndex >= adjustTimeTsList_nextLogIndex:
                    if adjustTimeTsList[adjustTimeTsList_i][1] != 0:
                        adjustTimeTs = adjustTimeTsList[adjustTimeTsList_i][1]
                    adjustTimeTsList_i += 1
                    if adjustTimeTsList_i >= len(adjustTimeTsList):
                        adjustTimeTsList_nextLogIndex = None
                    else:
                        adjustTimeTsList_nextLogIndex = adjustTimeTsList[adjustTimeTsList_i][0]
                try:
                    logAdjustDatetime = datetime.fromtimestamp(messageLogTime + adjustTimeTs)
                except:
                    logAdjustDatetime = datetime.fromtimestamp(messageLogTime)
                    
                message = analyzeMessage(messageLogIndex, logAdjustDatetime, messageID, data, processRelativeParse = False)
                if message == None:
                    continue
                if messageSheet.currentRow == 0:
                    messageSheet.worksheet.freeze_panes(1, 1)
                    messageSheet.worksheet.autofilter(0, 0, 0, 115)
                    messageSheet.currentRow = 1
                messageSheet.worksheet.write(messageSheet.currentRow, 0, '=PrintHead("' + getEtherIdDic(message.commonHeader.messageID)['name'] + '")')
                messageSheet.worksheet.write(messageSheet.currentRow, 1, messageFrom)
                messageSheet.worksheet.write(messageSheet.currentRow, 2, messageTo)
                [messageSheet.currentRow, _, _] = message.printValue(messageSheet.worksheet, messageSheet.currentRow, 3)
                
            except Exception as e:
                messageSheet.worksheet.write(messageSheet.currentRow, 3, 
                                             "Parse error occured! : logIndex:{}, {}({}), Error:{}".format(
                                                 messageLogIndex, getEtherIdDic(etherId)['name'], hex(etherId), e))

        elif etherId == EtherID.ServiceID.value:
            try:
                if messageSheet.currentRow == 0:
                    messageSheet.worksheet.write_row(0, 0, ['logIndex','logTime','from ECU','from','to','to ECU','serviceID'], messageSheet.worksheet.cellFormats('header'))
                    messageSheet.worksheet.set_row(0, 20)
                    messageSheet.worksheet.autofilter(0, 0, 0, 6)
                    messageSheet.worksheet.freeze_panes(1, 0)
                    messageSheet.currentRow = 1
                    
                for item in data.values():
                    if adjustTimeTsList_nextLogIndex != None and item['index'] >= adjustTimeTsList_nextLogIndex:
                        if adjustTimeTsList[adjustTimeTsList_i][1] != 0:
                            adjustTimeTs = adjustTimeTsList[adjustTimeTsList_i][1]
                        adjustTimeTsList_i += 1
                        if adjustTimeTsList_i >= len(adjustTimeTsList):
                            adjustTimeTsList_nextLogIndex = None
                        else:
                            adjustTimeTsList_nextLogIndex = adjustTimeTsList[adjustTimeTsList_i][0]
                    try:
                        logAdjustDatetime = datetime.fromtimestamp(item['ts'] + adjustTimeTs)
                    except:
                        logAdjustDatetime = datetime.fromtimestamp(item['ts'])
                            
                    messageSheet.worksheet.write_row(messageSheet.currentRow, 0, [
                        item['index'],
                        str(logAdjustDatetime),
                        IPdic.get(item['from'][:item['from'].find('(')], 'Unknown'),
                        item['from'],
                        item['to'],
                        IPdic.get(item['to'][:item['to'].find('(')], 'Unknown'),
                        item['serviceID']
                        ], messageSheet.worksheet.cellFormats('default'))
                    messageSheet.currentRow += 1

            except Exception as e:
                logger.errLog("logIndex:{}, Error:{}".format(item['index'], e))
                logger.errLog(traceback.format_exc())
                    
        else:
            try:
                if i & 0xFF == 0:
                    params['processMessage'][cpuID] = '(' + str(i) + '/' + str(totalCount) + ')' + getEtherIdDic(etherId)['name']
                    
                if not etherId in lastMessageDic:
                    lastMessageDic[etherId] = None
                lastMessage = lastMessageDic[etherId]
                
                if adjustTimeTsList_nextLogIndex != None and messageLogIndex >= adjustTimeTsList_nextLogIndex:
                    if adjustTimeTsList[adjustTimeTsList_i][1] != 0:
                        adjustTimeTs = adjustTimeTsList[adjustTimeTsList_i][1]
                    adjustTimeTsList_i += 1
                    if adjustTimeTsList_i >= len(adjustTimeTsList):
                        adjustTimeTsList_nextLogIndex = None
                    else:
                        adjustTimeTsList_nextLogIndex = adjustTimeTsList[adjustTimeTsList_i][0]
                try:
                    logAdjustDatetime = datetime.fromtimestamp(messageLogTime + adjustTimeTs)
                except:
                    logAdjustDatetime = datetime.fromtimestamp(messageLogTime)
                    
                message = analyzeMessage(messageLogIndex, logAdjustDatetime, etherId, data, lastMessage)
                if message == None:
                    continue
                lastMessageDic[etherId] = message
                
                if messageSheet.currentRow == 0:
                    [messageSheet.currentRow, _, _] = message.printHeader(messageSheet.worksheet, messageSheet.currentRow, 0)
                [messageSheet.currentRow, _, _] = message.printValue(messageSheet.worksheet, messageSheet.currentRow, 0)
                    
            except ValueError as e:
                logger.errLog("<Size Error> logIndex:{0}, {1}({2}), Error:{3}".format(messageLogIndex, getEtherIdDic(etherId)['name'], hex(etherId), e))
            except Exception as e:
                logger.errLog("logIndex:{0}, {1}({2}), Error:{3}".format(messageLogIndex, getEtherIdDic(etherId)['name'], hex(etherId), e))
                logger.errLog(traceback.format_exc())
                
        #共通
        if messageSheet.currentRow > 500000:
            if etherId != EtherID.AllMessageTimeLog.value:
                params['processMessage'][cpuID] = 'draw chart ' + getEtherIdDic(etherId)['name']
                message.drawChart(messageSheet.workbook, messageSheet.worksheet, messageSheet.currentRow)
                lastMessageDic[etherId] = None
                
            params['processMessage'][cpuID] = 'saving ' + getEtherIdDic(etherId)['name']
            try:
                messageSheet.worksheet.close()
                messageSheet.workbook.close()
            except Exception as e:
                logger.errLog(traceback.format_exc())
                
            messageSheetDic[etherId] = makeWorkSheet(etherId, getEtherIdDic(etherId)['name'] + '_div(' + message.commonHeader.logTime.strftime('%Y-%m-%d-%H-%M-%S') + '~)')
            
    ##### Target Message List Output Process End #####
    logger.enableLogger()

    try:
        # ************ Msg分析結果出力 ************ (CommonHeader構造体のメモリは、MultiProcessの中で更新しているので、MultiProcessの関数内で出力必要)
        if analyzeSummary == True:
            summaryFile = open("Summary.txt","w")
            summaryFile.write("\n")
            summaryFile.write("<MsgCount Maximum Diff>\n")
            for messageID in CommonHeader.maxMsgCountDiff.keys():
                summaryFile.write("{0}({1}) : index={2}, max={3}\n".format(getEtherIdDic(messageID)['name'],hex(messageID),
                                                                      CommonHeader.maxMsgCountDiff_index[messageID],
                                                                      CommonHeader.maxMsgCountDiff[messageID]))
            summaryFile.write("\n")
            summaryFile.write("<Same Packet Message Max Count>\n")
            for messageID in CommonHeader.maxSameIndexCnt.keys():
                summaryFile.write("{0}({1}) : index={2}, max={3}\n".format(getEtherIdDic(messageID)['name'],hex(messageID),
                                                                      CommonHeader.maxSameIndexCnt_index[messageID],
                                                                      CommonHeader.maxSameIndexCnt[messageID]))
            summaryFile.write("\n")
            summaryFile.close()
        # ************ Msg分析結果出力 ************
        
        if len(ProfileMessage.laneLinkGeometryDic) > 0:
            params['processMessage'][cpuID] = 'output geometry ' + getEtherIdDic(etherId)['name']
            laneLinkInfoDic = ProfileMessage.laneLinkGeometryDic
            jsonDic = {}
            jsonDic['type'] = 'FeatureCollection'
            jsonDic['features'] = []
            for key, item in laneLinkInfoDic.items():
                value = {}
                value['type'] = 'Feature'
                value['geometry'] = {}
                value['geometry']['type'] = 'LineString'
                value['geometry']['coordinates'] = item['geometry']
                value['properties'] = {}
                value['properties']['llid'] = key
                jsonDic['features'].append(value)
            with open("DummyLaneLink.geojson", "w") as json_file:
                json.dump(jsonDic, json_file, indent=2, separators=(',', ': '))
    
        for etherId, messageSheet in messageSheetDic.items():
            lastMessage = lastMessageDic.get(etherId, None)
            if lastMessage != None:
                params['processMessage'][cpuID] = 'draw chart ' + getEtherIdDic(etherId)['name']
                lastMessage.drawChart(messageSheet.workbook, messageSheet.worksheet, messageSheet.currentRow)
                
            params['processMessage'][cpuID] = 'saving ' + getEtherIdDic(etherId)['name']
            try:
                messageSheet.worksheet.close()
                messageSheet.workbook.close()
            except Exception as e:
                logger.errLog(traceback.format_exc())
            
    except Exception as e:
            logger.errLog(traceback.format_exc())

    params['processMessage'][cpuID] = 'Complete'
    